import re
import os
import logging
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

from pipeline.character_manager import CharacterManager, Character, get_character_manager
from pipeline.nlp_basics import get_nlp, extract_srl_arg0s, SRLArg0
from pipeline.semantic_ranker import SemanticRanker, get_semantic_ranker
from utils import config as sm_config
from pipeline.descriptive_role_extractor import (
    DescriptiveRoleExtractor, TITLE_TRIGGERS, ACTION_TRIGGERS, ADDRESS_TRIGGERS, TitleTriggerMatcher, AddressTriggerMatcher,
)
from pipeline.pronoun_resolver import PronounResolver, PRONOUNS
from utils.zh_names import SINGLE_CHAR_SURNAMES

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
    dialogue: Optional[str] = None
    prefix_narration: Optional[str] = None  # 纯对话原文，不含 prefix/suffix


@dataclass
class MatchResult:
    character: Character
    confidence: float
    match_type: str


# 群体说话人检测正则模式
#
# 用途：检测文本中的群体说话人（GROUP:N 或 GROUP:CROWD）
# 来源：中文语法结构（数量词+人称代词/群体名词）
# 边界：
#   - 模式1: 数字+人/位 → GROUP:N（如"三人"→GROUP:3）
#   - 模式2: 群体指示词 → GROUP:CROWD（众人/大家/所有/全体）
#   - 模式3: 齐声/异口同声 → GROUP:CROWD
# 更新日期：2026-05-09
# 维护者：项目规则
GROUP_NUMBER_PATTERN = re.compile(r'(\d+)人')
CROWD_INDICATOR_WORDS = {'众人', '大家', '所有', '全体', '人群', '群众'}
CROWD_ACTION_WORDS = {'齐声', '异口同声', '同声', '一起'}


def detect_group_speaker(text: str) -> Optional[str]:
    """检测文本中的群体说话人。
    
    Args:
        text: 待检测文本
        
    Returns:
        群体说话人标识（如 'GROUP:3' 或 'GROUP:CROWD'），或 None
    """
    # 模式1: 数字+人 → GROUP:N
    match = GROUP_NUMBER_PATTERN.search(text)
    if match:
        number = int(match.group(1))
        if 2 <= number <= 10:
            return f'GROUP:{number}'
    
    # 模式2: 群体指示词 → GROUP:CROWD
    for word in CROWD_INDICATOR_WORDS:
        if word in text:
            return 'GROUP:CROWD'
    
    # 模式3: 齐声/异口同声 → GROUP:CROWD
    for word in CROWD_ACTION_WORDS:
        if word in text:
            return 'GROUP:CROWD'
    
    return None


# ===== 内联自 speech_verb_detector.py（2026-05-14） =====

# 纯说话动词（不带修饰，约12条）
# 来源：现代汉语言说动词封闭集合
SIMPLE_SPEECH_VERBS = [
    '道', '说', '问', '喊', '叫', '答', '应',
    '喝', '嚷', '骂', '斥', '吼',
]

# 表情/情绪修饰 + 说话（前2字情绪/表情，后1~2字说话动词，约30条）
# 来源：中文网文高频说话模式
EMOTION_MODIFIED_SPEECH = [
    '笑道', '叹道', '怒道', '喝道', '哼道', '嚷道',
    '骂道', '泣道', '冷冷道', '淡淡道', '沉声道',
    '低声道', '高声道', '厉声道', '轻声道',
    '冷笑道', '怪笑道', '柔声道', '安慰道',
    '苦笑道', '涩声道', '颤声道', '怒声道',
]

# 复合动作 + 说话（动作词 + 道/说/问，约20条）
# 来源：中文网文高频说话模式
COMPOUND_ACTION_SPEECH = [
    '说道', '问道', '答道', '回答道', '回应道',
    '接道', '续道', '摇头道', '点头道', '叹息道',
    '冷笑道', '讽刺道', '打趣道', '赞叹道',
]

# 所有说话动词集合（用于快速查询）
ALL_SPEECH_VERBS: Set[str] = set(SIMPLE_SPEECH_VERBS + EMOTION_MODIFIED_SPEECH + COMPOUND_ACTION_SPEECH)

# 说话边界词（角色名后紧跟，用于方向-B反向提取）
SPEECH_BOUNDARY_WORDS = EMOTION_MODIFIED_SPEECH + COMPOUND_ACTION_SPEECH


# ===== 内联自 speaker_hint_matcher.py（2026-05-14） =====

# 说话提示词集合（约30条）
# 来源：中文标点规范 + 网文常见说话动词
SPEAKER_HINTS = [
    '道', '说', '问', '喊', '叫', '答', '应', '笑', '叹', '怒',
    '喝', '哼', '嚷', '骂', '嘟', '喃', '吟', '斥', '骂道', '说道',
    '问道', '答道', '笑道', '叹道', '怒道', '喝道', '哼道', '嚷道',
    '沉声道', '低声道', '高声道', '冷冷道', '淡淡道',
]

# 引号匹配模式
#
# 用途：识别中文引号内的对话文本
# 来源：中文标点规范 GB/T 15834-2011 规定的引号对
# 边界：仅包含标准中文引号对，不包含英文引号和特殊符号
_QUOTE_CHARS = '""''「」『』'
_LEFT_QUOTES = '"「『'
_RIGHT_QUOTES = '"」』'


def _build_quote_patterns():
    """构建引号对话匹配正则
    
    仅捕获引号内的对话内容，不捕获引号前的前缀。
    前缀信息通过后续的位置计算获得。
    """
    patterns = []
    
    for lq, rq in [('「', '」'), ('『', '』'), ('"', '"'), ("'", "'")]:
        patterns.append(re.compile(
            rf'{re.escape(lq)}'
            rf'([^{re.escape(rq)}]+?)'
            rf'{re.escape(rq)}'
        ))

    return patterns


DIALOGUE_PATTERNS = _build_quote_patterns()

# SPEAKER_PATTERNS
#
# 用途：匹配"XX道"、"XX说"等格式，从"秦羽问道"中提取说话人名字"秦羽"
# 来源：中文句法结构（主语+谓语+引语），网文常见说话模式统计
# 边界：仅匹配"说话"类动词，不匹配"思考"类动词
#       名字长度限制1-20字，覆盖中文人名和长外国名（亚历山大·尼古拉耶维奇）
#       支持中点·以兼容外国名（哈利·波特）
# 更新日期：2026-05-25（同步 speaker_hint_matcher.py：复合动词优先→X对Y说→单字兜底）
# 维护者：同步自 pipeline/matchers/speaker_hint_matcher.py
# 注意：按动词长度降序排列（长匹配优先），避免"问道"被"问"+"道"截断
SPEAKER_PATTERNS = [
    # P0: X对Y说 → 只捕获 X（X对Y说中的X是说话人）
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*对[\u4e00-\u9fa5\u2027·]{1,6}\s*(?:道|说|问)[：:，,。\s]'),
    # P1: 复合动词（4字+优先）
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*(?:回答说|喃喃道|催促道|大叫道|大喊道|大声喊道|回答道|回应道|询问道|自言自语|低声道|高声道|沉声道|冷冷道|淡淡道|厉声道|轻声道|轻声说|轻声地说|急切地喊道|小心翼翼地说|小心翼翼道)[：:，,。\s]'),
    # P2: 双字动词
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*(?:问道|答道|笑道|叹道|怒道|喝道|哼道|嚷道|骂道|说道|叫道)[：:，,。\s]'),
    # P3: 单字动词（最后的兜底，仅保留高频独立使用的单字）
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*(?:道|说|问|叫|答|应|笑|叹)[：:，,。\s]'),
]


# ===== 内联自 speech_verb_detector.py — SpeechVerbDetector 类 =====

class SpeechVerbDetector:
    """说话动词检测器"""

    def is_speech_verb(self, word: str) -> bool:
        return word in ALL_SPEECH_VERBS

    def is_speech_related(self, word: str) -> bool:
        return word in ALL_SPEECH_VERBS

    def get_boundary_pattern(self) -> str:
        return '|'.join(re.escape(w) for w in SPEECH_BOUNDARY_WORDS)

    def extract_speech_context(self, text: str) -> List[Tuple[str, int]]:
        results = []
        for verb in sorted(ALL_SPEECH_VERBS, key=len, reverse=True):
            start = 0
            while True:
                idx = text.find(verb, start)
                if idx == -1:
                    break
                results.append((verb, idx))
                start = idx + len(verb)
        results.sort(key=lambda x: x[1])
        return results


