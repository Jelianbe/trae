# -*- coding: utf-8 -*-
"""独立情绪提取模块 —— 方案 B 双管道中的管道2

设计原则：
1. 不依赖管道1（角色管道）的任何输出
2. 直接从原始文本提取情绪特征
3. 基于文本特征而非关键词匹配

情绪信号来源：
- 标点密度（感叹号密度、问号密度、省略号使用）
- 句式特征（感叹句、反问句、祈使句、短句连续）
- 情绪词（脏话、情绪副词、语气词）
- 重复模式（字符重复、词语重复）
- 大小写/全角半角（中文不适用，但全角标点有信息量）

目标：F1 >= 50%（当前规则系统 26.7%）
"""

import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# === Index-TTS 2 三层标注体系 ===

# L1 粗分类（3类）
EMOTION_CLASS_L1 = ['neutral', 'excited', 'subdued']

# L2 细分类（7类，含 unknown）
EMOTION_LABEL_L2 = ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral', 'unknown']

# unknown 判定阈值：所有情绪得分 <= 此值时归为 unknown
# 调整记录: 0.25→0.15 (2026-05-12)，降低 unknown 误判率，适配短文本场景
UNKNOWN_SCORE_THRESHOLD = 0.15

# unknown 判定最小文本长度：文本长度 < 此值时归为 unknown
UNKNOWN_MIN_TEXT_LENGTH = 5

# L3 8维情感向量维度名称（Index-TTS 2）
EMOTION_VECTOR_DIMS = ['happiness', 'anger', 'sadness', 'fear', 'disgust', 'melancholy', 'surprise', 'calm']


@dataclass
class EmotionResult:
    """情绪标注结果 —— 三层标注体系
    
    L1 粗分类: neutral / excited / subdued（用于规则系统训练目标）
    L2 细分类: joy / anger / sadness / surprise / fear / neutral（兼容旧系统）
    L3 情感向量: 8维向量，Index-TTS 2 直接消费
    """
    emotion_class: str                    # L1: neutral / excited / subdued
    emotion_label: str                    # L2: joy / anger / sadness / surprise / fear / neutral
    emotion_vector: List[float]           # L3: 8维向量 [happiness, anger, sadness, fear, disgust, melancholy, surprise, calm]
    emotion_text: str                     # 情感软指令描述（备选方案）
    confidence: float                     # 置信度 0.0~1.0
    intensity: float = 0.5                # 情绪强度 0.0~1.0（用于 L2 → L1 映射）


def map_l2_to_l1(emotion_label: str, intensity: float) -> str:
    """L2 → L1 映射（基于情绪强度）
    
    规则：
    - neutral → neutral（无论强度）
    - joy/surprise → excited（高强度）或 neutral（低强度）
    - anger → excited（高强度）或 subdued（低强度，压抑的愤怒）
    - sadness/fear → subdued（无论强度）
    
    Args:
        emotion_label: L2 细分类
        intensity: 情绪强度 0.0~1.0
    
    Returns:
        L1 粗分类
    """
    if emotion_label == 'neutral':
        return 'neutral'
    
    if emotion_label == 'unknown':
        return 'neutral'
    
    if emotion_label in ('sadness', 'fear'):
        return 'subdued'
    
    if emotion_label == 'anger':
        # 高强度愤怒 → excited（爆发式）
        # 低强度愤怒 → subdued（压抑式，冷怒）
        # 愤怒本质是激烈情绪，阈值从 0.6 降到 0.4
        return 'excited' if intensity >= 0.4 else 'subdued'
    
    if emotion_label in ('joy', 'surprise'):
        # 高强度 → excited
        # 低强度 → neutral（平静的喜悦/惊讶）
        return 'excited' if intensity >= 0.4 else 'neutral'
    
    return 'neutral'


def map_l2_to_vector(emotion_label: str, confidence: float, intensity: float) -> List[float]:
    """L2 + confidence → L3 8维向量动态计算
    
    Index-TTS 2 向量顺序: [happiness, anger, sadness, fear, disgust, melancholy, surprise, calm]
    
    Args:
        emotion_label: L2 细分类
        confidence: 置信度（影响主维度值），范围 0.0~1.0
        intensity: 情绪强度（影响向量值），范围 0.0~1.0
    
    Returns:
        8维情感向量，每个元素在 0.0~1.0 范围内
    """
    confidence = max(0.0, min(1.0, confidence))
    intensity = max(0.0, min(1.0, intensity))
    
    vector = [0.0] * 8
    
    primary_value = min(confidence * intensity, 1.0)
    
    if emotion_label == 'joy':
        vector[0] = primary_value
    elif emotion_label == 'anger':
        vector[1] = primary_value
    elif emotion_label == 'sadness':
        vector[2] = min(primary_value, 1.0)
        vector[5] = min(primary_value * 0.3, 1.0)
    elif emotion_label == 'fear':
        vector[3] = min(primary_value, 1.0)
        vector[2] = min(primary_value * 0.2, 1.0)
    elif emotion_label == 'surprise':
        vector[6] = primary_value
    elif emotion_label == 'neutral':
        vector[7] = 1.0
    elif emotion_label == 'unknown':
        vector[7] = 1.0
    
    vector = [max(0.0, min(v, 1.0)) for v in vector]
    
    return vector


