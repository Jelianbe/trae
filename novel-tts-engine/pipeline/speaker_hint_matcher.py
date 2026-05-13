# -*- coding: utf-8 -*-
"""说话人提示词匹配器：从上下文中提取显式说话人线索

设计原则：
1. SPEAKER_HINTS 基于中文常见说话提示词（如"道"、"说"、"问"等）
   中文说话提示词是有限集合，当前约30条已覆盖绝大多数场景。
"""

import re
import logging
from typing import List, Optional, Tuple, Set

logger = logging.getLogger(__name__)


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
    
    改进：对于英文双引号（左右相同），使用成对匹配逻辑，避免交错引号问题
    """
    patterns = []
    
    # 中文引号：左右不同，可以直接匹配
    for lq, rq in [('「', '」'), ('『', '』'), ('“', '”')]:
        patterns.append(re.compile(
            rf'{re.escape(lq)}'
            rf'([^{re.escape(rq)}]+?)'
            rf'{re.escape(rq)}'
        ))
    
    # 英文双引号：左右相同，需要特殊处理
    # 使用非贪婪匹配，确保正确处理连续引号对
    patterns.append(re.compile(r'"([^"]*?)"'))
    
    return patterns


DIALOGUE_PATTERNS = _build_quote_patterns()

# 说话人模式：匹配"XX道"、"XX说"等格式
# 关键：使用贪婪匹配 + 限定名字长度，确保"秦羽问道"提取为"秦羽"
#
# 用途：从"秦羽问道"等文本中提取说话人名字"秦羽"
# 来源：中文句法结构（主语+谓语+引语），网文常见说话模式统计
# 边界：仅匹配"说话"类动词，不匹配"思考"类动词
#       名字长度限制1-6字，覆盖绝大多数中文人名
SPEAKER_PATTERNS = [
    # 模式1：XX+复合动词（沉声道/低声道/高声道/冷冷道/淡淡道）
    re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:沉声道|低声道|高声道|冷冷道|淡淡道)[：:，,。\s]'),
    # 模式2：XX+单字动词（道/说/问/喊/叫/答/哼/笑/叹/怒/喝/嚷/骂）
    # 使用贪婪匹配 {1,6}，确保名字部分尽可能长，避免动词前的字被包含
    re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:道|说|问|喊|叫|答|应|笑|叹|怒|喝|哼|嚷|骂)[：:，,。\s]'),
]


class SpeakerHintMatcher:
    """说话人提示词匹配器"""

    def __init__(self, name_validator, nlp=None):
        self.name_validator = name_validator
        self.nlp = nlp

    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        """从文本中提取说话人提示词
        
        Returns:
            (speaker_name_or_None, hint_type)
        """
        if not text:
            return None, 'none'

        # 模式1：XX道、XX说 等显式提示
        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(text)
            if match:
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                if self.name_validator.is_valid_speaker_candidate(name):
                    return name, 'explicit_hint'

        # 模式2：从引号前的内容提取
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start = match.start()
                # 在引号前搜索说话人
                prefix = text[max(0, start - 30):start].strip()
                for sp in SPEAKER_PATTERNS:
                    pm = sp.search(prefix)
                    if pm:
                        name = _clean_speaker_name(pm.group(1).strip(), self.nlp)
                        if self.name_validator.is_valid_speaker_candidate(name):
                            return name, 'prefix_hint'

        return None, 'none'

    def extract_speech_patterns(self, text: str) -> List[Tuple[str, str]]:
        """从文本中提取所有说话人模式
        
        Returns:
            List of (name, hint_text)
        """
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
        """从对话后文本中提取说话人提示"""
        if not suffix:
            return None

        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(suffix[:50])  # 只看后50字
            if match:
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                if self.name_validator.is_valid_speaker_candidate(name):
                    return name

        return None

    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        """判断是否为称呼模式"""
        if not prefix:
            return False

        # 检查是否有"XX，你"或"XX啊"等称呼模式
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


def _clean_speaker_name(name: str, nlp=None) -> str:
    """清理说话人名称，提取真正的人名。
    
    设计原则：
    1. 优先使用 HanLP 词性标注，提取 NR(人名) 标记的 token
    2. 当 HanLP 不可用时，使用最小后缀清理（仅移除说话动词）
    3. 不再使用硬编码的 PREFIXES/FILTER_WORDS 列表
    
    来源：基于编码规则"优先使用句法、词性、标点等通用语言特征做判断"
    边界：仅处理说话动词后缀，不处理方向性前缀（由后续角色库匹配处理）
    """
    if not name:
        return name
    
    # 方法1：使用 HanLP 词性标注（优先）
    if nlp:
        try:
            result = nlp.analyze(name)
            # 提取 NR(人名) 标记的 token
            nr_tokens = [t.text for t in result.tokens if t.pos in ('NR', 'nr')]
            if nr_tokens:
                return ''.join(nr_tokens)
            
            # 如果没有 NR token，但有名词 token，尝试提取名词
            nn_tokens = [t.text for t in result.tokens if t.pos in ('NN', 'nn')]
            if nn_tokens:
                return ''.join(nn_tokens)
        except Exception:
            pass
    
    # 方法2：最小后缀清理（回退方案）
    # 来源：中文说话动词有限集合，基于中文标点规范和网文常见说话模式
    # 边界：仅包含明确的说话/回应类动词，不扩展至动作/表情类动词
    SPEECH_VERBS = [
        '冷冷道', '淡淡道', '沉声道', '低声道', '高声道',
        '说道', '问道', '答道', '笑道', '叹道', '怒道', '喝道', '哼道', '嚷道',
        '骂道', '回应道', '回答道', '接道', '续道',
        '轻声道', '低声说', '轻声说', '沉声说', '厉声道', '笑着道', '大叫道',
        '道', '说', '问', '喊', '叫', '答', '应', '笑', '叹', '怒',
        '喝', '哼', '嚷', '骂', '回',
    ]
    
    for verb in sorted(SPEECH_VERBS, key=len, reverse=True):
        if name.endswith(verb) and len(name) > len(verb):
            name = name[:-len(verb)]
            break
    
    return name