_speech_detector = SpeechVerbDetector()

def is_speech_verb(word: str) -> bool:
    return _speech_detector.is_speech_verb(word)

def is_speech_related(word: str) -> bool:
    return _speech_detector.is_speech_related(word)

def get_boundary_pattern() -> str:
    return _speech_detector.get_boundary_pattern()


def _clean_speaker_name(name: str, nlp=None) -> str:
    """清理说话人名称，提取真正的人名。
    
    设计原则：
    1. 优先使用 HanLP 词性标注，提取 NR(人名) 标记的 token
    2. 当 HanLP 不可用时，使用最小后缀清理（仅移除说话动词）
    """
    if not name:
        return name
    
    if nlp:
        try:
            result = nlp.analyze(name)
            nr_tokens = [t.text for t in result.tokens if t.pos in ('NR', 'nr')]
            if nr_tokens:
                return ''.join(nr_tokens)
            
            nn_tokens = [t.text for t in result.tokens if t.pos in ('NN', 'nn')]
            if nn_tokens:
                return ''.join(nn_tokens)
        except Exception:
            pass
    
    # SPEECH_VERBS
    #
    # 用途：从"XX说道"等复合名称中移除说话动词后缀，提取纯角色名
    # 来源：中文说话动词有限集合，基于中文标点规范和网文常见说话模式
    # 边界：仅包含明确的说话/回应类动词，不扩展至动作/表情类
    # 更新日期：2026-05-14
    # 维护者：内联自 speaker_hint_matcher.py
    SPEECH_VERBS = [
        '冷冷道', '淡淡道', '沉声道', '低声道', '高声道',
        '说道', '问道', '答道', '笑道', '叹道', '怒道', '喝道', '哼道', '嚷道',
        '骂道', '回应道', '回答道', '接道', '续道',
        '轻声道', '低声说', '轻声说', '沉声说', '厉声道', '笑着道', '大叫道',
        '笑着说', '笑着',
        '道', '说', '问', '喊', '叫', '答', '应', '笑', '叹', '怒',
        '喝', '哼', '嚷', '骂', '回',
    ]
    
    for verb in sorted(SPEECH_VERBS, key=len, reverse=True):
        if name.endswith(verb) and len(name) > len(verb):
            name = name[:-len(verb)]
            break

    if name.endswith('地') and len(name) > 1:
        name = name[:-1]

    MODIFIERS = [
        '轻声', '低声', '高声', '沉声', '厉声', '冷声', '柔声',
        '急切', '匆匆', '缓缓', '轻轻', '暗暗', '偷偷',
    ]
    for modifier in sorted(MODIFIERS, key=len, reverse=True):
        if name.endswith(modifier) and len(name) > len(modifier):
            name = name[:-len(modifier)]
            break
    
    return name