def generate_emotion_text(emotion_label: str, intensity: float) -> str:
    """生成情感软指令描述
    
    Args:
        emotion_label: L2 细分类
        intensity: 情绪强度
    
    Returns:
        情感描述文本
    """
    intensity_desc = "强烈" if intensity >= 0.7 else "中等" if intensity >= 0.4 else "轻微"
    
    emotion_desc_map = {
        'joy': f"{intensity_desc}的喜悦",
        'anger': f"{intensity_desc}的愤怒",
        'sadness': f"{intensity_desc}的悲伤",
        'surprise': f"{intensity_desc}的惊讶",
        'fear': f"{intensity_desc}的恐惧",
        'neutral': "平静",
        'unknown': "平静",
    }
    
    return emotion_desc_map.get(emotion_label, "平静")


@dataclass
class EmotionFeatures:
    """文本情绪特征"""
    text: str                              # 原始文本
    exclamation_count: int = 0             # 感叹号数量
    question_count: int = 0                # 问号数量
    ellipsis_count: int = 0                # 省略号数量
    exclamation_density: float = 0.0       # 感叹号密度（每10字）
    avg_sentence_len: float = 0.0          # 平均句长
    has_dirty_words: bool = False          # 是否有脏话/粗口
    has_repetition: bool = False           # 是否有重复模式
    has_short_sentences: bool = False      # 是否有短句连续
    has_emotion_adverb: bool = False       # 是否有情绪副词
    has_emotion_verb: bool = False         # 是否有情绪动词
    is_exclamatory: bool = False           # 是否感叹句
    is_rhetorical: bool = False            # 是否反问句
    is_imperative: bool = False            # 是否祈使句
    has_mood_particle: bool = False        # 是否有语气词

    def to_ml_vector(self) -> List[float]:
        """将特征转换为 ML-ready 特征向量（14维）
        
        用于训练决策树/随机森林等分类器
        """
        return [
            self.exclamation_density,
            self.exclamation_count,
            self.question_count,
            float(self.has_dirty_words),
            float(self.has_emotion_verb),
            float(self.has_emotion_adverb),
            float(self.has_mood_particle),
            float(self.is_exclamatory),
            float(self.is_rhetorical),
            float(self.is_imperative),
            float(self.has_short_sentences),
            float(self.has_repetition),
            float(len(self.text)),
            self.avg_sentence_len,
        ]

    def extract_emotion_words(self, text: str) -> Dict[str, List[str]]:
        """提取文本中的情绪关键词"""


# 情绪脏词词典
#
# 用途：检测文本中的脏话/粗口，作为 anger 情绪的强信号
# 来源：通用中文脏话（社会通用，非文体特定）+ 网文高频粗口（基于斗破苍穹等统计）
# 边界：仅包含明确表达愤怒/侮辱的词汇，不包含方言俚语
#       【特定文体过拟合风险】"放肆"、"大胆"、"岂有此理"等古风词在非古风文体中可能误判
#       【特定文体过拟合风险】"死无葬身之地"等极端词仅在热血/玄幻文中高频
DIRTY_WORDS = [
    '滚', '滚蛋', '混蛋', '王八蛋', '废物', '垃圾', '傻逼', '蠢货',
    '该死', '操', '他妈', '妈的', '草', '卧槽', '靠', '日',
    '贱人', '畜生', '狗东西', '杂种', '废物', '蠢材',
    '放肆', '大胆', '岂有此理', '混蛋', '找死', '活腻',
]

# 情绪副词/程度词
#
# 用途：检测文本中的情绪强度修饰词，辅助判断情绪类型和强度
# 来源：通用中文程度副词（现代汉语语法）+ 网文高频情绪副词
# 边界：仅包含修饰情绪/动作的副词，不包含纯逻辑副词（如"因此"、"所以"）
#       "冷冷"、"淡淡"等词同时出现在 anger 和 neutral 场景，需结合上下文判断
EMOTION_ADVERBS = [
    '极其', '非常', '特别', '十分', '格外', '分外',
    '狠狠', '猛地', '突然', '猛然', '骤然', '顿时',
    '不禁', '不由', '忍不住', '情不自禁',
    '愤怒地', '激动地', '颤抖地', '嘶吼地', '咆哮地',
    '冷冷', '淡淡', '微微', '轻轻',
    '咬牙切齿', '怒火中烧', '气急败坏',
]

