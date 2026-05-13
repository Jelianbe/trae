#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试角色名提取修复 - 使用否定后视"""

import re

_SINGLE_VERBS = '道说问喊叫答应笑叹怒喝哼嚷骂'
# 使用否定后视：确保捕获组的最后一个字符不是动词
_SPEAKER_NAME_PATTERN = rf'[\u4e00-\u9fa5]{{1,6}}(?<![{_SINGLE_VERBS}])'
pattern2 = re.compile(rf'({_SPEAKER_NAME_PATTERN})\s*(?:道|说|问|喊|叫|答|应|笑|叹|怒|喝|哼|嚷|骂)[：:，,。\s]')
pattern1 = re.compile(rf'({_SPEAKER_NAME_PATTERN})\s*(?:沉声道|低声道|高声道|冷冷道|淡淡道)[：:，,。\s]')

tests = [
    ('秦羽问道。', '秦羽'),
    ('林凡沉默了片刻，缓缓说道：', '林凡'),
    ('萧炎沉声道：', '萧炎'),
    ('小医仙笑道：', '小医仙'),
    ('"你什么意思？"秦羽问道。', '秦羽'),
    ('林凡说道："今天天气不错。"', '林凡'),
    ('他冷冷道："不可能！"', '他'),
]

print('角色名提取测试结果（否定后视方案）：')
print('=' * 50)
all_passed = True

for text, expected in tests:
    match = pattern2.search(text)
    if not match:
        match = pattern1.search(text)
    
    result = match.group(1) if match else None
    status = '✅' if result == expected else '❌'
    if result != expected:
        all_passed = False
    
    print(f'{status} "{text}"')
    print(f'   期望: {expected}, 实际: {result}')
    print()

print('=' * 50)
if all_passed:
    print('所有测试通过！')
else:
    print('部分测试未通过，需要进一步调整')
