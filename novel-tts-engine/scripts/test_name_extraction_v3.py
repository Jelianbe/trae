#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试角色名提取修复 - 后处理方案"""

import re

# 原始正则（贪婪匹配）
pattern2 = re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:道|说|问|喊|叫|答|应|笑|叹|怒|喝|哼|嚷|骂)[：:，,。\s]')
pattern1 = re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:沉声道|低声道|高声道|冷冷道|淡淡道)[：:，,。\s]')

# 常见动词后缀（用于清理）
_VERB_SUFFIXES = '道说问喊叫答应笑叹怒喝哼嚷骂'

def clean_speaker_name(name: str) -> str:
    """清理角色名末尾的动词字符"""
    if not name:
        return name
    # 从末尾移除动词字符，直到遇到非动词字符
    while len(name) > 1 and name[-1] in _VERB_SUFFIXES:
        name = name[:-1]
    return name

tests = [
    ('秦羽问道。', '秦羽'),
    ('林凡沉默了片刻，缓缓说道：', '林凡'),
    ('萧炎沉声道：', '萧炎'),
    ('小医仙笑道：', '小医仙'),
    ('"你什么意思？"秦羽问道。', '秦羽'),
    ('林凡说道："今天天气不错。"', '林凡'),
    ('他冷冷道："不可能！"', '他'),
    ('秦羽冷笑一声：', '秦羽'),  # "冷笑"是复合动词，应该只提取"秦羽"
]

print('角色名提取测试结果（后处理清理方案）：')
print('=' * 60)
all_passed = True

for text, expected in tests:
    match = pattern1.search(text)
    if not match:
        match = pattern2.search(text)
    
    raw = match.group(1) if match else None
    result = clean_speaker_name(raw) if raw else None
    status = '✅' if result == expected else '❌'
    if result != expected:
        all_passed = False
    
    print(f'{status} "{text}"')
    print(f'   原始: "{raw}", 清理后: "{result}", 期望: "{expected}"')
    print()

print('=' * 60)
if all_passed:
    print('所有测试通过！')
else:
    print('部分测试未通过，需要进一步调整')