# 情绪动词
#
# 用途：检测文本中的情绪行为动词，作为情绪分类的辅助信号
# 来源：通用中文情绪动词（现代汉语语法）+ 网文高频描写词
# 边界：仅包含表达情绪的外显行为，不包含内心活动（如"想"、"觉得"）
EMOTION_VERBS = [
    '怒吼', '咆哮', '嘶吼', '怒吼', '怒骂', '怒吼',
    '痛哭', '抽泣', '哽咽', '流泪', '落泪',
    '大笑', '狂笑', '冷笑', '嘲笑', '讥笑',
    '颤抖', '发抖', '哆嗦', '战栗',
    '瞪眼', '怒视', '盯着', '注视',
    '抓紧', '握紧', '捏紧', '拍打',
]

# 语气词（句末，表达情绪强度）
#
# 用途：检测句末语气词，辅助判断情绪强度和类型
# 来源：通用中文语气词（现代汉语语法）
# 边界：仅包含句末语气词，不包含句首/句中连词
MOOD_PARTICLES = ['啊', '呀', '哇', '呢', '吧', '哦', '唉', '哼', '呵', '哈']

# 厌恶词表
#
# 用途：检测文本中的厌恶/鄙视类词汇，作为 disgust 情绪的信号
# 来源：通用中文厌恶词（社会通用）+ 网文高频鄙视词
# 边界：仅包含明确表达厌恶/鄙视的词汇
#       【特定文体过拟合风险】"龌龊"、"下作"等古风词在非古风文体中可能误判
_DISGUST_KEYWORDS = [
    '恶心', '厌恶', '嫌弃', '反感', '讨厌', '作呕', '反胃',
    '呕吐', '吐了', '倒胃口', '膈应', '恶心人',
    '龌龊', '下流', '卑鄙', '无耻', '下作', '令人发指',
    '嗤之以鼻', '不屑', '鄙夷', '蔑视', '轻蔑',
]

# 祈使句模式
#
# 用途：检测祈使句（命令/请求），作为 anger 或 surprise 的辅助信号
# 来源：通用中文祈使句语法结构（现代汉语语法）
# 边界：仅包含祈使语气标记，不包含陈述句
IMPERATIVE_PATTERNS = [
    r'^(给我|马上|立刻|立即|赶紧|快点|快|去|来)',
    r'(准备战斗|集合|防御|进攻|撤退|出手|停下|闭嘴|滚开|让开|冲锋|净化|杀|受死|去死|吃招)',
    r'(不要|别|不准|禁止|严禁)',
]

# 反问句模式
#
# 用途：检测反问句，作为 anger 或 surprise 的辅助信号
# 来源：通用中文反问句语法结构（现代汉语语法）
# 边界：仅包含反问语气标记，不包含一般疑问句
RHETORICAL_PATTERNS = [
    r'难道.*[？?]',
    r'怎么.*[？?]',
    r'岂.*[？?]',
    r'谁.*[？?]',
    r'谁又.*[？?]',
    r'难道不是',
    r'怎么可能',
    r'怎么会有',
    r'[你他她我]又.*[？?]',
]

# 感叹句模式
#
# 用途：检测感叹句，作为 surprise 或 happiness 的辅助信号
# 来源：通用中文感叹句语法结构（现代汉语语法）
# 边界：仅包含感叹语气标记，不包含一般陈述句
EXCLAMATORY_PATTERNS = [
    r'^(太好了|太棒了|好极了|妙啊|完美|厉害)',
    r'(哈哈|哈哈哈|呵呵|嘻嘻)',
    r'^[哇啊哦唉哼嘿][！!]{1,3}',
]

# 引导词提取模式（从 EmotionTagger 迁移）
#
# 用途：提取紧邻引号的动词短语（如"冷笑道"、"急切的道"），作为情绪判断的强信号
# 来源：网文对话引导词高频模式（基于 GT 数据统计）
# 边界：仅匹配引号前 5 字内的引导词，不匹配远距离描写
GUIDE_PHRASE_PATTERN = re.compile(
    r'([\u4e00-\u9fa5]{0,5}?(?:道|说|问|喊|叫|骂|笑|叹|答|应|怒|喝|哼|嚷)[：:，。！!]?)'
)

QUOTE_START_PATTERN = re.compile(r'[""]')

# 特殊笑类映射（从 EmotionTagger 迁移）
# 冷笑 → anger，苦笑 → sadness
SPECIAL_LAUGHTER_MAP = {
    '冷笑': 'anger',
    '苦笑': 'sadness',
}

