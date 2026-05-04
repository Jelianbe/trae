import re
import logging
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

from pipeline.character_manager import CharacterManager, Character, get_character_manager
from pipeline.nlp_basics import get_nlp
from pipeline.semantic_ranker import SemanticRanker, get_semantic_ranker

logger = logging.getLogger(__name__)


@dataclass
class DialogueContext:
    text: str
    speaker_hint: Optional[str] = None
    prev_speaker: Optional[str] = None
    mentioned_characters: List[str] = field(default_factory=list)
    chapter_id: Optional[int] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None


@dataclass
class MatchResult:
    character: Character
    confidence: float
    match_type: str


PRONOUNS = {
    'male': {'他', '他俩', '他们'},
    'female': {'她', '她俩', '她们'},
    'unknown': {'它', '它们', '其'},
}

GROUP_SPEAKERS = {
    '三人': 'GROUP:3',
    '他们三人': 'GROUP:3',
    '他们三个': 'GROUP:3',
    '三人异口同声': 'GROUP:3',
    '众人': 'GROUP:CROWD',
    '大家': 'GROUP:CROWD',
    '齐声': 'GROUP:CROWD',
    '所有人': 'GROUP:CROWD',
}

TITLE_TRIGGERS = {
    '管家', '长老', '大师兄', '大师姐', '二师兄', '二师姐', '小师弟', '小师妹',
    '师兄', '师姐', '师弟', '师妹', '师尊', '师父', '徒弟', '徒儿',
    '公子', '小姐', '少爷', '夫人', '老爷', '奶奶', '将军', '丞相',
    '陛下', '殿下', '教主', '掌门', '帮主', '族长',
}

ACTION_TRIGGERS = {
    '冷笑', '沉声道', '点头', '摇头', '皱眉', '微笑', '大笑', '叹气',
    '挥手', '抬手', '转身', '站起', '坐下', '握拳', '抱拳', '拱手',
    '目光', '眼神', '脸色', '神情', '语气', '声音', '语气冰冷',
    '微微一笑', '哈哈大笑', '叹了口气', '皱了皱眉', '点了点头',
}

ADDRESS_TRIGGERS = {
    '师弟', '师妹', '师兄', '师姐', '徒儿', '徒弟', '师傅', '师父',
    '公子', '小姐', '少爷', '大人', '前辈', '晚辈', '阁下',
}

SPEAKER_HINTS = {
    '说道', '道', '说', '问道', '答道', '笑道', '喊道', '叫道', '怒道',
    '冷冷道', '淡淡道', '沉声道', '低声道', '高声道', '大声道',
    '开口道', '接口道', '插口道', '回应道', '点头道', '摇头道',
    '冷笑', '微笑', '大笑', '叹气', '叹息', '惊呼', '大喊', '大叫',
    '恭敬地', '恭敬', '轻声', '低声', '高声', '大声',
    '介绍道', '命令道', '下令', '报告', '推测', '皱眉', '犹豫',
    '接话', '齐声', '猜测', '暗道', '心想',
}

DIALOGUE_PATTERNS = [
    re.compile(r'"([^"]+)"'),
    re.compile(r'「([^」]+)」'),
    re.compile(r'『([^』]+)』'),
]

SPEAKER_PATTERNS = [
    re.compile(r'^([^\s]+?)(说道|道|问道|答道|笑道|喊道|叫道|怒道|冷冷道|淡淡道|沉声道|低声道|高声道|大声道|开口道|接口道|插口道|回应道|点头道|摇头道)'),
    re.compile(r'^([^\s]+?)(冷笑|微笑|大笑|叹气|叹息|惊呼|大喊|大叫)'),
    re.compile(r'^([^\s]+?)(恭敬地|恭敬|轻声|低声|高声|大声)说道'),
    # 都市格式：对话后跟动作/描述（"dialogue" 说话人动作）
    re.compile(r'^([^\s，。！？]{2,10}?)(的声音|介绍道|命令道|下令|报告|推测|皱眉|犹豫|接话|猜测|齐声)'),
]


