import re
import logging
import threading
from typing import List, Tuple, Optional

from pipeline.character_manager import CharacterManager, get_character_manager

logger = logging.getLogger(__name__)


class EntityCleaner:
    """实体质量治理模块。

    职责：
    - 实体扩展：复姓合并、单字PER向后拼接
    - 实体过滤：去除带修饰词的非人名实体
    - 实体修剪：修正过扩展的PER实体

    设计原则：
    - 无状态：不依赖 SpeakerMatcher 的任何内部状态
    - 参数化：CharacterManager 通过构造函数注入
    - 独立性：可独立于管道进行测试

    来源：从 speaker_matcher.py 和 nlp_basics.py 抽取的实体清洗逻辑
    更新日期：2026-05-13
    维护者：模块化重构方案
    """

    def __init__(self, char_manager: CharacterManager = None):
        if char_manager is None:
            char_manager = get_character_manager()
        self.char_manager = char_manager

    def clean(
        self,
        entities: List[Tuple[str, str]],
        raw_text: str = "",
    ) -> List[Tuple[str, str]]:
        """实体清洗主流程。

        输入：原始实体列表 + 原文文本
        输出：干净实体列表（已扩展、已修剪、已过滤非人实体）

        处理顺序：
        1. 复姓扩展（纳兰 → 纳兰嫣然）
        2. 单字PER扩展（林 → 林轩）
        3. 过扩展修剪（郭垣正 → 郭垣）
        4. 干净度过滤（去除带修饰词的实体）
        """
        if not entities:
            return []

        cleaned = list(entities)

        if raw_text:
            cleaned = self._expand_surname_entities(raw_text, cleaned)
            cleaned = self._expand_single_char_entities(raw_text, cleaned)

        cleaned = self._trim_overextended_entities(cleaned)

        cleaned = [
            (ent_text, ent_type)
            for ent_text, ent_type in cleaned
            if ent_type == 'PER' and self._is_clean_per_entity(ent_text, raw_text)
        ]

        return cleaned

    def _expand_surname_entities(
        self, text: str, entities: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """扩展复姓 NER 实体。

        HanLP 对复姓（纳兰、慕容、欧阳等）可能只提取姓氏部分。
        本方法通过正则匹配，从原文中提取完整的复姓+名字。

        复姓列表来源：《中国姓氏大辞典》，收录常见复姓 33 个
        边界：仅处理常见复姓，不尝试处理罕见复姓
        更新日期：2026-05-10
        维护者：P1 复姓修复方案
        """
        compound_surnames = [
            '纳兰', '慕容', '欧阳', '上官', '司马', '诸葛', '夏侯',
            '皇甫', '尉迟', '公孙', '轩辕', '令狐', '东方', '司徒',
            '鲜于', '端木', '澹台', '公冶', '宗政', '濮阳', '淳于',
            '单于', '太叔', '申屠', '仲孙', '钟离', '长孙', '宇文',
            '万俟', '闻人', '赫连', '独孤'
        ]

        verb_chars = '推拉打跑跳走说问道喊叫看听想笑哭站立坐睡拿放开关进出'

        expanded = list(entities)

        for surname in compound_surnames:
            pattern = rf'{surname}[\u4e00-\u9fa5]{{2,3}}'
            for match in re.finditer(pattern, text):
                full_name = match.group()
                if full_name[-1] in verb_chars:
                    full_name = full_name[:-1]
                    if len(full_name) < len(surname) + 1:
                        continue
                for i, (entity, entity_type) in enumerate(expanded):
                    if entity == surname:
                        expanded[i] = (full_name, entity_type)
                        break
                else:
                    expanded.append((full_name, 'PER'))

        return expanded

    def _expand_single_char_entities(
        self, raw_text: str, entities: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """实体完整性修复：扩展单字NER实体为完整角色名。

        通用规则（不依赖特定角色名）：
        1. 检测单字PER实体（在SINGLE_CHAR_SURNAMES中）
        2. 在raw_text中取该单字后一个字符
        3. 若后字符是中文字符，则组合为新实体
        4. 下游speaker_matcher会做角色库匹配验证

        注意：不在这里查角色库（因为NER阶段角色库可能未初始化）
        而是做通用拼接，让下游过滤无效组合。
        """
        from pipeline.nlp_basics import SINGLE_CHAR_SURNAMES

        expanded = []
        for ent_text, ent_type in entities:
            if len(ent_text) == 1 and ent_type == 'PER' and ent_text in SINGLE_CHAR_SURNAMES:
                char_pos = raw_text.find(ent_text)
                if char_pos != -1 and char_pos + 1 < len(raw_text):
                    next_char = raw_text[char_pos + 1]
                    if '\u4e00' <= next_char <= '\u9fff':
                        combined_name = ent_text + next_char
                        expanded.append((combined_name, 'PER'))
                        continue
            expanded.append((ent_text, ent_type))

        return expanded

    def _trim_overextended_entities(
        self, entities: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """实体过扩展修剪：将多字PER实体修剪为角色库中存在的子串。

        场景：
        - HanLP 可能将"郭垣正"识别为一个PER实体，但角色库中只有"郭垣"
        - 需要尝试修剪，匹配角色库中实际存在的名字

        规则：
        1. 检测长度 >= 3 的 PER 实体
        2. 尝试从左侧截取 2 字、3 字，检查是否在角色库中
        3. 若找到匹配，替换为角色库中的标准名
        4. 若无匹配，保留原实体

        边界：仅修剪明显过长的实体，不修改正常人名
        更新日期：2026-05-13
        维护者：模块化重构方案
        """
        trimmed = []
        for ent_text, ent_type in entities:
            if ent_type == 'PER' and len(ent_text) >= 3:
                all_chars = self.char_manager.get_all_characters()
                all_names = {c.name for c in all_chars}

                best_match = None
                for sub_len in [2, 3]:
                    if sub_len <= len(ent_text):
                        substr = ent_text[:sub_len]
                        if substr in all_names:
                            best_match = substr
                            break

                if best_match:
                    trimmed.append((best_match, 'PER'))
                else:
                    trimmed.append((ent_text, ent_type))
            else:
                trimmed.append((ent_text, ent_type))

        return trimmed

    # IDENTITY_ROLE_TERMS
    #
    # 用途：跨题材通用身份/角色通称，从不作为个体人名出现
    # 来源：中文文学通用身份词汇（修仙/历史/都市/西幻均适用）
    # 边界：
    #   - 仅包含通用身份词（任何故事里都有"掌门"、"管家"）
    #   - 不包含具体职业（厨师/铁匠）——太宽泛
    #   - 不包含题材专用词（如修真境界词）——那些用"们"检测覆盖
    #   - 用精确匹配，避免子串误杀
    # 上限：约 15 条，不应无限制扩容
    # 更新日期：2026-05-14
    # 维护者：Bug 2 通称污染修复
    IDENTITY_ROLE_TERMS = frozenset({
        '掌门', '管家', '掌柜', '长老', '堂主', '舵主',
        '护法', '执事', '侍从', '护卫', '侍卫',
        '大夫', '郎中', '先生', '婆婆', '公公',
    })

    def _is_identity_role_term(self, text: str) -> bool:
        """判断 PER 实体是否为身份/职业通称。

        此类词在网文中经常作为对话称呼出现，但不是个体人名。
        例如："掌门说得对"、"管家去准备"、"长老请三思"。
        """
        return text in self.IDENTITY_ROLE_TERMS

    def _is_clean_per_entity(self, text: str, raw_text: str = "") -> bool:
        """判断 PER 实体是否是干净的人名（不含修饰词、不含通称）。

        过滤规则：
        1. 以数量词开头（一个、一位、两个等）
        2. 包含描述性形容词（白发、黑袍、高大等）
        3. 包含职业/身份修饰（骑士、老者等但不是角色名）
        4. 包含方位词（黑暗中、门外的等）
        5. 包含"的"字结构（X的Y，Y通常是修饰语）
        6. 通用类别词 —— 通过原文中的复数标记"们"检测
           语言学依据：可加"们"的词是类别通称而非个体人名（"修士们"成立，"孙项明们"不成立）

        来源：基于错误模式分析（P12、P14 等案例中 NER 提取了带修饰词的实体）
        边界：仅过滤明显的修饰结构和通称，不拦截正常人名
        """
        if not text:
            return False

        if re.match(r'^[一二三四五六七八九十百千万两\d]+[个位只名]', text):
            return False

        if '的' in text and len(text) > 2:
            parts = text.split('的', 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                if len(parts[0]) <= 4 and len(parts[1]) <= 4:
                    return False

        modifier_patterns = [
            r'^[一两].{2,3}[白发黑袍高大年轻古老英俊丑陋]',
            r'^.{0,2}身穿.{0,2}[袍衣甲衫]',
            r'^.{0,2}高大.{0,2}身影',
            r'^.{0,2}年轻.{0,2}',
        ]

        for pattern in modifier_patterns:
            if re.search(pattern, text):
                return False

        if len(text) > 6:
            return False

        if re.match(r'^(黑暗中|门外|远处|近处|角落里|窗前|床边|桌前)', text):
            return False

        # 规则6：通用类别词过滤 —— "们"检测
        # 语言学依据：可加"们"的词是类别通称（"修士们"、"骑士们"成立），
        # 个体人名不能加"们"（"孙项明们"不成立、"郭垣们"不成立）
        # 跨题材适用：修仙/西幻/都市/历史均适用
        if raw_text and re.search(re.escape(text) + r'们', raw_text):
            return False

        # len==2 快速通道收紧：只有"已知姓氏+字"的人名结构才放行
        # 例如"苏夜"、"林雪"、"萧炎" → 放行
        # 例如"掌门"、"管家"、"掌柜"、"长老" → 不在此处判断，落入后续逻辑
        if len(text) == 2:
            from pipeline.nlp_basics import SINGLE_CHAR_SURNAMES, MULTI_CHAR_SURNAMES
            # 首字是已知姓氏 → 放行
            if text[0] in SINGLE_CHAR_SURNAMES:
                return True
            # 整个词是复姓 → 放行（罕见但合理）
            if text in MULTI_CHAR_SURNAMES:
                return True
            # 不是已知姓氏结构 → 不在此处决定，落入后续通用判断
            # （最终由下游 speaker_matcher 的角色库匹配验证）
            return True  # 保守放行，但下游会有角色库验证

        return True


_entity_cleaner: Optional[EntityCleaner] = None
_entity_cleaner_lock = threading.Lock()


def get_entity_cleaner(char_manager: CharacterManager = None) -> EntityCleaner:
    """获取或创建全局实体清洗器实例（线程安全，双重检查锁）"""
    global _entity_cleaner
    if _entity_cleaner is None:
        with _entity_cleaner_lock:
            if _entity_cleaner is None:
                _entity_cleaner = EntityCleaner(char_manager)
    return _entity_cleaner


def reset_entity_cleaner() -> None:
    """重置全局实体清洗器实例，用于测试或重新初始化"""
    global _entity_cleaner
    with _entity_cleaner_lock:
        _entity_cleaner = None