# 程度副词（从 EmotionTagger 迁移，用于情绪强度检测）
DEGREE_ADVERBS_STRONG = ["非常", "极其", "极度", "十分", "格外", "分外", "异常", "太", "极为", "无比"]
DEGREE_ADVERBS_MILD = ["有点", "略微", "微微", "稍稍", "稍微", "略有", "稍显"]


class EmotionExtractor:
    """独立情绪提取器 —— 不依赖角色管道，直接从原始文本提取情绪特征"""
    
    # NEGATION_WORDS
    #
    # 用途：用于情绪极性反转检测的否定词列表
    # 来源：通用中文否定词（现代汉语语法封闭集）
    # 边界：仅包含否定副词，不包含否定义动词（"拒绝"、"否认"——这些在DIRTY_WORDS/动词中处理）
    #       不包含否定义名词（"否定"、"否认"）
    # 上限：约 10 条，固定封闭集
    # 更新日期：2026-05-15
    # 维护者：R-016 规则
    NEGATION_WORDS = ['不', '没', '别', '莫', '勿', '并非', '从不', '毫无', '没有']
    
    def __init__(self):
        # 预编译正则
        # 脏词正则：
        # - 多字词：直接匹配
        # - 单字脏词：仅对真正有歧义的字（草、日）使用词边界
        #   "草"可能匹配"草木"，"日"可能匹配"日期"
        #   但"滚"、"靠"、"操"几乎总是作为脏词单独使用
        SINGLE_CHAR_DIRTY = {'草', '日'}  # 仅这些需要词边界
        dirty_patterns = []
        for w in DIRTY_WORDS:
            if len(w) == 1 and w in SINGLE_CHAR_DIRTY:
                dirty_patterns.append(r'(?<![一-龥])' + re.escape(w) + r'(?![一-龥])')
            else:
                dirty_patterns.append(re.escape(w))
        self._dirty_re = re.compile('|'.join(dirty_patterns))
        self._adverb_re = re.compile('|'.join(re.escape(w) for w in EMOTION_ADVERBS))
        self._verb_re = re.compile('|'.join(re.escape(w) for w in EMOTION_VERBS))
        self._mood_re = re.compile('|'.join(re.escape(w) for w in MOOD_PARTICLES))
        self._imperative_res = [re.compile(p, re.IGNORECASE) for p in IMPERATIVE_PATTERNS]
        self._rhetorical_res = [re.compile(p, re.IGNORECASE) for p in RHETORICAL_PATTERNS]
        self._exclamatory_res = [re.compile(p, re.IGNORECASE) for p in EXCLAMATORY_PATTERNS]
        self._repetition_re = re.compile(r'(.)\1{2,}')  # 字符重复 3+ 次
        # 否定模式：检测否定词+情绪词的组合
        self._negation_re = re.compile(
            r'(?:' + '|'.join(re.escape(w) for w in self.NEGATION_WORDS) + r').{0,4}'
            r'(?:[生气愤怒害怕恐惧悲伤哭恨讨厌喜欢笑高兴开心激动紧张担心])'
        )
    
    def extract_features(self, text: str) -> EmotionFeatures:
        """提取文本的情绪特征"""
        features = EmotionFeatures(text=text)
        
        # 基础标点统计
        features.exclamation_count = len(re.findall(r'[！!]', text))
        features.question_count = len(re.findall(r'[？?]', text))
        features.ellipsis_count = len(re.findall(r'\.{3,}|…+', text))
        
        # 感叹号密度（每10字）
        char_count = max(1, len(text))
        features.exclamation_density = features.exclamation_count * 10 / char_count
        
        # 平均句长
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            features.avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
        
        # 短句连续检测（连续2个以上<5字的句子）
        short_count = sum(1 for s in sentences if len(s) <= 4)
        features.has_short_sentences = short_count >= 2
        
        # 脏话检测
        features.has_dirty_words = bool(self._dirty_re.search(text))
        
        # 重复模式
        features.has_repetition = bool(self._repetition_re.search(text))
        
        # 情绪副词/动词
        features.has_emotion_adverb = bool(self._adverb_re.search(text))
        features.has_emotion_verb = bool(self._verb_re.search(text))
        
        # 语气词检测
        features.has_mood_particle = bool(self._mood_re.search(text))
        
        # 句式类型
        features.is_exclamatory = any(r.search(text) for r in self._exclamatory_res)
        features.is_rhetorical = any(r.search(text) for r in self._rhetorical_res)
        features.is_imperative = any(r.search(text) for r in self._imperative_res)
        
        return features
    
    def _extract_guide_phrase(self, text: str) -> str:
        """精确引导词提取：只提取紧邻引号的动词短语
        
        策略：
        1. 找到左引号位置
        2. 在引号前 10 字内搜索动词短语（道/说/问/笑/叹/怒等）
        3. 如果找到，返回引导词；否则返回空字符串
        
        Returns:
            str: 引导词（如"冷笑道"、"急切的道"），未找到返回空字符串
        """
        quote_match = QUOTE_START_PATTERN.search(text)
        if not quote_match:
            return ""
        
        quote_pos = quote_match.start()
        prefix = text[max(0, quote_pos - 10):quote_pos]
        
        # 使用 findall 找到所有匹配，取最靠近引号的那个
        matches = GUIDE_PHRASE_PATTERN.findall(prefix)
        if matches:
            return matches[-1]  # 最后一个匹配最靠近引号
        
        return ""
    
    def _check_special_laughter(self, text: str) -> Optional[str]:
        """特殊笑类关键词检查（优先级：冷笑 > 苦笑）
        
        Returns:
            情绪标签（anger/sadness），未匹配返回 None
        """
        if '冷笑' in text:
            return 'anger'
        if '苦笑' in text:
            return 'sadness'
        return None
    
    def _apply_guide_phrase_bonus(self, text: str, scores: Dict[str, float]) -> None:
        """引导词情绪加分：基于引导词内容给对应情绪加分
        
        引导词是紧邻对话引号的动词短语，通常是作者直接给出的情绪提示，
        应作为强信号（加分幅度高于普通关键词匹配）。
        """
        guide_phrase = self._extract_guide_phrase(text)
        if not guide_phrase:
            return
        
        special = self._check_special_laughter(guide_phrase)
        if special:
            scores[special] += 0.5
            return
        
        if '怒' in guide_phrase or '骂' in guide_phrase or '吼' in guide_phrase:
            scores['anger'] += 0.4
        elif '哭' in guide_phrase or '叹' in guide_phrase or '泣' in guide_phrase:
            scores['sadness'] += 0.4
        elif '笑' in guide_phrase:
            if '微' in guide_phrase or '轻' in guide_phrase:
                scores['neutral'] += 0.2
            else:
                scores['joy'] += 0.3
        elif '喊' in guide_phrase or '叫' in guide_phrase or '嚷' in guide_phrase:
            scores['surprise'] += 0.3
        elif '问' in guide_phrase:
            scores['surprise'] += 0.2
    
    def classify(self, text: str, context_hint: Optional[str] = None, context_confidence: float = 0.0) -> EmotionResult:
        """基于情绪特征分类
        
        Args:
            text: 待分类文本
            context_hint: 上下文情绪提示（上一句的情绪标签）
                          用于处理单句无情绪信号但上下文决定情绪的 case
            context_confidence: 上下文情绪的置信度
                                仅当 >= 0.5 时才触发上下文干预
        
        返回: EmotionResult
        """
        features = self.extract_features(text)
        
        # === 否定词检测 ===
        # 检测否定词+情绪词的组合，如果命中则降低对应情绪的得分
        has_negation = bool(self._negation_re.search(text))
        
        # 情绪打分
        scores = {
            'joy': 0.0,
            'anger': 0.0,
            'sadness': 0.0,
            'surprise': 0.0,
            'fear': 0.0,
            'neutral': 0.0,  # 基础分降为 0，让 neutral 完全靠正向特征竞争
        }
        
        # === ANGER 愤怒信号 ===
        # 脏话/粗口
        if features.has_dirty_words:
            scores['anger'] += 0.5
        # 感叹号密度高 + 祈使句
        if features.exclamation_density > 0.3 and features.is_imperative:
            scores['anger'] += 0.3
        # 祈使句 + 感叹号（非恐惧场景）
        if features.is_imperative and features.exclamation_count >= 1:
            if '过来' not in text and '伤害' not in text and '别伤害' not in text:
                scores['anger'] += 0.15
        # 情绪动词（怒吼、咆哮等）
        if features.has_emotion_verb:
            scores['anger'] += 0.2
        # 连续短句 + 高感叹号
        if features.has_short_sentences and features.exclamation_count >= 2:
            scores['anger'] += 0.2
        # 宣言类愤怒（"三十年河东，三十年河西"、"放肆"等）
        if re.search(r'(河东|河西|放肆|狂妄|大胆|岂敢)', text):
            scores['anger'] += 0.4
        # 威胁/诅咒类愤怒
        if re.search(r'(死无葬身之地|自寻死路|找死|活腻|不得好死|碎尸万段|千刀万剐)', text):
            scores['anger'] += 0.5
        # 叛逆/背叛类愤怒
        if re.search(r'(背叛|叛徒|逆贼|谋反|造反)', text):
            scores['anger'] += 0.4
        # 仇恨类愤怒
        if re.search(r'(恨|仇恨|仇人|仇家|血债|血海深仇)', text):
            scores['anger'] += 0.4
        
        # === FEAR 恐惧信号 ===
        # 情绪动词（颤抖、发抖等）
        if features.has_emotion_verb and ('颤抖' in text or '发抖' in text or '哆嗦' in text):
            scores['fear'] += 0.4
        # 省略号（犹豫、紧张）
        if features.ellipsis_count >= 2:
            scores['fear'] += 0.2
        # 短句连续 + 问号
        if features.has_short_sentences and features.question_count >= 1:
            scores['fear'] += 0.2
        # "害怕"直接出现
        if '害怕' in text or '恐惧' in text or '别伤害' in text:
            scores['fear'] += 0.3
        # "不要" + 省略号/问号
        if ('不要' in text or '别' in text) and (features.ellipsis_count >= 1 or features.question_count >= 1):
            # 如果同时有"离开"，偏向 sadness
            if '离开' in text or '对不起' in text or '难过' in text:
                scores['sadness'] += 0.3
            else:
                scores['fear'] += 0.3
        # "不要过来"类恐惧
        if '不要过来' in text or '别过来' in text:
            scores['fear'] += 0.4
        # "恐怖"直接出现
        if '恐怖' in text:
            scores['fear'] += 0.4
        # 求饶类恐惧
        if re.search(r'(饶命|求饶|饶了我|放过|不要杀|别杀|救命|求求)', text):
            scores['fear'] += 0.5
        # 危险/威胁类恐惧
        if re.search(r'(危险|快跑|逃命|躲开|小心)', text):
            scores['fear'] += 0.4
        
        # === SADNESS 悲伤信号 ===
        # 叹词开头（唉、呜）
        if text.startswith(('唉', '呜', '呜呜', '唉声叹气')):
            scores['sadness'] += 0.3
        # 省略号
        if features.ellipsis_count >= 1:
            scores['sadness'] += 0.2
        # 情绪副词（不禁、不由等）
        if features.has_emotion_adverb and ('不禁' in text or '不由' in text):
            scores['sadness'] += 0.2
        # "难过"、"离开"、"不要"
        if '难过' in text or '离开' in text or '对不起' in text:
            scores['sadness'] += 0.2
        # 失去/离别类悲伤
        if re.search(r'(最后一面|见不到|回不去|再也见|永别|死别|生离)', text):
            scores['sadness'] += 0.5
        # 遗憾/后悔类悲伤
        if re.search(r'(遗憾|后悔|来不及|没能|本该|早知道)', text):
            scores['sadness'] += 0.4
        # 哭泣类悲伤
        if re.search(r'(哭|泪|泣|泪流|泪如|泪下|落泪|掉泪)', text):
            scores['sadness'] += 0.4
        # 亲人称呼 + 语气词（"我的儿啊"、"我的孩儿"等）
        if re.search(r'(我的儿|我的孩|我的女|我的妻|我的夫|儿啊|孩儿|女儿啊)', text):
            scores['sadness'] += 0.5
        # 放手/成全类悲伤
        if re.search(r'(走吧|放手|成全|趁我|别管我)', text):
            scores['sadness'] += 0.3
        
        # === SURPRISE 惊讶信号 ===
        # 反问句
        if features.is_rhetorical:
            scores['surprise'] += 0.3
        # 问号密度高
        if features.question_count >= 2:
            scores['surprise'] += 0.2
        # "居然"、"竟然"、"天哪"（删除"什么"，它是常用词，过度匹配）
        if re.search(r'(居然|竟然|天哪|竟然复活)', text):
            scores['surprise'] += 0.4
        # 高感叹号 + 非愤怒词
        if features.exclamation_count >= 2 and not features.has_dirty_words:
            scores['surprise'] += 0.2
        # "这" + 感叹号（"这是什么？""这怎么可能？"）
        if re.search(r'这.*[！!]', text) and features.exclamation_count >= 1:
            scores['surprise'] += 0.1
        # "太可怕了"、"太厉害了" 类惊叹
        if re.search(r'太(可怕|厉害|惊人|恐怖|强大)了', text):
            scores['surprise'] += 0.4
        # "还活着"、"竟然"类惊讶
        if '还活着' in text or '没死' in text or '不敢相信' in text:
            scores['surprise'] += 0.4
        if re.search(r'(竟然|居然)', text):
            scores['surprise'] += 0.3
        # "难道...真的"类惊讶
        if re.search(r'(难道|怎会|怎可能|怎么可能)', text):
            scores['surprise'] += 0.4
        # "真的" + 省略号/问号（疑惑/惊讶）
        if re.search(r'真的[……?？]', text):
            scores['surprise'] += 0.3
        
        # === JOY 喜悦信号 ===
        # 感叹句模式（哈哈、太好了等）
        if features.is_exclamatory:
            scores['joy'] += 0.4
        # 高感叹号密度（非愤怒场景）
        if features.exclamation_density > 0.3 and not features.has_dirty_words and not features.is_imperative:
            scores['joy'] += 0.2
        # 笑声/笑
        if re.search(r'(哈哈|呵呵|嘻嘻|大笑|微笑)', text):
            scores['joy'] += 0.3
        # 重复模式（高兴时常见）
        if features.has_repetition:
            scores['joy'] += 0.1
        # "完美"、"赢了"、"太好了"
        if re.search(r'(完美|赢了|太好了|太棒了)', text):
            scores['joy'] += 0.3
        # "哼"、嘲讽、轻蔑（网文常见 joy/anger 混合，偏向 joy 因为通常表示不屑/轻松）
        if text.startswith('哼') and ('本事' in text or '就这' in text or '这点' in text):
            scores['joy'] += 0.4
        # 笑声/笑（补充"笑"字）
        if '笑' in text and not ('冷笑' in text or '嘲笑' in text):
            scores['joy'] += 0.2
        # 胜利/成就类喜悦
        if re.search(r'(冠军|胜利|赢了|成功|终于|梦寐以求|喜事|好消息)', text):
            scores['joy'] += 0.5
        # 庆祝/祝福类喜悦
        if re.search(r'(恭喜|祝贺|庆祝|万岁|干杯|庆祝)', text):
            scores['joy'] += 0.4
        # 幸福/满足类喜悦
        if re.search(r'(幸福|满足|开心|高兴|快乐|美好)', text):
            scores['joy'] += 0.4
        
        # === 否定词惩罚 ===
        # 如果检测到否定词+情绪词的组合，降低该情绪的得分
        # 例如："不生气" → anger 分数降低，"不害怕" → fear 分数降低
        if has_negation:
            # 否定词会削弱所有情绪信号，使结果偏向 neutral
            for key in scores:
                if key != 'neutral':
                    scores[key] *= 0.5  # 所有情绪分数减半
        
        # === 特殊否定模式识别 ===
        # "不" + 情绪词（如"不生气"、"不怕"、"不难过"）
        if '不生气' in text or '不愤怒' in text or '不恨' in text:
            scores['anger'] *= 0.3  # 明确否定，大幅降低
        if '不害怕' in text or '不怕' in text or '不恐惧' in text:
            scores['fear'] *= 0.3
        if '不难过' in text or '不悲伤' in text or '不伤心' in text:
            scores['sadness'] *= 0.3
        if '不高兴' in text or '不开心' in text or '不快乐' in text:
            scores['joy'] *= 0.3
        if '不惊讶' in text or '不惊奇' in text:
            scores['surprise'] *= 0.3
        
        # === FEAR 恐惧信号（补充）===
        # 恐慌/惊慌类
        if re.search(r'(恐慌|惊慌|惊恐|惊惶|慌张|慌乱)', text):
            scores['fear'] += 0.4
        # 心跳加速/呼吸急促
        if re.search(r'(心跳|心慌|心悸|呼吸困难|喘不过气|屏住呼吸)', text):
            scores['fear'] += 0.3
        # 冷汗/腿软
        if re.search(r'(冷汗|腿软|脚软|毛骨悚然|脊背发凉|后背发凉)', text):
            scores['fear'] += 0.3
        # 尖叫/惊呼
        if re.search(r'(尖叫|惊呼|惨叫|失声)', text):
            scores['fear'] += 0.3
        # 鬼怪/超自然恐惧
        if re.search(r'(鬼|鬼魂|幽灵|妖怪|魔物|邪灵|怨灵|黑影|鬼影)', text):
            scores['fear'] += 0.3
        # 死亡/杀戮威胁
        if re.search(r'(杀了你|弄死你|干掉|灭口|灭门|屠城)', text):
            scores['fear'] += 0.5
        # 绝望/无助
        if re.search(r'(绝望|无助|无路可退|走投无路|没有办法|束手无策)', text):
            scores['fear'] += 0.3
        # 退缩/躲避
        if re.search(r'(后退|退后|躲避|闪避|蜷缩|缩在|藏在)', text):
            scores['fear'] += 0.2
        
        # === NEUTRAL 中性信号（正向特征）===
        # neutral 不是垃圾桶，它有自己的特征
        # 调参版本：上限 0.5，只保留两个核心信号
        
        neutral_score = 0.0
        
        # 信号1：句号结尾 + 无感叹号 + 无问号
        if text.endswith('。') and features.exclamation_count == 0 and features.question_count == 0:
            neutral_score += 0.2
        
        # 信号2：无情绪词命中
        has_emotion_signals = (
            features.has_dirty_words or 
            features.has_emotion_verb or 
            features.has_emotion_adverb or
            features.is_exclamatory or
            features.is_rhetorical or
            features.is_imperative
        )
        if not has_emotion_signals:
            neutral_score += 0.2
        
        # 归一化 neutral 分数，上限 0.25
        # 低于任何情绪的强信号阈值，但仍高于完全无信号时的兜底线
        neutral_score = min(neutral_score, 0.25)
        scores['neutral'] = neutral_score
        
        # === 引导词情绪加分（从 EmotionTagger 迁移）===
        self._apply_guide_phrase_bonus(text, scores)
        
        # === 上下文干预 ===
        # 置信度门控：仅当前句最高分<=0.25且前句置信度>=0.3时，才继承前句情绪
        # 门控阈值从 0.5 降到 0.3，因为很多情绪句的置信度在 0.3-0.5 之间
        if context_hint and context_hint in ('sadness', 'fear', 'anger', 'joy', 'surprise'):
            if context_confidence >= 0.3:
                # 当前句最高分 <= 0.25 时，上下文干预生效
                current_max = max(scores.values())
                if current_max <= 0.25:
                    # 继承上下文情绪，给予 0.4 的基础分（超过 neutral 上限 0.25）
                    scores[context_hint] += 0.4
        
        # 取最高分（先 clamp 所有分数到 [0.0, 1.0]）
        for emotion_key in scores:
            scores[emotion_key] = min(scores[emotion_key], 1.0)
        best_emotion = max(scores, key=scores.get)
        best_score = scores[best_emotion]
        
        # === 祈使句误判修复：愤怒 → 恐惧豁免 ===
        # 当 anger 分数较高时，如果文本包含明确恐惧信号且 fear 分数不为零，
        # 说明这是恐惧驱动的祈使句（"快跑！"、"别过来！"），不是愤怒
        if best_emotion == 'anger' and best_score >= 0.4:
            fear_signals = ['快跑', '逃', '别过来', '救命', '危险', '求饶', '饶命', '别杀', '别伤害']
            has_fear_signal = any(signal in text for signal in fear_signals)
            if has_fear_signal and scores.get('fear', 0) > 0.1:
                best_emotion = 'fear'
                best_score = max(best_score * 0.8, scores['fear'])
        
        # unknown 判定：所有情绪得分 <= 阈值 且无引导词加分
        # unknown 表示"无法判断情绪类型"，不等于"中性"
        # 如果 best_emotion 已经是 neutral（有正向特征支持），保持 neutral
        if len(text) == 0:
            best_emotion = 'neutral'
            best_score = 0.3
        elif best_score <= UNKNOWN_SCORE_THRESHOLD and len(text) >= UNKNOWN_MIN_TEXT_LENGTH:
            # 只在 best_emotion 不是 neutral 时才判定为 unknown
            # neutral 本身就是一种明确的情绪判断，不需要转为 unknown
            if best_emotion != 'neutral':
                best_emotion = 'unknown'
                best_score = 0.3
        
        # 归一化置信度
        confidence = min(best_score, 0.95)
        
        # 计算情绪强度（基于分数）
        # 分数越高，强度越大
        intensity = min(best_score / 0.8, 1.0)  # 0.8 分以上为高强度
        
        # L2 → L1 映射
        emotion_class = map_l2_to_l1(best_emotion, intensity)
        
        # L2 + confidence → L3 向量
        emotion_vector = map_l2_to_vector(best_emotion, confidence, intensity)
        
        # 生成情感描述
        emotion_text = generate_emotion_text(best_emotion, intensity)
        
        return EmotionResult(
            emotion_class=emotion_class,
            emotion_label=best_emotion,
            emotion_vector=emotion_vector,
            emotion_text=emotion_text,
            confidence=confidence,
            intensity=intensity,
        )
    
    def classify_simple(self, text: str) -> Tuple[str, float]:
        """简化分类接口（兼容旧代码）
        
        返回: (emotion_label, confidence)
        """
        result = self.classify(text)
        return result.emotion_label, result.confidence
    
    def batch_classify(self, texts: List[str]) -> List[EmotionResult]:
        """批量分类"""
        return [self.classify(t) for t in texts]


# 全局单例（双重检查锁，线程安全）
_extractor: Optional[EmotionExtractor] = None
_extractor_lock = threading.Lock()


def get_emotion_extractor() -> EmotionExtractor:
    global _extractor
    if _extractor is None:
        with _extractor_lock:
            if _extractor is None:
                _extractor = EmotionExtractor()
    return _extractor


def reset_emotion_extractor() -> None:
    global _extractor
    with _extractor_lock:
        _extractor = None