class SpeakerMatcher:
    # ROLE_CORE_WORDS
    #
    # 用途：角色核心词表，用于识别"修饰语+核心词"结构的角色指称
    # 来源：中文语言学称谓体系——社交称谓中的职衔类、职业类、身份类
    #       结合中文网文高频角色类型统计
    # 边界：
    #   - 仅包含能独立作为说话人身份的词
    #   - 中文里能独立作为角色指称的社会身份词汇是有限的
    #   - 此集合基于语言学分类，不应无限制扩容
    # 更新日期：2026-05-02
    # 维护者：项目规则
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
        enable_alternating_detection: bool = False,
        enable_self_introduction: bool = False,
        enable_prev_speaker_fallback: bool = False,
    ):
        self.char_manager = character_manager or get_character_manager()
        self.nlp = get_nlp()
        # P2-1: 角色频率衰减 - 从简单计数器改为带时间衰减的权重
        # {character_id: {'weight': float, 'last_update': int}}
        self._character_activity: Dict[int, Dict] = {}
        self._activity_counter = 0  # 单调递增计数器，用于衰减计算
        self._recent_speakers: List[str] = []
        self._recent_mentions: List[str] = []
        self._mention_counter = 0
        self._current_chapter_id: Optional[int] = None
        self._current_project_id: str = ''
        self.semantic_ranker = semantic_ranker or get_semantic_ranker()
        self.l2_threshold = l2_threshold
        self._character_dialogues: Dict[str, List[str]] = defaultdict(list)
        self._role_extract_cache: Dict[str, List[str]] = {}
        self._temp_char_cache: Dict[str, Character] = {}

        self._enable_alternating_detection = enable_alternating_detection
        self._enable_self_introduction = enable_self_introduction
        self._enable_prev_speaker_fallback = enable_prev_speaker_fallback

        self.name_validator = CharacterNameValidator(self.nlp)
        self.hint_matcher = SpeakerHintMatcher(self.name_validator)
        self.role_extractor = DescriptiveRoleExtractor()
        self.self_ref_inferrer = SelfReferenceInferrer(self.char_manager)
        self.pronoun_resolver = PronounResolver(self.char_manager)
        self.title_trigger_matcher = TitleTriggerMatcher(self.char_manager)
        self.address_trigger_matcher = AddressTriggerMatcher(self.char_manager)

    @property
    def current_project_id(self) -> str:
        return self._current_project_id

    @current_project_id.setter
    def current_project_id(self, value: str):
        self._current_project_id = value

    def _extract_descriptive_roles(self, text: str) -> List[str]:
        return self.role_extractor.extract(text)

    def _is_valid_character_name(self, name: str) -> bool:
        return self.name_validator.is_valid(name)

    def _is_verb(self, name: str) -> bool:
        return self.name_validator.is_verb(name)

    def _infer_gender_from_context(self, name: str, context: str) -> str:
        return self.self_ref_inferrer.infer_gender_from_context(name, context)

    def _has_speech_context(self, context: str) -> bool:
        """检测文本是否包含说话/动作上下文。
        
        优先使用 HanLP 词性标注检测动词后是否紧跟引号或冒号。
        降级方案：HanLP 不可用时使用关键词匹配（仅作为辅助信号）。
        
        Args:
            context: 待检测的上下文文本
            
        Returns:
            是否包含说话上下文
        """
        # 优先方案：使用 HanLP 词性标注
        try:
            result = self.nlp.analyze(context)
            tokens = result.tokens
            pos_tags = [t.pos for t in tokens]
            
            # 检测动词(v/vd/VV)后是否紧跟引号或冒号
            for i, pos in enumerate(pos_tags):
                if pos in ('v', 'vd', 'VV', 'V', 'VE', 'VC', 'VW', 'VL', 'VH', 'VO', 'VP', 'VB'):
                    # 检查后续字符是否有引号或冒号
                    if i + 1 < len(tokens):
                        next_token = tokens[i + 1].text
                        if next_token in ('"', '"', ''', ''', '：', ':', '「', '『'):
                            return True
                    # 检查当前token后是否有标点符号
                    if i + 1 < len(pos_tags):
                        next_pos = pos_tags[i + 1]
                        if next_pos in ('PU', 'w', ':'):
                            return True
            
            open_quotes = {'"', '\u2018', '\u300c', '\u300e'}
            close_quotes = {'"', '\u2019', '\u300d', '\u300f'}
            has_open_q = any(t.text in open_quotes for t in tokens)
            has_close_q = any(t.text in close_quotes for t in tokens)
            if has_open_q and has_close_q:
                return True
                
        except (RuntimeError, ValueError, KeyError, AttributeError) as e:
            # HanLP 分析失败（模型不可用或输入格式异常），降级到关键词匹配
            logger.debug(f"HanLP 说话上下文检测失败，降级到关键词匹配: {e}")
            return self._has_speech_context_fallback(context)
        
        return False
    
    def _has_speech_context_fallback(self, context: str) -> bool:
        """降级方案：使用关键词匹配检测说话上下文。
        
        注意：此方法仅作为 HanLP 不可用时的降级方案，
        关键词只能作为辅助信号，不能作为唯一依据。
        """
        SPEECH_ACTION_PATTERNS = [
            r'(?:说道|道|问|说|喊道|叫道|笑道|沉声道|低声道|高声道|冷冷道|淡淡道)',
            r'(?:点头|摇头|皱眉|转身|站起|坐下|抬手|挥手|冷笑|微笑)',
            r'(?:出现|走来|过来|进来|离开|推开|抓住|跑进|冲进)',
            r'(?:看着|盯着|扫了|抬起|放下|举起|拔出|跪)',
        ]
        return any(
            re.search(pat, context) for pat in SPEECH_ACTION_PATTERNS
        )

    def _register_temporary_character(self, name: str, context: str, skip_speech_check: bool = False) -> Optional[Character]:
        # 使用通则推理检测说话上下文
        # skip_speech_check=True 时跳过检查（用于已从上下文提取的候选词）
        if not skip_speech_check and not self._has_speech_context(context):
            return None

        # H-20260516-10: 后台频次堆积
        self.char_manager.increment_frequency(name, self._current_project_id)

        if name in self._temp_char_cache:
            return self._temp_char_cache[name]

        try:
            gender = self._infer_gender_from_context(name, context)
            char = self.char_manager.add_character(
                name=name,
                project_id=self._current_project_id,
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
        if not sentences:
            return 0

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
            sorted_chars = sorted(char_map.items(), key=lambda x: len(x[0]), reverse=True)
            for char_name, char in sorted_chars:
                if char_name in text:
                    sentence.speaker = char_name
                    sentence.speaker_id = char.id
                    backfill_count += 1
                    break

        return backfill_count

    def _extract_narration(self, text: str, context_before: str = '', context_after: str = '') -> str:
        """从文本中提取旁白内容（去除引号内的对话）。
        
        用途：说话人识别只分析旁白内容，对话内容（引号内）不参与识别
        来源：中文标点规范 GB/T 15834-2011
        边界：
          - 移除所有引号内的对话内容：「...」『...』"..."'...'
          - 保留引号外的旁白描述
          - 如果旁白为空，返回空字符串
        更新日期：2026-05-14
        维护者：说话人识别改进方案
        """
        import re

        NARRATION_QUOTE_PATTERN = re.compile(
            '[\u300c\u300e\u201c\u2018\']'  # 「『"'  (左引号)
            '.*?'
            '[\u300d\u300f\u201d\u2019\']'  # 」』"'  (右引号)
        )
        
        narration_parts = []
        
        if context_before:
            narration_parts.append(NARRATION_QUOTE_PATTERN.sub('', context_before))
        
        if text:
            narration_parts.append(NARRATION_QUOTE_PATTERN.sub('', text))
        
        if context_after:
            narration_parts.append(NARRATION_QUOTE_PATTERN.sub('', context_after))
        
        narration = ' '.join(narration_parts)
        return narration.strip()

    def _match_from_character_library(self, narration: str, locked_only: bool = False) -> Optional[Character]:
        """在旁白中匹配角色库。
        
        用途：优先匹配角色库中的角色，避免 NER 重复创建
        来源：角色库（characters 表）
        边界：
          - locked_only=True 时只匹配锁定角色
          - locked_only=False 时匹配所有角色
          - 精确匹配角色名和别名
          - Phase 2: 增加说话关系验证，只返回有说话动词/动作暗示支撑的匹配
        更新日期：2026-05-09
        维护者：说话人识别改进方案
        """
        if locked_only:
            characters = self.char_manager.get_locked_characters(self._current_project_id)
        else:
            # H-20260516-10: 非锁定模式使用 eligible_characters
            characters = self.char_manager.get_eligible_characters(self._current_project_id)
        
        for char in characters:
            if char.name in narration:
                idx = narration.index(char.name)
                window = narration[max(0, idx - 20):idx + len(char.name) + 20]
                has_speech_verb = any(v in window for v in ALL_SPEECH_VERBS)
                has_action_hint = any(a in window for a in ['道', '说', '问', '答', '笑', '叹', '点头', '摇头', '转身', '看着', '望向', '走上前', '上前'])
                if has_speech_verb or has_action_hint:
                    return char
        
        for char in characters:
            if char.name in narration:
                return char
            for alias in char.aliases:
                if alias in narration:
                    return char
        
        return None

    def _extract_from_ner(self, narration: str) -> List[Tuple[str, str, float]]:
        """使用 NER 从旁白中提取人名（兜底方案）。
        
        用途：角色库匹配失败时，使用 NER 自动识别新角色
        来源：HanLP NER 分析
        边界：
          - 只提取 PER 类型实体
          - 需要过 name_validator 验证
          - 置信度固定为 0.70
        更新日期：2026-05-09
        维护者：说话人识别改进方案
        """
        candidates = []
        try:
            result = self.nlp.analyze(narration)
            pers = [e for e in result.entities if e.type == 'PER']
            for pe in pers:
                if not self.name_validator.is_valid(pe.text) or self.name_validator.is_verb(pe.text):
                    continue

                # H-20260516-10: NER 发现的角色名也计入后台频次
                self.char_manager.increment_frequency(pe.text, self._current_project_id)

                char = self.char_manager.get_character_by_name(pe.text, self._current_project_id)
                if char:
                    candidates.append((char.name, 'NER角色库匹配', 0.80))
                else:
                    new_char = self.char_manager.find_or_create(
                        pe.text, 
                        self._current_project_id,
                        context=narration,
                        chapter_id=self._current_chapter_id
                    )
                    candidates.append((new_char.name, 'NER自动创建', 0.70))
        except Exception as e:
            logger.debug(f"NER 分析失败: {e}")
        
        return candidates

    def _is_prev_speaker_addressed(self, text: str, prev_speaker: str) -> bool:
        if not prev_speaker or not text:
            return False
        if prev_speaker in text:
            return True
        return False

    def _detect_self_introduction(self, text: str) -> Optional[str]:
        match = re.search(r'我是([\u4e00-\u9fa5]{2,4})', text)
        if match:
            name = match.group(1)
            if self.name_validator.is_valid_speaker_candidate(name):
                return name
        return None

    def _expand_surname_entities(self, text: str, entities: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
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

        # 常见动词（用于排除）
        verb_chars = '推拉打跑跳走说问道喊叫看听想笑哭站立坐睡拿放开关进出'

        expanded = list(entities)

        for surname in compound_surnames:
            # 匹配复姓+2-3字名字（如纳兰嫣然、慕容复、欧阳明日）
            # 使用负向前瞻排除动词
            pattern = rf'{surname}[\u4e00-\u9fa5]{{2,3}}'
            for match in re.finditer(pattern, text):
                full_name = match.group()
                # 排除：最后一个字是动词（可能是后面的动词被包含进来）
                if full_name[-1] in verb_chars:
                    full_name = full_name[:-1]
                    if len(full_name) < len(surname) + 1:
                        continue
                # 检查是否已有截断版本
                for i, (entity, entity_type) in enumerate(expanded):
                    if entity == surname:
                        expanded[i] = (full_name, entity_type)
                        break
                else:
                    expanded.append((full_name, 'PER'))

        return expanded

    def _extract_descriptive_characters(self, text: str) -> List[str]:
        """从文本中提取描述性角色指称。

        当 NER 未识别到 PER 实体时，使用正则匹配常见的描述性角色模式。
        这些模式包括：
        - 颜色 + 服饰/物品（如"黑衣人"、"白袍老者"）
        - 形容词 + 身份（如"高大身影"、"神秘人物"）

        来源：基于错误案例分析（P4、P13 等描述性角色未被识别案例）
        边界：仅匹配 2-5 字的描述性短语，避免匹配过长描述
              不匹配"声音"类型（因为声音本身不是说话人）
        更新日期：2026-05-10
        维护者：P2 描述性角色修复方案
        """
        candidates = []

        # 模式1：颜色 + 服饰 + 身份
        pattern1 = r'[黑白红蓝青紫黄灰银金][\u4e00-\u9fa5]{1,3}(?:人|者|客|僧|道|尼|侠|剑)'
        for match in re.finditer(pattern1, text):
            candidates.append(match.group())

        # 模式2：形容词 + 身份/人物（排除"声音"类型）
        pattern2 = r'(?:高大|矮小|瘦弱|肥胖|年轻|年老|神秘|陌生)(?:的)?(?:身影|人物|男子|女子|老者|少年)'
        for match in re.finditer(pattern2, text):
            word = match.group()
            if '声音' not in word:
                candidates.append(word)

        return candidates

    def _extract_context_speakers(
        self,
        text: str,
        context_before: str,
        context_after: str,
        prefix_narration: str = ''
    ) -> List[Tuple[str, str, float]]:
        candidates = []
        seen_names = set()

        # 步骤0：引号前旁白前缀优先（H-20260516-10）
        # 格式：赵总监皱起眉头问道："谁批准的？" → prefix="赵总监皱起眉头问道"
        # 如果旁白前缀中包含角色库角色名，则该角色有最高优先级
        if prefix_narration:
            speech_verbs = {'道', '说', '问', '答', '笑道', '说道', '问道', '答道',
                            '冷喝', '喝道', '冷笑', '叹道', '怒道', '斥道', '叫道', '喊道'}
            all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
            sorted_chars = sorted(all_chars, key=lambda c: -len(c.name))
            for char in sorted_chars:
                if char.name in prefix_narration and char.name not in seen_names:
                    after_name = prefix_narration[prefix_narration.index(char.name) + len(char.name):
                                                  prefix_narration.index(char.name) + len(char.name) + 15]
                    has_speech = any(v in after_name for v in speech_verbs)
                    candidates.append((char.name,
                        '同行动作主语' if has_speech else '同行引用',
                        0.88 if has_speech else 0.82))
                    seen_names.add(char.name)
                    break

        # 步骤1：代词消解优先于 NER（代词比描述性短语更可靠）
        pronoun_weak_signal = False
        if context_before:
            pronoun_result = self._resolve_pronoun_in_context(context_before)
            if pronoun_result:
                if pronoun_result.get('weak_signal'):
                    # P1-3: 代词消解失败传递弱信号
                    # 记录存在未解析代词，后续步骤不强行匹配
                    pronoun_weak_signal = True
                    logger.debug(f"代词弱信号: {pronoun_result['reason']}")
                else:
                    char = self._match_candidate_to_character(pronoun_result['name'], context_before)
                    if char:
                        candidates.append((char.name, f'代词消解({pronoun_result["reason"]})', 0.80 if char.id != -1 else 0.65))
                        seen_names.add(char.name)

        # 步骤2：NER context_per 路径已移除（2026-05-14）
        # 原因：消融实验显示 NER context_per 路径净收益 -1.9%
        # NER 提取的"上下文被提及角色"多数是旁白中提到的非说话人角色
        # 步骤2：描述性角色提取（从 context_before 旁白中）
        # 新方案A: 描述性角色必须映射到角色库，非角色库描述不作为候选
        if context_before:
            before_narr = self._extract_narration('', context_before, '')
            if before_narr:
                descriptive_roles = self.role_extractor.extract(before_narr)
            else:
                descriptive_roles = []
            for role in descriptive_roles:
                if role not in seen_names:
                    # 新方案A: require_library=True, 不创建临时角色
                    char = self._match_candidate_to_character(role, before_narr, skip_speech_check=True, require_library=True)
                    if char:
                        candidates.append((char.name, '描述性角色', 0.80))
                        seen_names.add(role)

        # 步骤3：身份词提取已删除（2026-05-12）
        # 原因：身份词提取在测试集中没有贡献正面准确率，且干扰主流程
        # 身份词太泛（如"长老"可能对应多个角色），依赖隐式静态映射表，违背核心原则

        if text:
            self_ref_candidates = self.self_ref_inferrer.infer(text, context_before or '')
            for name, reason, confidence in self_ref_candidates:
                if name not in seen_names:
                    # 新方案A: require_library=True, 不创建临时角色
                    char = self._match_candidate_to_character(name, text, require_library=True)
                    if char:
                        candidates.append((char.name, f'自称推断({reason})', 0.80))
                        seen_names.add(name)

        if context_after:
            after_narr = self._extract_narration('', '', context_after)
            if after_narr:
                descriptive_roles = self.role_extractor.extract(after_narr)
            else:
                descriptive_roles = []
            for role in descriptive_roles:
                if role not in seen_names:
                    # 新方案A: require_library=True, 不创建临时角色
                    char = self._match_candidate_to_character(role, after_narr, skip_speech_check=True, require_library=True)
                    if char:
                        candidates.append((char.name, '描述性角色(后)', 0.75))
                        seen_names.add(role)

        # 方向1：语境角色优先（H-20260516-10: 改用 get_eligible_characters 过滤临时角色）
        # 注意：使用 append 而非 insert(0)，配合 sorted 的 -len(name) 确保最长匹配优先
        if context_before and not candidates:
            nearby_window = context_before[-120:]
            all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
            sorted_chars = sorted(all_chars, key=lambda c: -len(c.name))
            for char in sorted_chars:
                if char.name in nearby_window and char.name not in seen_names:
                    pos = nearby_window.rindex(char.name)
                    distance = len(nearby_window) - pos
                    proximity_bonus = max(0.10 - 0.005 * distance, 0.0)
                    after_name = nearby_window[pos + len(char.name):pos + len(char.name) + 15]
                    speech_verbs = {'道', '说', '问', '答', '笑道', '说道', '问道', '答道',
                                    '冷喝', '喝道', '冷笑', '叹道', '怒道', '斥道', '叫道', '喊道'}
                    has_speech = any(v in after_name for v in speech_verbs)
                    confidence = min(0.75 + proximity_bonus + (0.10 if has_speech else 0), 0.90)
                    candidates.append((char.name,
                        '语境角色优先({})'.format('说话动词' if has_speech else '临近'),
                        confidence))
                    seen_names.add(char.name)

        # 方向3：动态候选（角色库精确匹配 + 别名匹配）
        # H-20260516-10: 改用 get_eligible_characters
        if not candidates and (context_before or context_after):
            merged = self._extract_narration('', context_before or '', context_after or '')
            if merged:
                all_chars = sorted(
                    self.char_manager.get_eligible_characters(self._current_project_id),
                    key=lambda c: -len(c.name)
                )
                for char in all_chars:
                    if char.name in merged:
                        candidates.append((char.name, '动态候选(角色库)', 0.72))
                    else:
                        for alias in char.aliases:
                            if alias in merged:
                                candidates.append((char.name, '动态候选(别名:{})'.format(alias), 0.70))
                                break

        # 兜底步骤：在角色库中匹配旁白内容
        # 用于处理"掌柜抬头看了看他，笑道"等场景，其中身份词提取失败但角色库中有该角色
        # 注意：优先匹配 context_before 中的角色，避免 context_after 中的角色干扰
        # H-20260515-05 + 方向2(H-20260515-08): 话动特征强化
        # 方向2改动：扩大说话动词列表 + 扩大窗口至20字 + 提高置信度至0.78
        if not candidates or (len(candidates) <= 2 and all(c[2] < 0.75 for c in candidates)):
            if context_before:
                before_narration = self._extract_narration('', context_before, '')
                if before_narration:
                    speech_verbs = ['道', '说', '问', '答', '笑道', '说道', '问道', '答道',
                                    '冷喝', '喝道', '冷笑', '叹道', '怒道', '斥道', '叫道', '喊道',
                                    '笑问', '笑骂', '嗔道', '应道', '叹息', '沉吟']
                    action_verbs = ['端起', '翻开', '打开', '站起身', '皱起', '走到', '看向',
                                    '扫了', '看了看', '点头', '摇头', '坐下', '合上', '放下',
                                    '接过', '转身', '摆了摆', '喝了口', '揉了揉', '掏出']

                    all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
                    for char in all_chars:
                        if char.name in before_narration:
                            idx = before_narration.index(char.name)
                            after_name = before_narration[idx + len(char.name):idx + len(char.name) + 20]
                            has_speech = any(v in after_name for v in speech_verbs)
                            has_action = any(v in after_name for v in action_verbs)

                            if has_speech:
                                candidates.insert(0, (char.name, '角色库旁白匹配(前)(说话)', 0.78))
                            elif has_action:
                                candidates.append((char.name, '角色库旁白匹配(前)(动作)', 0.55))
                            else:
                                candidates.insert(0, (char.name, '角色库旁白匹配(前)', 0.70))
            if not candidates or (len(candidates) <= 2 and all(c[2] < 0.75 for c in candidates)):
                narration = self._extract_narration('', context_before, context_after)
                if narration:
                    char_match = self._match_from_character_library(narration)
                    if char_match:
                        candidates.insert(0, (char_match.name, '角色库旁白匹配', 0.70))

        # N-2: 动作主语优先
        # 语言学依据：中文旁白中"角色名+动词"结构的主语通常是动作发出者
        # 来源：通用句法规则，非静态词表
        # 边界：只识别角色库中的角色名+动词结构
        if context_before and candidates:
            action_subject = self._extract_action_subject(context_before)
            if action_subject and action_subject in [c[0] for c in candidates]:
                # 提升动作主语的置信度
                enhanced = []
                for name, reason, confidence in candidates:
                    if name == action_subject:
                        confidence = min(confidence + 0.10, 0.95)
                        reason = f'{reason}(动作主语)'
                    enhanced.append((name, reason, confidence))
                enhanced.sort(key=lambda x: -x[2])
                candidates = enhanced

        # P2-2: 近因衰减（反粘着机制）
        # v7.0 长文本基线显示：连续对话中最近说话人被过度优先
        # 原理：对话通常是轮流进行的，刚说完的人不应立即再次说话
        # 衰减梯度：越近的角色获得越多的负分
        from utils.config import RECENCY_DECAY_RECENT, RECENCY_DECAY_SECOND, RECENCY_DECAY_OTHER

        if candidates and self._recent_speakers:
            recent_rank = {}
            for i, name in enumerate(reversed(self._recent_speakers[-5:])):
                recent_rank[name] = len(self._recent_speakers[-5:]) - i  # 最近=5, 次近=4, ...

            decayed = []
            for name, reason, confidence in candidates:
                if name in recent_rank:
                    rank = recent_rank[name]
                    # 衰减量：最近的 -RECENCY_DECAY_RECENT，次近 -RECENCY_DECAY_SECOND，其余 -RECENCY_DECAY_OTHER
                    if rank == len(self._recent_speakers[-5:]):
                        decay = RECENCY_DECAY_RECENT
                    elif rank == len(self._recent_speakers[-5:]) - 1:
                        decay = RECENCY_DECAY_SECOND
                    else:
                        decay = RECENCY_DECAY_OTHER
                    confidence = max(confidence - decay, 0.20)
                    reason = f'{reason}(近因衰减-r{rank})'
                decayed.append((name, reason, confidence))
            decayed.sort(key=lambda x: -x[2])
            return decayed

        if not candidates:
            candidates.append(('未知_无法推断', '无上下文线索', 0.30))

        return candidates

    def _is_clean_per_entity(self, text: str) -> bool:
        """判断 PER 实体是否是干净的人名（不含修饰词）。

        过滤规则：
        1. 以数量词开头（一个、一位、两个等）
        2. 包含描述性形容词（白发、黑袍、高大等）
        3. 包含职业/身份修饰（骑士、老者等但不是角色名）
        4. 包含方位词（黑暗中、门外的等）

        来源：基于错误模式分析（P12、P14 等案例中 NER 提取了带修饰词的实体）
        边界：仅过滤明显的修饰结构，不拦截正常人名
        """
        if not text:
            return False

        # 过滤：以数量词开头
        if re.match(r'^[一二三四五六七八九十百千万两\d]+[个位只名]', text):
            return False

        # 过滤：包含常见修饰词模式
        modifier_patterns = [
            r'^[一两].{2,3}[白发黑袍高大年轻古老英俊丑陋]',  # "一个白发"、"两位高大"
            r'^.{0,2}身穿.{0,2}[袍衣甲衫]',  # "身穿黑袍"
            r'^.{0,2}高大.{0,2}身影',  # "高大的身影"
            r'^.{0,2}年轻.{0,2}',  # "年轻人"
        ]

        for pattern in modifier_patterns:
            if re.search(pattern, text):
                return False

        # 过滤：太长（超过 6 字，正常人名很少这么长）
        if len(text) > 6:
            return False

        # 过滤：以方位词开头
        if re.match(r'^(黑暗中|门外|远处|近处|角落里|窗前|床边|桌前)', text):
            return False

        return True

    def _resolve_pronoun_in_context(self, text: str) -> Optional[Dict]:
        """在上下文中解析代词。

        使用局部窗口（最近说话人 + 活跃度）来解析代词。

        Returns:
            {'name': str, 'reason': str, 'confidence': float} 解析成功
            {'weak_signal': True, 'pronoun': str, 'gender': str} 检测到代词但无法解析（P1-3）
            None 未检测到代词
        """
        import re
        from pipeline.pronoun_resolver import PRONOUNS

        found_pronoun = None
        found_gender = None

        for pronoun, gender in PRONOUNS.items():
            if pronoun in text:
                found_pronoun = pronoun
                found_gender = gender
                # 使用局部窗口解析代词
                result = self.pronoun_resolver.resolve_in_local_window(
                    gender,
                    self._recent_speakers,
                    character_activity={cid: data['weight'] for cid, data in self._character_activity.items()},
                    recent_mentions=self._recent_mentions,
                    context_before=text
                )
                if result and result.character:
                    return {
                        'name': result.character.name,
                        'reason': f'{pronoun}→{result.character.name}',
                        'confidence': result.confidence
                    }

        # P1-3: 代词消解失败传递弱信号
        # 检测到代词但局部窗口内无法解析时，返回弱信号而非 None
        # 后续步骤可利用此信号（如降低其他候选人置信度），但不强行匹配
        if found_pronoun:
            return {
                'weak_signal': True,
                'pronoun': found_pronoun,
                'gender': found_gender,
                'reason': f'检测到代词"{found_pronoun}"但无法解析'
            }

        return None

    def _match_candidate_to_character(
        self,
        candidate_name: str,
        context: str,
        skip_speech_check: bool = False,
        require_library: bool = False
    ) -> Optional[Character]:
        """将候选名字匹配到角色库。

        优先级：
        1. 锁定角色精确匹配（最高优先）
        2. 普通角色精确匹配 + 别名匹配
        3. 创建临时角色（兜底）

        注意：不再使用模糊匹配（在旁白中搜索角色名），
        因为这样会导致匹配到错误角色（旁白中提到的角色 ≠ 说话人）。

        设计原则：角色库优先，但只基于候选名字本身进行精确/别名匹配，
        不依赖旁白中的模糊搜索。
        当 require_library=True 时，不创建临时角色。
        """
        # 步骤1：精确匹配角色名（项目范围内）
        char = self.char_manager.get_character_by_name(candidate_name, self._current_project_id)
        if char:
            return char

        # 步骤2：别名匹配
        char = self.char_manager.get_character_by_alias(candidate_name, self._current_project_id)
        if char:
            return char

        # 步骤2.5：角色核心词后缀匹配（无新增硬编码）
        # H-20260516-10: 改用 get_eligible_characters
        from pipeline.descriptive_role_extractor import DescriptiveRoleExtractor

        all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
        if len(candidate_name) >= 4:
            for char in all_chars:
                if len(char.name) >= 2 and len(candidate_name) > len(char.name):
                    if candidate_name.endswith(char.name):
                        return char

        for core_word in DescriptiveRoleExtractor.ROLE_CORE_WORDS_SORTED:
            if len(candidate_name) > len(core_word) and candidate_name.endswith(core_word):
                exact_char = self.char_manager.get_character_by_name(core_word, self._current_project_id)
                if exact_char:
                    return exact_char
                for char in all_chars:
                    if core_word in char.name:
                        return char

        # 步骤3：创建临时角色（兜底）
        # require_library=True 时不创建临时角色
        if not require_library:
            temp_char = self._register_temporary_character(candidate_name, context, skip_speech_check)
            return temp_char
        return None

    @contextmanager
    def chapter_context(self, chapter_id: int):
        self.reset_activity()
        self._current_chapter_id = chapter_id
        try:
            yield self
        finally:
            self._current_chapter_id = None

    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        return self.hint_matcher.extract_speaker_hint(text)

    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        return self.hint_matcher._is_address_pattern(text, prefix)

    def extract_post_dialogue_hint(self, suffix: str) -> Optional[str]:
        return self.hint_matcher.extract_post_dialogue_hint(suffix)

    def extract_mentioned_characters(self, text: str) -> List[str]:
        """从文本中提取被提及的角色。
        
        改进：只分析旁白内容，不分析对话内容
        """
        narration = self._extract_narration(text)
        try:
            result = self.nlp.analyze(narration)
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
        return self.title_trigger_matcher.match_by_title(title)

    def match_by_semantic(self, sentence: str) -> Optional[MatchResult]:
        # H-20260516-10: 改用 get_eligible_characters
        all_chars = self.char_manager.get_eligible_characters()
        if not all_chars:
            return None

        profiles = []
        char_by_name = {}

        for char in all_chars:
            char_by_name[char.name] = char
            dialogue_context = self.get_dialogue_context(char.name)
            if dialogue_context:
                profiles.append((char.name, dialogue_context))
            else:
                profile_parts = []
                profile_parts.append(char.name)
                if char.aliases:
                    profile_parts.extend(char.aliases)
                if char.gender != "unknown":
                    profile_parts.append("他" if char.gender == "male" else "她")
                profile_parts.append(f"{char.name}说道")
                profile_parts.append(f"{char.name}点头")
                profile_parts.append(f"{char.name}看着")
                for alias in char.aliases:
                    profile_parts.append(f"{alias}道")

                profile_text = " ".join(profile_parts)
                profiles.append((char.name, profile_text))

        results = self.semantic_ranker.rank_with_profiles(
            sentence=sentence,
            profiles=profiles,
            threshold=self.l2_threshold,
        )

        if not results:
            return None

        best_char_name, best_score = results[0]
        matched_char = char_by_name.get(best_char_name)

        if matched_char:
            confidence = 0.6 + (best_score - self.l2_threshold) * 0.5
            confidence = max(0.6, min(confidence, 0.8))

            return MatchResult(
                character=matched_char,
                confidence=confidence,
                match_type='semantic',
            )

        return None

    def match_by_trigger_words(self, text: str, context: DialogueContext) -> Optional[MatchResult]:
        title_candidates = self.title_trigger_matcher.extract_title_trigger_candidates(text)
        for name, match_type_str, conf in title_candidates:
            char = self.char_manager.get_character_by_name(name)
            if char:
                return MatchResult(
                    character=char,
                    confidence=conf,
                    match_type=match_type_str
                )

        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char:
                idx = text.find(prev_char.name)
                if idx >= 0:
                    context_window = text[max(0, idx-20):idx+20+len(prev_char.name)]
                    if any(action in context_window for action in ACTION_TRIGGERS):
                        return MatchResult(
                            character=prev_char,
                            confidence=0.65,
                            match_type='trigger_action_prev_speaker'
                        )

        for addr in ADDRESS_TRIGGERS:
            if addr in text:
                # H-20260516-10: 改用 get_eligible_characters
                for char in self.char_manager.get_eligible_characters():
                    if addr in char.aliases or char.name.endswith(addr):
                        unique_recent = []
                        for recent in reversed(self._recent_speakers[-3:]):
                            if recent != char.name:
                                speaker = self.char_manager.get_character_by_name(recent)
                                if speaker and speaker not in unique_recent:
                                    unique_recent.append(speaker)

                        if len(unique_recent) == 1:
                            return MatchResult(
                                character=unique_recent[0],
                                confidence=0.70,
                                match_type='trigger_address'
                            )

        return None

    def match_by_pronoun(self, pronoun: str, context: DialogueContext) -> Optional[MatchResult]:
        gender = self.pronoun_resolver.resolve_by_pronoun(pronoun)
        if not gender:
            return None

        local_result = self.pronoun_resolver.resolve_in_local_window(
            gender,
            self._recent_speakers,
            character_activity={cid: data['weight'] for cid, data in self._character_activity.items()},
            recent_mentions=self._recent_mentions,
            context_before=context.context_before or ''
        )
        if local_result:
            return local_result

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
        # H-20260516-10: 改用 get_eligible_characters
        for char in self.char_manager.get_eligible_characters():
            if char.gender == gender:
                activity = self._get_activity_weight(char.id)
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
        return self.pronoun_resolver.resolve_in_local_window(gender, self._recent_speakers)

    def _collect_signal_candidates(self, context: DialogueContext, narration: str, possessive_excluded: set) -> List[Tuple[str, float, str]]:
        """并行收集所有信号源的候选说话人。

        收集后按置信度排序，返回 (name, confidence, source) 列表。
        """
        all_candidates: List[Tuple[str, float, str]] = []
        seen_names: set = set()

        # 信号源1: 正则说话人匹配（旁白中的"XX说道"）
        context_candidates = self._extract_context_speakers(
            narration,
            context.context_before or '',
            context.context_after or '',
            context.prefix_narration or ''
        )
        if context_candidates:
            for name, reason, confidence in context_candidates:
                if name not in seen_names and name not in possessive_excluded:
                    all_candidates.append((name, confidence, f'正则匹配({reason})'))
                    seen_names.add(name)

        # 信号源2: SRL ARG0 提取（语义角色标注）
        full_context = (context.context_before or '') + narration + (context.context_after or '')
        try:
            srl_arg0s = extract_srl_arg0s(full_context)
            for arg0 in srl_arg0s:
                name = arg0.text
                if name not in seen_names and name not in possessive_excluded and len(name) >= 2:
                    confidence = sm_config.CONFIDENCE_SRL_ARG0
                    all_candidates.append((name, confidence, f'SRL_ARG0(谓语={arg0.predicate})'))
                    seen_names.add(name)
        except Exception as e:
            logger.debug(f"SRL提取失败: {e}")

        # 信号源3: 主动 NER 提取角色名
        try:
            nlp = get_nlp()
            nlp_result = nlp.analyze(full_context)
            for entity in nlp_result.entities:
                if entity.type == 'PER':
                    name = entity.text
                    if name not in seen_names and name not in possessive_excluded and len(name) >= 2:
                        confidence = entity.confidence * sm_config.CONFIDENCE_NER_MULTIPLIER
                        all_candidates.append((name, confidence, f'NER_PER(conf={entity.confidence:.2f})'))
                        seen_names.add(name)
        except Exception as e:
            logger.debug(f"NER提取失败: {e}")

        # 信号源4: speaker_hint（显式提示）
        if context.speaker_hint and context.speaker_hint not in seen_names:
            if context.speaker_hint in ('他', '她'):
                hint_result = self.match_by_pronoun(context.speaker_hint, context)
                if hint_result:
                    all_candidates.append((hint_result.character.name, hint_result.confidence, 'speaker_hint(pronoun)'))
                    seen_names.add(hint_result.character.name)
            else:
                hint_result = self.match_by_name(context.speaker_hint)
                if hint_result:
                    all_candidates.append((hint_result.character.name, hint_result.confidence, 'speaker_hint'))
                    seen_names.add(hint_result.character.name)

        # 信号源5: mentioned_characters（被动NER）
        if context.mentioned_characters:
            for name in context.mentioned_characters:
                if name not in seen_names and name not in possessive_excluded and len(name) >= 2:
                    confidence = sm_config.CONFIDENCE_MENTIONED_CHARACTERS
                    all_candidates.append((name, confidence, 'mentioned_characters'))
                    seen_names.add(name)

        # 信号源6: 称呼推理
        if context.text:
            address_result = self._infer_from_address(context.text, context)
            if address_result and address_result.character.name not in seen_names:
                all_candidates.append((address_result.character.name, address_result.confidence, '称呼推理'))
                seen_names.add(address_result.character.name)

        # 信号源7: 触发词匹配
        if context.text:
            trigger_result = self.match_by_trigger_words(context.text, context)
            if trigger_result and trigger_result.character.name not in seen_names:
                all_candidates.append((trigger_result.character.name, trigger_result.confidence, '触发词匹配'))
                seen_names.add(trigger_result.character.name)

        # 信号源8: 角色库旁白匹配（兜底）
        lib_result = self._match_from_character_library(narration)
        if lib_result and lib_result.name not in seen_names and lib_result.name not in possessive_excluded:
            all_candidates.append((lib_result.name, sm_config.CONFIDENCE_CHARACTER_LIBRARY, '角色库旁白'))
            seen_names.add(lib_result.name)

        # 按置信度降序排序
        all_candidates.sort(key=lambda x: -x[1])
        return all_candidates

    def match_speaker(self, context: DialogueContext) -> Optional[MatchResult]:
        narration = self._extract_narration(
            context.text,
            context.context_before or '',
            context.context_after or ''
        )

        # N-4: 对话中"X的"所有格排除
        possessive_excluded = set()
        dialogue_text = context.dialogue or ''
        if dialogue_text:
            for m in re.finditer(r'([\u4e00-\u9fa5\u2027·]{2,4})的', dialogue_text):
                possessive_excluded.add(m.group(1))

        # H-20260515-05: 称呼排除增强
        if dialogue_text:
            vocative_match = re.match(r'^[\u201c\u201d\u2018\u2019"\'"]*([\u4e00-\u9fa5\u2027·]{2,4})[，,]', dialogue_text)
            if vocative_match:
                possessive_excluded.add(vocative_match.group(1))

        # 并行收集所有信号源候选
        all_candidates = self._collect_signal_candidates(context, narration, possessive_excluded)

        if not all_candidates:
            return None

        # 代词过滤 + 取最高置信度非代词候选
        selected = None
        for name, confidence, source in all_candidates:
            if name in ('他', '她', '它', '他们', '她们', '它们') or name in PRONOUNS:
                logger.debug(f"代词过滤: {name} 不应作为说话人")
                continue
            if name in ('UNKNOWN', '未知', 'unknown'):
                continue
            selected = (name, confidence, source)
            break

        if not selected:
            return None

        name, confidence, source = selected

        # 匹配角色库
        matched_char = self.char_manager.get_character_by_name(name, self._current_project_id)
        if not matched_char:
            matched_char = self.char_manager.get_character_by_alias(name, self._current_project_id)

        if matched_char:
            return MatchResult(
                character=matched_char,
                confidence=confidence,
                match_type=source,
            )

        return None

    def _infer_from_address(self, narration: str, context: DialogueContext) -> Optional[MatchResult]:
        addressed_char = self.address_trigger_matcher.find_addressed_character(narration)
        address_confidence = 0.9 if addressed_char else 0

        candidates = []

        if addressed_char:
            # H-20260516-10: 改用 get_eligible_characters
            for char in self.char_manager.get_eligible_characters():
                if char.id != addressed_char.id:
                    activity = self._get_activity_weight(char.id)
                    candidates.append((char, 0.6 + activity * 0.05, activity))

        if self._recent_mentions:
            for mentioned in reversed(self._recent_mentions[-5:]):
                char = self.char_manager.get_character_by_name(mentioned)
                if char and (not addressed_char or char.id != addressed_char.id):
                    activity = self._get_activity_weight(char.id)
                    candidates.append((char, 0.5 + activity * 0.03, activity))

        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char and (not addressed_char or prev_char.id != addressed_char.id):
                activity = self._get_activity_weight(prev_char.id)
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

    def _get_activity_weight(self, character_id: int) -> float:
        """P2-1: 获取角色的衰减后活动权重。"""
        from utils.config import ACTIVITY_DECAY_FACTOR
        if character_id not in self._character_activity:
            return 0.0
        activity_data = self._character_activity[character_id]
        time_diff = self._activity_counter - activity_data['last_update']
        # 指数衰减: weight = initial_weight * exp(-decay * time_diff)
        import math
        decayed_weight = activity_data['weight'] * math.exp(-ACTIVITY_DECAY_FACTOR * time_diff)
        return decayed_weight

    def update_activity(self, character_id: int, name: str):
        """更新角色活动度。P2-1: 添加指数衰减机制。"""
        from utils.config import ACTIVITY_INCREMENT, ACTIVITY_DECAY_FACTOR
        
        self._activity_counter += 1
        
        # 先对所有角色应用衰减（懒衰减：只在更新时计算）
        # 然后更新目标角色
        current_data = self._character_activity.get(character_id)
        if current_data:
            # 先应用衰减到当前权重
            import math
            time_diff = self._activity_counter - current_data['last_update']
            decayed_weight = current_data['weight'] * math.exp(-ACTIVITY_DECAY_FACTOR * time_diff)
            # 再加上新增量
            new_weight = decayed_weight + ACTIVITY_INCREMENT
        else:
            new_weight = ACTIVITY_INCREMENT
        
        self._character_activity[character_id] = {
            'weight': new_weight,
            'last_update': self._activity_counter
        }

        if name not in self._recent_speakers:
            self._recent_speakers.append(name)
            if len(self._recent_speakers) > 10:
                self._recent_speakers.pop(0)

    def _extract_action_subject(self, narration: str) -> Optional[str]:
        """N-2: 从旁白中提取动作主语。

        语言学依据：中文旁白中"角色名+动词"结构的主语通常是动作发出者
        来源：通用句法规则，非静态词表
        边界：只识别角色库中的角色名+说话/动作动词结构

        Returns:
            角色名 或 None
        """
        import re

        # H-20260516-10: 改用 get_eligible_characters
        all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
        if not all_chars:
            return None

        # 按角色名长度降序排序，优先匹配长名称
        char_names = sorted([c.name for c in all_chars], key=len, reverse=True)

        for char_name in char_names:
            if char_name not in narration:
                continue

            # 在角色名后面寻找说话/动作动词
            idx = narration.find(char_name)
            after_name = narration[idx + len(char_name):idx + len(char_name) + 15]

            # 检查是否紧跟说话动词或动作动词
            if re.match(r'^(?:说道|道|说|问|答|笑道|冷喝|喝道|冷笑|摇头|点头|起身|站起|坐下|看向|看向|走向|转身|翻开|端起|放下|拿起)', after_name):
                return char_name

        return None

    def cache_dialogue(self, character_name: str, dialogue_text: str):
        if character_name not in self._character_dialogues:
            self._character_dialogues[character_name] = []
        self._character_dialogues[character_name].append(dialogue_text)
        if len(self._character_dialogues[character_name]) > 20:
            self._character_dialogues[character_name] = self._character_dialogues[character_name][-20:]

    def get_dialogue_context(self, character_name: str) -> str:
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
        self._character_activity.clear()
        self._recent_speakers.clear()
        self._recent_mentions.clear()
        self._temp_char_cache.clear()

    def get_speaker_for_sentence(self, sentence: str, prev_speaker: str = None,
                                  chapter_id: int = None) -> Tuple[Optional[Character], str]:
        # 分离对话和旁白
        narration = self._extract_narration(sentence)
        
        # 提取说话人提示（基于完整句子，因为引号前的旁白可能包含说话人信息）
        speaker_hint, hint_type = self.extract_speaker_hint(sentence)
        
        # 提取被提及角色（只分析旁白）
        mentioned = self.extract_mentioned_characters(narration)

        if mentioned:
            self.update_mentions(mentioned)

        context = DialogueContext(
            text=narration,  # 只传递旁白内容，不传递完整句子
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

    def analyze_dialogue(self, text: str, chapter_id: int = None,
                         match_speaker_override=None) -> List[Tuple[str, Optional[Character]]]:
        dialogues = []
        seen_positions = set()

        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                dialogue = match.group(1)
                if not any(start <= p < end or p <= start < p + (end - start) for p in seen_positions):
                    dialogues.append((start, end, dialogue))
                    seen_positions.add(start)

        self._build_dialogue_cache(text, chapter_id)

        # 用 DialogueBoundaryDetector 过滤非对话引号内容
        try:
            from pipeline.dialogue_boundary_detector import DialogueBoundaryDetector
            detector = DialogueBoundaryDetector()
            all_quote_results = detector.detect_all(text)
            non_dialogue_positions = {
                (r.quote_info.start_pos, r.quote_info.end_pos)
                for r in all_quote_results if not r.is_dialogue
            }
            dialogues = [
                d for d in dialogues if (d[0], d[1]) not in non_dialogue_positions
            ]
        except Exception:
            pass

        # P0-7: v7.0 原则8 — _recent_speakers 不应在每次 analyze_dialogue 时清空
        # 角色活跃度、最近说话人、最近提及都应该跨段落/章节累积
        # 只有在项目级别 reset 时才清空（由调用方控制）

        dialogues.sort(key=lambda x: x[0])
        results = []
        prev_speaker = None
        last_successful_speaker = None
        prev_had_explicit_hint = False
        _match_speaker = match_speaker_override or self.match_speaker
        for i, (start, end, dialogue) in enumerate(dialogues):
            prefix_start = dialogues[i-1][1] if i > 0 else 0
            prefix = text[prefix_start:start].strip()

            suffix_end = dialogues[i+1][0] if i < len(dialogues) - 1 else len(text)
            suffix = text[end:suffix_end].strip()

            speaker_hint, hint_type = self.extract_speaker_hint(prefix + " " + suffix)
            mentioned = self.extract_mentioned_characters(prefix + " " + suffix)

            if mentioned:
                self.update_mentions(mentioned)

            context = DialogueContext(
                text=prefix + " " + dialogue + " " + suffix,
                dialogue=dialogue,
                speaker_hint=speaker_hint,
                prev_speaker=last_successful_speaker,
                mentioned_characters=mentioned,
                chapter_id=chapter_id,
                context_before=prefix,
                context_after=suffix,
            )

            match_result = _match_speaker(context)

            if match_result and match_result.character and match_result.character.name != '未知' and not match_result.character.name.startswith('未知_'):
                speaker = match_result.character
                self.update_activity(speaker.id, speaker.name)
                prev_speaker = speaker.name
                last_successful_speaker = speaker.name
                prev_had_explicit_hint = bool(speaker_hint)
            else:
                speaker = None
                prev_speaker = None
                prev_had_explicit_hint = False

            results.append((dialogue, speaker))

        return results

    def _build_dialogue_cache(self, text: str, chapter_id: int = None):
        all_dialogues = []
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                prefix_text = match.group(1).strip() if match.group(1) else ''
                dialogue_text = match.group(2) if match.lastindex and match.lastindex >= 2 else ''

                prefix_start = max(0, start - 50)
                suffix_end = min(len(text), end + 50)
                prefix = text[prefix_start:start].strip()
                suffix = text[end:suffix_end].strip()
                context = prefix + " " + dialogue_text + " " + suffix

                all_dialogues.append((start, context, dialogue_text))

        all_dialogues.sort(key=lambda x: x[0])

        for _, context, dialogue in all_dialogues:
            speaker_hint, _ = self.extract_speaker_hint(context)
            if speaker_hint and speaker_hint not in ('他', '她'):
                char = self.char_manager.get_character_by_name(speaker_hint, self._current_project_id)
                if not char:
                    char = self.char_manager.get_character_by_alias(speaker_hint)
                if char and getattr(char, 'name', None):
                    self.cache_dialogue(char.name, dialogue)


# ===== 内联自 character_name_validator.py（2026-05-14） =====

# 非人名词黑名单（技术债务）
# 问题：此列表基于经验枚举而非统计验证，应逐步迁移至 ContextDiversityValidator 的统计阈值
PER_BLACKLIST: Set[str] = {
    '一个', '两个', '三个', '这个', '那个', '什么', '怎么', '为什么',
    '今天', '明天', '昨天', '现在', '时候', '地方', '东西', '事情',
    '样子', '办法', '问题', '可能', '可以', '应该', '一定', '非常',
    '而且', '但是', '所以', '因为', '如果', '虽然', '然而',
}


class CharacterNameValidator:
    """角色名称验证器"""

    def __init__(self, nlp=None):
        self.nlp = nlp
        self._blacklist: Set[str] = PER_BLACKLIST | self._load_false_person_words()

    def _load_false_person_words(self) -> Set[str]:
        false_person_words = {
            '一声', '一眼', '一手', '一脚', '一头', '一边', '一半',
            '一切', '一起', '一定', '一点', '一些', '一般', '一样',
            '一直', '一向', '一旦', '一定', '一切',
            '突然', '忽然', '猛然', '骤然', '陡然', '赫然',
            '缓缓', '慢慢', '渐渐', '匆匆', '悄悄', '默默',
            '微微', '轻轻', '暗暗', '偷偷', '狠狠', '死死',
            '仿佛', '似乎', '好像', '犹如', '如同', '宛如',
        }
        return false_person_words

    def is_valid(self, name: str) -> bool:
        if not name or len(name) < 2 or len(name) > 6:
            return False
        if name in self._blacklist:
            return False
        if len(name) >= 2 and name[0] in SINGLE_CHAR_SURNAMES:
            return True
        non_person_suffixes = ['的', '了', '着', '过', '吗', '呢', '吧', '啊', '哦', '呀']
        if name[-1] in non_person_suffixes:
            return False
        return True

    def is_valid_speaker_candidate(self, name: str) -> bool:
        if not name or len(name) < 2 or len(name) > 20:
            return False
        if name in self._blacklist:
            return False
        return True

    def is_verb(self, name: str) -> bool:
        verb_suffixes = ['说道', '道', '说', '问', '喊', '叫', '笑', '叹',
                         '答', '应', '怒', '喝', '哼', '嚷', '跑', '走',
                         '看', '听', '想', '做', '打', '拿', '放', '吃']
        for suffix in verb_suffixes:
            if name.endswith(suffix) and len(name) > len(suffix):
                return True
        if self.nlp:
            try:
                result = self.nlp.analyze(name)
                for token in result.tokens:
                    if token.pos in ('v', 'vd', 'vf', 'vi', 'vl', 'vshi', 'vyou'):
                        return True
            except Exception:
                pass
        return False


# ===== 内联自 speaker_hint_matcher.py — SpeakerHintMatcher 类（2026-05-14） =====

class SpeakerHintMatcher:
    """说话人提示词匹配器"""

    def __init__(self, name_validator, nlp=None):
        self.name_validator = name_validator
        self.nlp = nlp

    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        if not text:
            return None, 'none'

        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(text)
            if match:
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                if self.name_validator.is_valid_speaker_candidate(name):
                    return name, 'explicit_hint'

        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start = match.start()
                prefix = text[max(0, start - 30):start].strip()
                for sp in SPEAKER_PATTERNS:
                    pm = sp.search(prefix)
                    if pm:
                        name = _clean_speaker_name(pm.group(1).strip(), self.nlp)
                        if self.name_validator.is_valid_speaker_candidate(name):
                            return name, 'prefix_hint'

        return None, 'none'

    def extract_speech_patterns(self, text: str) -> List[Tuple[str, str]]:
        if not text:
            return []

        results = []
        for pattern in SPEAKER_PATTERNS:
            for match in pattern.finditer(text):
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                hint = match.group(0).strip()
                if self.name_validator.is_valid_speaker_candidate(name):
                    results.append((name, hint))

        return results

    def extract_post_dialogue_hint(self, suffix: str) -> Optional[str]:
        if not suffix:
            return None

        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(suffix[:50])
            if match:
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                if self.name_validator.is_valid_speaker_candidate(name):
                    return name

        return None

    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        if not prefix:
            return False

        address_patterns = [
            re.compile(r'([\u4e00-\u9fa5]{2,6})[，,、\s]'),
            re.compile(r'([\u4e00-\u9fa5]{2,6})(?:啊|呀|呢|吧)[！!？?]?'),
        ]

        for pattern in address_patterns:
            match = pattern.search(prefix)
            if match:
                name = match.group(1).strip()
                if self.name_validator.is_valid_speaker_candidate(name):
                    return True

        return False


# ===== 内联自 self_reference_inferrer.py（2026-05-14） =====

# 自称词映射
#
# 用途：通过自称词（我、朕、本座等）推断说话人身份
# 来源：汉语称谓体系——古代官职谦辞与通用谦辞
# 边界：仅包含有明确语言学/文献依据的谦辞
# 硬性约束：上限15条，当前9条
SELF_REFERENCE_MAP: Dict[str, str] = {
    '我': 'first_person',
    '吾': 'first_person_classical',
    '朕': 'first_person_emperor',
    '本座': 'first_person_cultivation',
    '本王': 'first_person_king',
    '老夫': 'first_person_elder_male',
    '老身': 'first_person_elder_female',
    '奴家': 'first_person_humble_female',
    '妾身': 'first_person_concubine',
}

assert len(SELF_REFERENCE_MAP) <= 15, (
    f"SELF_REFERENCE_MAP 超出15条上限（当前{len(SELF_REFERENCE_MAP)}条），"
    "请审查是否越界，或重构为统计方法"
)


class SelfReferenceInferrer:
    """自称词推断器"""

    def __init__(self, char_manager):
        self.char_manager = char_manager

    def infer(self, text: str, context: str = '') -> List[Tuple[str, str, float]]:
        candidates = []

        for ref_word, ref_type in SELF_REFERENCE_MAP.items():
            if ref_word in text:
                known_chars = self._find_nearby_characters(context)
                if known_chars:
                    for char in known_chars[:1]:
                        candidates.append((char.name, f'自称词:{ref_word}→{char.name}', 0.75))
                else:
                    candidates.append(('未知', f'自称词:{ref_word}', 0.40))

        return candidates

    def infer_gender_from_context(self, name: str, context: str) -> str:
        male_indicators = ['他', '男子', '男人', '公子', '陛下', '王爷', '少爷',
                          '老夫', '朕', '本王', '本座']
        female_indicators = ['她', '女子', '女人', '小姐', '夫人', '姑娘', '娘娘',
                            '奴家', '妾身', '姑娘', '妹妹', '姐姐']

        male_count = sum(1 for w in male_indicators if w in context)
        female_count = sum(1 for w in female_indicators if w in context)

        if male_count > female_count:
            return 'male'
        elif female_count > male_count:
            return 'female'
        else:
            return 'unknown'

    def _find_nearby_characters(self, context: str) -> list:
        # H-20260516-10: 改用 get_eligible_characters
        all_chars = self.char_manager.get_eligible_characters()
        found = []
        for char in all_chars:
            if char.name in context:
                found.append(char)
                continue
            for alias in char.aliases:
                if alias in context:
                    found.append(char)
                    break
        return found


_speaker_matcher: Optional[SpeakerMatcher] = None


def get_speaker_matcher() -> SpeakerMatcher:
    global _speaker_matcher
    if _speaker_matcher is None:
        _speaker_matcher = SpeakerMatcher()
    return _speaker_matcher
