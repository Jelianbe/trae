# -*- coding: utf-8 -*-
"""T-007 代词消解详细调试"""
from pipeline.speaker_hint_matcher import SpeakerHintMatcher, SPEAKER_PATTERNS
from pipeline.name_validator import NameValidator
import re

validator = NameValidator()
matcher = SpeakerHintMatcher(validator)

# 测试 extract_speaker_hint
texts = [
    "林轩说道： 小翠回应道：",
    "林轩说道： 他转身离开了。",
    " 小翠回应道：",
]

for text in texts:
    hint, hint_type = matcher.extract_speaker_hint(text)
    print(f"文本: {repr(text)}")
    print(f"  结果: hint={hint}, type={hint_type}")
    
    # 检查每个 pattern
    for i, pattern in enumerate(SPEAKER_PATTERNS):
        match = pattern.search(text)
        if match:
            print(f"  Pattern {i+1} 匹配: {repr(match.group(0))}, 名字: {repr(match.group(1))}")
