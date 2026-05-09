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
#
# 用途：匹配"XX道"、"XX说"等显式说话人提示模式
# 来源：中文标点规范 GB/T 15834-2011 + 网文常见说话动词（基于斗破苍穹、凡人修仙传等统计）
# 边界：仅包含"说话"语义的动词，不包含"思考"、"感受"类动词
#       不应往里加：想、觉得、认为、知道、明白（这些不是说话动词）
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
    """构建引号对话匹配正则"""
    patterns = []
    for lq, rq in zip(_LEFT_QUOTES, _RIGHT_QUOTES):
        patterns.append(re.compile(
            rf'(?:^|[\n。！？；：,，\s])'
            rf'[^{re.escape(lq)}]*?'
            rf'{re.escape(lq)}'
            rf'([^ {re.escape(rq)}]+?)'
            rf'{re.escape(rq)}'
        ))
    return patterns


DIALOGUE_PATTERNS = _build_quote_patterns()

# 说话人模式：匹配"XX道"、"XX说"等格式
# 关键：复合动词必须在单字动词之前匹配，避免"沉声道"被拆分为"沉声"+ "道"
#
# 用途：从"秦羽问道"等文本中提取说话人名字"秦羽"
# 来源：中文句法结构（主语+谓语+引语），网文常见说话模式统计
# 边界：仅匹配"说话"类动词，不匹配"思考"类动词
#       名字长度限制1-6字，覆盖绝大多数中文人名
_VERB_SUFFIXES = set('道说问喊叫答应笑叹怒喝哼嚷骂')

SPEAKER_PATTERNS = [
    # 模式1：XX+三字复合动词（冷冷道/淡淡道）
    re.compile(r'([\u4e00-\u9fa5]{1,5})\s*(?:冷冷道|淡淡道)[：:，,。\s]'),
    # 模式2：XX+三字复合动词（沉声道/低声道/高声道）
    re.compile(r'([\u4e00-\u9fa5]{1,5})\s*(?:沉声道|低声道|高声道)[：:，,。\s]'),
    # 模式3：XX+双字动词+道（说道/问道/答道/笑道/叹道/怒道/喝道/哼道/嚷道/骂道）
    re.compile(r'([\u4e00-\u9fa5]{1,5})\s*(?:说道|问道|答道|笑道|叹道|怒道|喝道|哼道|嚷道|骂道)[：:，,。\s]'),
    # 模式4：XX+单字动词（道/说/问/喊/叫/答/哼/笑/叹/怒/喝/嚷/骂）
    re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:道|说|问|喊|叫|答|应|笑|叹|怒|喝|哼|嚷|骂)[：:，,。\s]'),
]


def _clean_speaker_name(name: str) -> str:
    """清理角色名末尾的动词字符
    
    例如：
    - "秦羽问" → "秦羽"（"问道"被拆分为名字+道）
    - "小医仙笑" → "小医仙"（"笑道"被拆分为名字+道）
    """
    if not name:
        return name
    while len(name) > 1 and name[-1] in _VERB_SUFFIXES:
        name = name[:-1]
    return name


class SpeakerHintMatcher:
    """说话人提示词匹配器"""

    def __init__(self, name_validator):
        self.name_validator = name_validator

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
                name = _clean_speaker_name(match.group(1).strip())
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
                        name = _clean_speaker_name(pm.group(1).strip())
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
                name = _clean_speaker_name(match.group(1).strip())
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
                name = _clean_speaker_name(match.group(1).strip())
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
