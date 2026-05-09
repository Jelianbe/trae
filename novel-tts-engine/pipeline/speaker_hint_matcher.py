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
# 关键：使用贪婪匹配 + 限定名字长度，确保"秦羽问道"提取为"秦羽"
SPEAKER_PATTERNS = [
    # 模式1：XX+复合动词（沉声道/低声道/高声道/冷冷道/淡淡道）
    re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:沉声道|低声道|高声道|冷冷道|淡淡道)[：:，,。\s]'),
    # 模式2：XX+单字动词（道/说/问/喊/叫/答/哼/笑/叹/怒/喝/嚷/骂）
    # 使用贪婪匹配 {1,6}，确保名字部分尽可能长，避免动词前的字被包含
    re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:道|说|问|喊|叫|答|应|笑|叹|怒|喝|哼|嚷|骂)[：:，,。\s]'),
]


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
                name = match.group(1).strip()
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
                        name = pm.group(1).strip()
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
                name = match.group(1).strip()
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
                name = match.group(1).strip()
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