class SpeakerMatcher:
    ROLE_CORE_WORDS = [
        '将军', '丞相', '元帅', '统领', '校尉', '大臣', '尚书', '宰相', '太傅',
        '总管', '掌门', '舵主', '堂主', '族长', '团长', '队长',
        '骑士', '剑客', '法师', '护卫', '士兵', '斥候', '杀手', '刺客',
        '盗贼', '佣兵', '猎人', '冒险者', '剑修', '修士',
        '管家', '丫鬟', '侍女', '侍卫', '铁匠', '商人', '牧师', '主教',
        '青年', '少年', '少女', '老者', '老人', '男子', '女子', '男人', '女人',
        '道士', '和尚', '僧人', '长老', '弟子', '前辈', '药老',
    ]
    ROLE_CORE_WORDS_SORTED = sorted(ROLE_CORE_WORDS, key=len, reverse=True)
    
    MODIFIER_PATTERN = (
        r'(?:'
        r'[黑白红蓝紫金银铁铜青灰赤绛翠黛玄]|'
        r'黑甲|白衣|青衣|红衣|蓝衣|紫衣|金甲|银甲|铁甲|'
        r'[老小长少中青幼]|'
        r'年[老迈轻少幼]|'
        r'[男女]|'
        r'[圣魔暗光血龙鹰狼凤虎蛇鬼]|'
        r'[未知神秘恐怖危险]|'
        r'中[年]|'
        r'[^\s，。！？\n「」『』""]{1,6}'
        r')?'
    )
    
    def __init__(
        self,
        character_manager: CharacterManager = None,
        semantic_ranker: SemanticRanker = None,
        l2_threshold: float = 0.7,
    ):
        self.char_manager = character_manager or get_character_manager()
        self.nlp = get_nlp()
        self._character_activity: Dict[int, int] = defaultdict(int)
        self._recent_speakers: List[str] = []
        self._recent_mentions: List[str] = []
        self._mention_counter = 0
        self._current_chapter_id: Optional[int] = None
        self.semantic_ranker = semantic_ranker or get_semantic_ranker()
        self.l2_threshold = l2_threshold
        self._character_dialogues: Dict[str, List[str]] = defaultdict(list)
        self._role_extract_cache: Dict[str, List[str]] = {}
        self._temp_char_cache: Dict[str, Character] = {}
    
    def _extract_descriptive_roles(self, text: str) -> List[str]:
        """
        提取描述性角色称呼。

        设计原理：中文社交称谓的结构是"修饰语+职业/身份核心词"。
        核心词（如"骑士""将军""法师"）是封闭的有限集合，修饰语（颜色、年龄、性别等）
        通过正则模式匹配。两者组合可覆盖所有未收录的变体（如"紫袍法师""银甲将军"），
        无需穷举所有可能组合。
        """
        if text in self._role_extract_cache:
            return self._role_extract_cache[text]
        
        results = []
        found_positions = set()
        
        for core_word in self.ROLE_CORE_WORDS_SORTED:
            full_pattern = self.MODIFIER_PATTERN + re.escape(core_word)
            
            for match in re.finditer(full_pattern, text):
                start, end = match.start(), match.end()
                overlaps = False
                for p in found_positions:
                    if start <= p < end or p <= start < end:
                        overlaps = True
                        break
                if not overlaps:
                    results.append(match.group())
                    found_positions.add(start)
        
        self._role_extract_cache[text] = results
        if len(self._role_extract_cache) > 1000:
            self._role_extract_cache.pop(next(iter(self._role_extract_cache)))
        
        # 过滤指示代词前缀（那、这、一）
        filtered_results = []
        for r in results:
            cleaned = re.sub(r'^[那这一][个些只]?', '', r)
            if cleaned:
                filtered_results.append(cleaned)
        
        return filtered_results
    
    def _infer_gender_from_context(self, name: str, context: str) -> str:
        """从上下文推断角色性别"""
        if any(h in context for h in ['他', '先生', '公子', '少爷', '老爷', '将军', '师兄', '师弟']):
            return 'male'
        if any(h in context for h in ['她', '小姐', '姑娘', '夫人', '师姐', '师妹', '丫鬟', '侍女']):
            return 'female'
        for male_title in ['骑士', '剑客', '法师', '将军', '团长', '管家', '侍卫', '长老', '掌门']:
            if male_title in name:
                return 'male'
        for female_title in ['丫鬟', '侍女', '小姐', '姑娘', '夫人']:
            if female_title in name:
                return 'female'
        return 'unknown'
    
    def _is_valid_character_name(self, name: str) -> bool:
        """验证角色名是否合法，过滤垃圾输出"""
        if not name or len(name) < 1:
            return False
        if name.startswith('未知_'):
            return True
        garbage_patterns = [
            r'[从在到向对于把被让给跟和与及]', r'[的地得了着过]', r'[一二三四五六七八九十]',
            r'[上下左右前后里外中]', r'[个只条本件位张把]', r'[很非常十分已经正在]',
        ]
        for pat in garbage_patterns:
            if re.search(pat, name):
                return False
        if len(name) > 6:
            return False
        try:
            result = self.nlp.analyze(name)
            if result.pos_tags:
                generic_nouns = {'人', '手', '身', '头', '心', '事', '物', '时', '年', '日', '月',
                                 '少', '老', '大', '小', '男', '女', '青', '中', '兵', '将',
                                 '少年', '青年', '老者', '少女', '男子', '女子', '男人', '女人'}
                if name in generic_nouns:
                    return False
        except Exception:
            pass
        return True
    
    def _is_verb(self, name: str) -> bool:
        """HanLP词性验证：若候选角色名中包含动词，返回True"""
        try:
            result = self.nlp.analyze(name)
            if result.pos_tags:
                for _, pos in result.pos_tags:
                    if pos and pos[0].lower() == 'v':
                        return True
        except Exception:
            pass
        return False
    
    def _resolve_pronoun_speaker(self, context_before: str) -> List[Tuple[str, str, float]]:
        """
        代词消解：从上下文中提取代词（他/她）的指代对象。
        
        策略：
        1. 找到上下文中最近的同性别角色
        2. 使用位置信息来确定"最近"
        """
        candidates = []
        pronoun_gender = None
        pronoun_pos = -1
        
        for i, char in enumerate(reversed(context_before)):
            if char == '她':
                pronoun_gender = 'female'
                pronoun_pos = len(context_before) - 1 - i
                break
            elif char == '他':
                pronoun_gender = 'male'
                pronoun_pos = len(context_before) - 1 - i
                break
        
        if not pronoun_gender:
            return candidates
        
        all_chars = self.char_manager.get_all_characters()
        
        char_positions = []
        for char in all_chars:
            if char.gender != pronoun_gender:
                continue
            
            last_pos = -1
            for i in range(len(context_before) - 1, -1, -1):
                if context_before[i:i+len(char.name)] == char.name:
                    last_pos = i
                    break
            
            for alias in char.aliases:
                for i in range(len(context_before) - 1, -1, -1):
                    if context_before[i:i+len(alias)] == alias:
                        if last_pos == -1 or i > last_pos:
                            last_pos = i
                        break
            
            if last_pos >= 0 and last_pos < pronoun_pos:
                char_positions.append((char, last_pos))
        
        char_positions.sort(key=lambda x: x[1], reverse=True)
        
        for char, pos in char_positions[:3]:
            distance = pronoun_pos - pos
            confidence = max(0.60, 0.85 - distance * 0.01)
            candidates.append((char.name, f'代词消解:{pronoun_gender}(距离{distance})', confidence))
        
        if not candidates:
            matching_chars = [c for c in all_chars if c.gender == pronoun_gender]
            for char in matching_chars[:2]:
                candidates.append((char.name, f'代词消解:{pronoun_gender}(无位置)', 0.50))
        
        return candidates
    
    def _infer_self_reference_speaker(self, text: str, context_before: str) -> List[Tuple[str, str, float]]:
        """
        自称词推断：从对话中的自称词推断说话人身份。
        
        原则：通则推理、拒绝猜测、标识未知
        
        优先级：
        1. 上下文中已存在的匹配身份的角色
        2. 上下文关键词匹配
        3. 未知_类型回落（不硬猜具体身份）
        """
        self_reference_map = {
            '老臣': ('elder_official', 'male', ['丞相', '大臣', '尚书', '宰相', '太傅', '老丞相'], '未知_文臣'),
            '末将': ('general', 'male', ['将军', '元帅', '统领', '校尉', '武将'], '未知_武将'),
            '属下': ('subordinate', 'unknown', ['下属', '部下', '随从'], '未知_下属'),
            '臣': ('official', 'male', ['丞相', '大臣', '尚书', '宰相'], '未知_文臣'),
            '奴才': ('servant', 'male', ['仆人', '奴仆', '家丁'], '未知_仆从'),
            '贫道': ('taoist', 'male', ['道士', '道长', '真人'], '未知_道士'),
            '贫尼': ('nun', 'female', ['尼姑', '师太'], '未知_尼姑'),
            '弟子': ('disciple', 'unknown', ['弟子', '徒弟', '徒儿'], '未知_弟子'),
            '徒儿': ('disciple', 'unknown', ['弟子', '徒弟'], '未知_弟子'),
        }
        
        candidates = []
        
        for self_ref, (role_type, gender, role_keywords, unknown_label) in self_reference_map.items():
            if self_ref in text:
                all_chars = self.char_manager.get_all_characters()
                matched_by_context = False
                
                for char in all_chars:
                    if gender != 'unknown' and char.gender != gender:
                        continue
                    
                    char_name = char.name
                    for kw in role_keywords:
                        if kw in char_name:
                            candidates.append((char.name, f'自称词:{self_ref}→{char.name}', 0.80))
                            matched_by_context = True
                            break
                
                if not matched_by_context and context_before:
                    for kw in role_keywords:
                        if kw in context_before:
                            for char in all_chars:
                                if kw in char.name:
                                    if gender == 'unknown' or char.gender == gender:
                                        candidates.append((char.name, f'自称词:{self_ref}→上下文匹配:{kw}', 0.75))
                                        matched_by_context = True
                                        break
                            if matched_by_context:
                                break
                
                if not candidates:
                    candidates.append((unknown_label, f'自称词:{self_ref}→{unknown_label}', 0.50))
        
        return candidates
    
    def _register_temporary_character(self, name: str, context: str) -> Optional[Character]:
        """
        动态注册临时角色（带内存缓存）。

        安全检查：仅在上下文中明确存在语言行为提示时才注册。
        无充分证据时返回 None，由调用方决定是否输出"未知_角色"。
        """
        SPEECH_ACTION_PATTERNS = [
            r'(?:说道|道|问|说|喊道|叫道|笑道|沉声道|低声道|高声道|冷冷道|淡淡道)',
            r'(?:点头|摇头|皱眉|转身|站起|坐下|抬手|挥手|冷笑|微笑)',
            r'(?:出现|走来|过来|进来|离开|推开|抓住|跑进|冲进)',
            r'(?:看着|盯着|扫了|抬起|放下|举起|拔出|跪)',
        ]
        has_speech_context = any(
            re.search(pat, context) for pat in SPEECH_ACTION_PATTERNS
        )
        if not has_speech_context:
            return None
        
        if name in self._temp_char_cache:
            return self._temp_char_cache[name]
        
        try:
            gender = self._infer_gender_from_context(name, context)
            char = self.char_manager.add_character(
                name=name,
                aliases=set(),
                gender=gender
            )
            if char:
                self._temp_char_cache[name] = char
                logger.debug(f"注册临时角色: {name} (性别: {gender})")
            return char
        except Exception as e:
            logger.warning(f"注册临时角色失败: {name}, {e}")
            return None
    
    def backfill_unknown_speakers(self, sentences: list) -> int:
        """
        冷启动后用全文角色库回填未知说话人。
        """
        if not sentences:
            return 0
        
        # 获取全文已确认的角色库
        confirmed_chars = list(self.char_manager._confirmed_characters.values())
        if not confirmed_chars:
            return 0
        
        char_map = {}
        for char in confirmed_chars:
            char_map[char.name] = char
            for alias in char.aliases:
                char_map[alias] = char
        
        backfill_count = 0
        for sentence in sentences:
            if not sentence.speaker.startswith("未知"):
                continue
            
            text = sentence.text
            # 按角色名长度降序排列，优先匹配长名字（避免短名字抢先匹配）
            sorted_chars = sorted(char_map.items(), key=lambda x: len(x[0]), reverse=True)
            for char_name, char in sorted_chars:
                if char_name in text:
                    sentence.speaker = char_name
                    sentence.speaker_id = char.id
                    backfill_count += 1
                    break
        
        return backfill_count
    
    def _extract_context_speakers(
        self, 
        text: str,
        context_before: str, 
        context_after: str
    ) -> List[Tuple[str, str, float]]:
        """
        从上下文窗口中提取候选说话人。
        
        优先级：
        1. context_before中的"XX说/道/问"显式提示
        2. context_before中的描述性角色称呼（优先于NER，避免截断）
        3. context_before中的PER实体（最近的优先）
        4. 自称词推断（老臣/末将/属下）
        5. 代词消解（他/她）
        6. context_after中的描述性角色
        7. context_after中的PER实体
        
        如果角色不在CharacterManager中，动态注册为临时角色。
        
        Returns:
            List of (角色名, 推理依据, 置信度)
        """
        candidates = []
        seen_names = set()
        
        if context_before:
            speech_pattern = re.findall(
                r'([^\s，。！？\n「」『』""]{1,6})(说道|道|说|问|沉声道|低声道|高声道|冷冷道|淡淡道|开口道|接口道|回应道|点头道|摇头道|笑道|喊道|叫道|怒道)',
                context_before
            )
            for name, hint in speech_pattern:
                if name in ['他', '她', '它', '我', '你']:
                    continue
                if name in ['沉声', '冷冷', '淡淡', '低声', '高声', '轻声', '微笑', '冷笑', '苦笑', '大笑', '怒吼', '咆哮', '低语', '喃喃', '厉声', '柔声', '急声', '颤声', '哑声', '厉色', '正色', '失声', '惊呼']:
                    continue
                if self._is_verb(name):
                    continue
                char = self.char_manager.get_character_by_name(name)
                if not char:
                    char = self._register_temporary_character(name, context_before)
                if char and char.name not in seen_names:
                    candidates.append((char.name, f'显式提示:{name}{hint}', 0.95))
                    seen_names.add(char.name)
            
            descriptive_roles = self._extract_descriptive_roles(context_before)
            for role in descriptive_roles:
                if role not in seen_names:
                    char = self.char_manager.get_character_by_name(role)
                    if not char:
                        char = self._register_temporary_character(role, context_before)
                    if char:
                        candidates.append((char.name, '描述性角色', 0.80))
                        seen_names.add(char.name)
            
            try:
                result = self.nlp.analyze(context_before)
                before_pers = [e for e in result.entities if e.type == 'PER']
                for pe in reversed(before_pers):
                    if not self._is_valid_character_name(pe.text) or self._is_verb(pe.text):
                        continue
                    is_substring = False
                    for seen in seen_names:
                        if pe.text in seen or seen in pe.text:
                            is_substring = True
                            break
                    if is_substring:
                        continue
                    char = self.char_manager.get_character_by_name(pe.text)
                    if not char:
                        char = self._register_temporary_character(pe.text, context_before)
                    if char and char.name not in seen_names:
                        candidates.append((char.name, '上下文PER(前)', 0.75))
                        seen_names.add(char.name)
            except Exception:
                pass
            
            pronoun_candidates = self._resolve_pronoun_speaker(context_before)
            for name, reason, confidence in pronoun_candidates:
                if name not in seen_names and self._is_valid_character_name(name) and not self._is_verb(name):
                    candidates.append((name, reason, confidence))
                    seen_names.add(name)
        
        if text:
            self_ref_candidates = self._infer_self_reference_speaker(text, context_before or '')
            for name, reason, confidence in self_ref_candidates:
                if name not in seen_names:
                    candidates.append((name, reason, confidence))
                    seen_names.add(name)
        
        if context_after:
            descriptive_roles = self._extract_descriptive_roles(context_after)
            for role in descriptive_roles:
                if role not in seen_names:
                    char = self.char_manager.get_character_by_name(role)
                    if not char:
                        char = self._register_temporary_character(role, context_after)
                    if char:
                        candidates.append((char.name, '描述性角色(后)', 0.75))
                        seen_names.add(char.name)
            
            try:
                result = self.nlp.analyze(context_after)
                after_pers = [e for e in result.entities if e.type == 'PER']
                for pe in after_pers:
                    if not self._is_valid_character_name(pe.text) or self._is_verb(pe.text):
                        continue
                    is_substring = False
                    for seen in seen_names:
                        if pe.text in seen or seen in pe.text:
                            is_substring = True
                            break
                    if is_substring:
                        continue
                    char = self.char_manager.get_character_by_name(pe.text)
                    if not char:
                        char = self._register_temporary_character(pe.text, context_after)
                    if char and char.name not in seen_names:
                        candidates.append((char.name, '上下文PER(后)', 0.70))
                        seen_names.add(char.name)
            except Exception:
                pass
        
        if not candidates:
            candidates.append(('未知_角色', '无充分证据', 0.30))
        
        return candidates
    
    @contextmanager
    def chapter_context(self, chapter_id: int):
        self.reset_activity()
        self._current_chapter_id = chapter_id
        try:
            yield self
        finally:
            self._current_chapter_id = None
    
    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        text = text.strip()
        
        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(text)
            if match:
                speaker = match.group(1).strip()
                hint = match.group(2)
                if speaker and len(speaker) <= 10:
                    if self._is_address_pattern(text, speaker):
                        return None, ""
                    return speaker, hint
        
        for hint in SPEAKER_HINTS:
            if hint in text:
                idx = text.find(hint)
                prefix = text[:idx].strip()
                
                if prefix:
                    for pattern in DIALOGUE_PATTERNS:
                        match = pattern.search(prefix)
                        if match:
                            prefix = prefix[:match.start()].strip()
                            break
                    
                    if prefix and len(prefix) <= 10:
                        if self._is_address_pattern(text, prefix):
                            return None, ""
                        return prefix, hint
        
        return None, ""
    
    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        """检查是否是呼唤句式（前缀是被呼唤的对象而非说话人）"""
        prefix_len = len(prefix)
        if prefix_len < len(text):
            next_char = text[prefix_len]
            if next_char in '！!':
                # 获取感叹号之后的内容（去掉感叹号本身）
                after_exclamation = text[prefix_len + 1:].strip()
                # 如果感叹号后紧跟说话提示词，则不是呼唤模式
                if after_exclamation.startswith(('说', '道', '问', '答', '笑', '喊', '叫')):
                    return False
                return True
            if next_char in '：:':
                # 获取冒号之后的内容（去掉冒号本身）
                after_colon = text[prefix_len + 1:].strip()
                # 如果冒号后紧跟说话提示词，则不是呼唤模式
                if after_colon.startswith(('说', '道', '问', '答', '笑', '喊', '叫')):
                    return False
                return True
            if next_char in '，,':
                remaining = text[prefix_len + 1:].strip()
                dialogue_start = re.match(r'^[您你你我我他她我们你们他们]+', remaining)
                if dialogue_start and len(dialogue_start.group()) >= 1:
                    return True
        return False
    
    def extract_post_dialogue_hint(self, suffix: str) -> Optional[str]:
        suffix = suffix.strip()
        
        patterns = [
            re.compile(r'^([^\s]+?)(说道|道|问道|答道|笑道|喊道|叫道)'),
            re.compile(r'^(他|她)说道'),
            re.compile(r'^(他|她)道'),
        ]
        
        for pattern in patterns:
            match = pattern.search(suffix)
            if match:
                speaker = match.group(1).strip()
                if speaker in ('他', '她'):
                    return speaker
                if speaker and len(speaker) <= 10:
                    return speaker
        
        return None
    
    def extract_mentioned_characters(self, text: str) -> List[str]:
        try:
            result = self.nlp.analyze(text)
            persons = [e.text for e in result.entities if e.type == 'PER']
        except Exception:
            persons = []
        return list(set(persons))
    
    def match_by_name(self, name: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_name(name)
        if char:
            return MatchResult(
                character=char,
                confidence=1.0,
                match_type='exact_name'
            )
        return None
    
    def match_by_alias(self, alias: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_alias(alias)
        if char:
            return MatchResult(
                character=char,
                confidence=0.9,
                match_type='alias'
            )
        return None
    
    def match_by_title(self, title: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_name(title)
        if char:
            return MatchResult(
                character=char,
                confidence=1.0,
                match_type='exact_name'
            )
        
        char = self.char_manager.get_character_by_alias(title)
        if char:
            return MatchResult(
                character=char,
                confidence=0.95,
                match_type='title'
            )
        
        return None
    
    def match_by_semantic(self, sentence: str) -> Optional[MatchResult]:
        """L2 语义匹配阶段。

        使用句子嵌入模型对候选角色进行语义相似度排序。
        先用角色名/别名进行初步筛选，然后用对话历史画像进行精细排序。

        冷启动优化：当角色没有对话历史时，构建更丰富的画像：
        - 包含角色名、别名、性别、头衔模式
        - 添加上下文模板（如"{name}说道"、"{name}点头"）

        Args:
            sentence: 输入句子（通常包含对话和上下文）

        Returns:
            匹配结果，如果没有候选超过阈值则返回 None
        """
        all_chars = self.char_manager.get_all_characters()
        if not all_chars:
            return None

        # 构建对话画像列表：(角色名, 画像文本)
        profiles = []
        char_by_name = {}  # 角色名 -> Character
        
        for char in all_chars:
            char_by_name[char.name] = char
            # 获取对话历史作为画像
            dialogue_context = self.get_dialogue_context(char.name)
            if dialogue_context:
                # 使用对话历史作为语义画像
                profiles.append((char.name, dialogue_context))
            else:
                # 冷启动优化：构建更丰富的画像
                profile_parts = []
                # 1. 角色名和别名
                profile_parts.append(char.name)
                if char.aliases:
                    profile_parts.extend(char.aliases)
                # 2. 性别提示
                if char.gender != "unknown":
                    profile_parts.append("他" if char.gender == "male" else "她")
                # 3. 上下文模板（模拟常见说话场景）
                profile_parts.append(f"{char.name}说道")
                profile_parts.append(f"{char.name}点头")
                profile_parts.append(f"{char.name}看着")
                # 4. 头衔模式
                for alias in char.aliases:
                    profile_parts.append(f"{alias}道")
                
                profile_text = " ".join(profile_parts)
                profiles.append((char.name, profile_text))

        # 使用语义排序器（用对话画像进行匹配）
        results = self.semantic_ranker.rank_with_profiles(
            sentence=sentence,
            profiles=profiles,
            threshold=self.l2_threshold,
        )

        if not results:
            return None

        # 取最高相似度的结果
        best_char_name, best_score = results[0]
        matched_char = char_by_name.get(best_char_name)

        if matched_char:
            # 将语义相似度映射到置信度 (0.6-0.8 范围)
            # 添加 max(0.6, ...) 下限保护，确保置信度不低于 0.6
            confidence = 0.6 + (best_score - self.l2_threshold) * 0.5
            confidence = max(0.6, min(confidence, 0.8))

            return MatchResult(
                character=matched_char,
                confidence=confidence,
                match_type='semantic',
            )

        return None
    
    def match_by_trigger_words(self, text: str, context: DialogueContext) -> Optional[MatchResult]:
        """
        FO-06: 触发词机制匹配
        
        在句子中搜索头衔/动作/称呼触发词，结合上下文匹配说话人。
        仅在上下文信息充足时使用，避免过度匹配。
        
        Args:
            text: 待匹配的句子
            context: 对话上下文
        
        Returns:
            匹配结果，如果没有找到触发词匹配则返回None
        """
        # 1. 头衔触发词：当文本中明确出现"X管家"、"Y师兄"等格式时才匹配
        # 需要是"修饰语+头衔"的形式，不能只有头衔本身
        title_patterns = [
            (r'(\S{1,3})(管家|长老|师兄|师姐|师弟|师妹)', 'title_with_modifier'),
            (r'(\S{1,3})(公子|小姐|少爷|夫人|老爷)', 'title_with_modifier'),
        ]
        
        import re
        for pattern, match_type in title_patterns:
            match = re.search(pattern, text)
            if match:
                modifier = match.group(1).strip()
                title = match.group(2)
                full_name = modifier + title
                
                # 尝试匹配角色名或别名
                char = self.char_manager.get_character_by_name(full_name)
                if char:
                    return MatchResult(
                        character=char,
                        confidence=0.80,
                        match_type=f'trigger_{match_type}'
                    )
                
                # 尝试匹配修饰语对应的角色
                if modifier:
                    char = self.char_manager.get_character_by_name(modifier)
                    if char:
                        return MatchResult(
                            character=char,
                            confidence=0.75,
                            match_type=f'trigger_{match_type}'
                        )
        
        # 2. 动作触发词：仅在最近有明确说话人且动作词紧接角色名时使用
        # 格式如："林轩皱眉"、"陈风最后说道"
        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char:
                idx = text.find(prev_char.name)
                if idx >= 0:
                    # 检查角色名前后20字内是否有动作触发词
                    context_window = text[max(0, idx-20):idx+20+len(prev_char.name)]
                    if any(action in context_window for action in ACTION_TRIGGERS):
                        return MatchResult(
                            character=prev_char,
                            confidence=0.65,
                            match_type='trigger_action_prev_speaker'
                        )
        
        # 3. 称呼触发词：如果对话中包含对其他角色的称呼，且最近只有一个候选说话人
        for addr in ADDRESS_TRIGGERS:
            if addr in text:
                # 查找被称呼的角色
                for char in self.char_manager.get_all_characters():
                    if addr in char.aliases or char.name.endswith(addr):
                        # 说话人是最近活跃但不是被称呼者的角色
                        # 仅当最近活跃角色只有1个候选时才匹配
                        unique_recent = []
                        for recent in reversed(self._recent_speakers[-3:]):
                            if recent != char.name:
                                speaker = self.char_manager.get_character_by_name(recent)
                                if speaker and speaker not in unique_recent:
                                    unique_recent.append(speaker)
                        
                        # 只有唯一候选时才返回
                        if len(unique_recent) == 1:
                            return MatchResult(
                                character=unique_recent[0],
                                confidence=0.70,
                                match_type='trigger_address'
                            )
        
        return None
    
    def match_by_pronoun(self, pronoun: str, context: DialogueContext) -> Optional[MatchResult]:
        gender = None
        for g, pronouns in PRONOUNS.items():
            if pronoun in pronouns:
                gender = g
                break
        
        if not gender:
            return None
        
        # FO-03: 局部对话窗口代词消解（3次发言内唯一性别候选）
        local_result = self._match_pronoun_in_local_window(gender)
        if local_result:
            return local_result
        
        # 回退到原有逻辑
        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char and prev_char.gender == gender:
                return MatchResult(
                    character=prev_char,
                    confidence=0.8,
                    match_type='pronoun_prev_speaker'
                )
        
        for mentioned in reversed(self._recent_mentions):
            char = self.char_manager.get_character_by_name(mentioned)
            if char and char.gender == gender:
                return MatchResult(
                    character=char,
                    confidence=0.7,
                    match_type='pronoun_recent'
                )
        
        candidates = []
        for char in self.char_manager.get_all_characters():
            if char.gender == gender:
                activity = self._character_activity.get(char.id, 0)
                candidates.append((char, activity))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return MatchResult(
                character=candidates[0][0],
                confidence=0.4,
                match_type='pronoun_activity'
            )
        
        return None
    
    def _match_pronoun_in_local_window(self, gender: str) -> Optional[MatchResult]:
        """
        FO-03: 局部对话窗口代词消解
        
        查找最近3次发言内，若只有1个角色性别匹配，直接返回该角色。
        
        Args:
            gender: 代词性别 ('male', 'female', 'unknown')
        
        Returns:
            匹配结果，如果窗口内无唯一性别候选则返回None
        """
        if not self._recent_speakers:
            return None
        
        # 获取最近3次发言的说话人
        recent_3 = self._recent_speakers[-3:]
        
        # 解析为角色对象并过滤性别
        candidates = []
        for name in recent_3:
            char = self.char_manager.get_character_by_name(name)
            if char and char.gender == gender:
                candidates.append(char)
        
        # 去重（同一角色可能连续发言多次）
        unique_candidates = []
        seen_ids = set()
        for char in candidates:
            if char.id not in seen_ids:
                seen_ids.add(char.id)
                unique_candidates.append(char)
        
        # 若只有1个角色性别匹配，直接返回
        if len(unique_candidates) == 1:
            return MatchResult(
                character=unique_candidates[0],
                confidence=0.90,
                match_type='pronoun_local_window'
            )
        
        return None
    
    def match_speaker(self, context: DialogueContext) -> Optional[MatchResult]:
        # L0: 上下文窗口推理（优先级最高）
        if context.context_before or context.context_after:
            context_candidates = self._extract_context_speakers(
                context.text,
                context.context_before or '', 
                context.context_after or ''
            )
            if context_candidates:
                name, reason, confidence = context_candidates[0]
                if name.startswith('未知_'):
                    unknown_char = Character(
                        id=-1,
                        name=name,
                        aliases=set(),
                        gender='unknown'
                    )
                    return MatchResult(
                        character=unknown_char,
                        confidence=confidence,
                        match_type=f'context_reasoning:{reason}'
                    )
                char = self.char_manager.get_character_by_name(name)
                if char:
                    return MatchResult(
                        character=char,
                        confidence=confidence,
                        match_type=f'context_reasoning:{reason}'
                    )
        
        if context.speaker_hint:
            if context.speaker_hint in ('他', '她'):
                result = self.match_by_pronoun(context.speaker_hint, context)
                if result:
                    return result
            else:
                result = self.match_by_name(context.speaker_hint)
                if result:
                    return result
                
                result = self.match_by_alias(context.speaker_hint)
                if result:
                    return result
                
                result = self.match_by_title(context.speaker_hint)
                if result:
                    return result
        
        mentioned = context.mentioned_characters or []
        if mentioned:
            for name in mentioned:
                result = self.match_by_name(name)
                if result:
                    return result
                
                result = self.match_by_alias(name)
                if result:
                    return result
        
        # L2 semantic matching (after L0/L1, before address inference)
        if context.chapter_id is not None and self.semantic_ranker.is_available():
            result = self.match_by_semantic(context.text)
            if result:
                return result
        
        # FO-06: 触发词机制（在语义匹配后，作为补充增强）
        trigger_result = self.match_by_trigger_words(context.text, context)
        if trigger_result:
            return trigger_result
        
        result = self._infer_from_address(context)
        if result:
            return result
        
        return None
    
    def _infer_from_address(self, context: DialogueContext) -> Optional[MatchResult]:
        text = context.text
        all_chars = self.char_manager.get_all_characters()
        
        addressed_char = None
        address_confidence = 0
        
        for char in all_chars:
            if char.name in text:
                addressed_char = char
                address_confidence = 0.9
                break
        
        if not addressed_char:
            for char in all_chars:
                for alias in char.aliases:
                    if alias in text:
                        addressed_char = char
                        address_confidence = 0.8
                        break
                if addressed_char:
                    break
        
        candidates = []
        
        if addressed_char:
            for char in all_chars:
                if char.id != addressed_char.id:
                    activity = self._character_activity.get(char.id, 0)
                    candidates.append((char, 0.6 + activity * 0.05, activity))
        
        if self._recent_mentions:
            for mentioned in reversed(self._recent_mentions[-5:]):
                char = self.char_manager.get_character_by_name(mentioned)
                if char and (not addressed_char or char.id != addressed_char.id):
                    activity = self._character_activity.get(char.id, 0)
                    candidates.append((char, 0.5 + activity * 0.03, activity))
        
        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char and (not addressed_char or prev_char.id != addressed_char.id):
                activity = self._character_activity.get(prev_char.id, 0)
                candidates.append((prev_char, 0.4, activity))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        seen_ids = set()
        unique_candidates = []
        for char, conf, activity in candidates:
            if char.id not in seen_ids:
                seen_ids.add(char.id)
                unique_candidates.append((char, conf, activity))
        
        if not unique_candidates:
            return None
        
        best_char, best_conf, _ = unique_candidates[0]
        
        MIN_CONFIDENCE_THRESHOLD = 0.4
        if best_conf < MIN_CONFIDENCE_THRESHOLD:
            return None
        
        return MatchResult(
            character=best_char,
            confidence=min(best_conf, 0.6),
            match_type='address_inference'
        )
    
    def update_activity(self, character_id: int, name: str):
        """记录角色出现，增加活跃度"""
        self._character_activity[character_id] = self._character_activity.get(character_id, 0) + 1
        
        # 维护最近活跃角色列表（最多10个）
        if name not in self._recent_speakers:
            self._recent_speakers.append(name)
            if len(self._recent_speakers) > 10:
                self._recent_speakers.pop(0)
    
    def cache_dialogue(self, character_name: str, dialogue_text: str):
        """缓存角色的对话文本，用于L2语义画像"""
        if character_name not in self._character_dialogues:
            self._character_dialogues[character_name] = []
        self._character_dialogues[character_name].append(dialogue_text)
        # 保持最近20条对话
        if len(self._character_dialogues[character_name]) > 20:
            self._character_dialogues[character_name] = self._character_dialogues[character_name][-20:]
    
    def get_dialogue_context(self, character_name: str) -> str:
        """获取角色的对话上下文（用于L2语义匹配）"""
        if character_name in self._character_dialogues:
            return " ".join(self._character_dialogues[character_name])
        return ""
    
    def update_mentions(self, names: List[str]):
        for name in names:
            if name not in self._recent_mentions:
                self._recent_mentions.append(name)
        if len(self._recent_mentions) > 20:
            self._recent_mentions = self._recent_mentions[-20:]
    
    def reset_activity(self):
        """重置活跃状态，并清理临时角色内存缓存"""
        self._character_activity.clear()
        self._recent_speakers.clear()
        self._recent_mentions.clear()
        self._temp_char_cache.clear()
    
    def get_speaker_for_sentence(self, sentence: str, prev_speaker: str = None, 
                                  chapter_id: int = None) -> Tuple[Optional[Character], str]:
        speaker_hint, hint_type = self.extract_speaker_hint(sentence)
        mentioned = self.extract_mentioned_characters(sentence)
        
        if mentioned:
            self.update_mentions(mentioned)
        
        context = DialogueContext(
            text=sentence,
            speaker_hint=speaker_hint,
            prev_speaker=prev_speaker or (self._recent_speakers[-1] if self._recent_speakers else None),
            mentioned_characters=mentioned,
            chapter_id=chapter_id
        )
        
        match_result = self.match_speaker(context)
        
        if match_result:
            self.update_activity(match_result.character.id, match_result.character.name)
            return match_result.character, match_result.character.name
        
        return None, None
    
    def analyze_dialogue(self, text: str, chapter_id: int = None) -> List[Tuple[str, Optional[Character]]]:
        # 第一轮：提取所有对话并建立缓存
        dialogues = []
        seen_positions = set()
        
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                if not any(start <= p < end or p <= start < p + (end - start) for p in seen_positions):
                    dialogues.append((start, end, match.group(1)))
                    seen_positions.add(start)
        
        # 第一轮：建立对话历史缓存
        self._build_dialogue_cache(text, chapter_id)
        
        # 重置追踪状态，避免第一轮缓存建立干扰第二轮说话人匹配
        self._recent_speakers.clear()
        self._recent_mentions.clear()
        self._character_activity.clear()
        
        # 第二轮：匹配说话人
        dialogues.sort(key=lambda x: x[0])
        results = []
        prev_speaker = None
        last_successful_speaker = None  # 记录最近成功匹配的说话人（用于代词消解）
        for i, (start, end, dialogue) in enumerate(dialogues):
            prefix_start = dialogues[i-1][1] if i > 0 else 0
            prefix = text[prefix_start:start].strip()
            
            suffix_end = dialogues[i+1][0] if i < len(dialogues) - 1 else len(text)
            suffix = text[end:suffix_end].strip()
            
            speaker_hint, hint_type = self.extract_speaker_hint(prefix + " " + suffix)
            mentioned = self.extract_mentioned_characters(prefix + " " + suffix)
            
            if mentioned:
                self.update_mentions(mentioned)
            
            # 代词消解优先使用 last_successful_speaker，而非 prev_speaker
            # 这样即使中间某句匹配失败，后续的"他/她"仍能解析到正确的角色
            pronoun_speaker = last_successful_speaker
            
            context = DialogueContext(
                text=prefix + " " + dialogue + " " + suffix,
                speaker_hint=speaker_hint,
                prev_speaker=pronoun_speaker,
                mentioned_characters=mentioned,
                chapter_id=chapter_id
            )
            
            match_result = self.match_speaker(context)
            
            if match_result:
                speaker = match_result.character
                self.update_activity(speaker.id, speaker.name)
                prev_speaker = speaker.name
                last_successful_speaker = speaker.name  # 更新最近成功匹配的说话人
            else:
                speaker = None
                prev_speaker = None
                # 注意：不更新 last_successful_speaker，保持上一轮的成功值
            
            results.append((dialogue, speaker))
        
        return results
    
    def _build_dialogue_cache(self, text: str, chapter_id: int = None):
        """
        第一轮扫描全文，建立角色对话历史缓存。
        先提取所有有明确说话人的对话，缓存到对应角色名下。
        这样第二轮语义匹配时可以利用已建立的对话画像。
        """
        all_dialogues = []
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                dialogue = match.group(1)
                
                prefix_start = max(0, start - 50)
                suffix_end = min(len(text), end + 50)
                prefix = text[prefix_start:start].strip()
                suffix = text[end:suffix_end].strip()
                context = prefix + " " + dialogue + " " + suffix
                
                all_dialogues.append((start, context, dialogue))
        
        all_dialogues.sort(key=lambda x: x[0])
        
        for _, context, dialogue in all_dialogues:
            speaker_hint, _ = self.extract_speaker_hint(context)
            if speaker_hint and speaker_hint not in ('他', '她'):
                char = self.char_manager.get_character_by_name(speaker_hint)
                if not char:
                    char = self.char_manager.get_character_by_alias(speaker_hint)
                if char and getattr(char, 'name', None):
                    self.cache_dialogue(char.name, dialogue)


_speaker_matcher: Optional[SpeakerMatcher] = None


def get_speaker_matcher() -> SpeakerMatcher:
    global _speaker_matcher
    if _speaker_matcher is None:
        _speaker_matcher = SpeakerMatcher()
    return _speaker_matcher
