#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试角色名提取修复 - 最终验证"""

import re

_VERB_SUFFIXES = set('道说问喊叫答应笑叹怒喝哼嚷骂')

SPEAKER_PATTERNS = [
    # 模式1：XX+三字复合动词（冷冷道/淡淡道）
    re.compile(r'([\u4e00-\u9fa5]{1,5})\s*(?:冷冷道|淡淡道)[：:，,。\s]'),
    # 模式2：XX+三字复合动词（沉声道/低声道/高声道）
    re.compile(r'([\u4e00-\u9fa5]{1,5})\s*(?:沉声道|低声道|高声道)[：:，,。\s]'),
    # 模式3：XX+双字动词+道（说道/问道/答道/笑道/叹道/怒道/喝道/哼道/嚷道/骂道）
    re.compile(r'([\u4e00-\u9fa5]{1,5})\s*(?:说道|问道|答道|笑道|叹道|怒道|喝道|哼道|嚷道|骂道)[：:，,。\s]'),
    # 模式4：XX+单字动词（道/说/问/喊/叫/答/应/笑/叹/怒/喝/哼/嚷/骂）
    re.compile(r'([\u4e00-\u9fa5]{1,6})\s*(?:道|说|问|喊|叫|答|应|笑|叹|怒|喝|哼|嚷|骂)[：:，,。\s]'),
]


def _clean_speaker_name(name: str) -> str:
    """清理角色名末尾的动词字符"""
    if not name:
        return name
    while len(name) > 1 and name[-1] in _VERB_SUFFIXES:
        name = name[:-1]
    return name


def extract_name(text: str) -> str:
    """从文本中提取角色名"""
    for pattern in SPEAKER_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean_speaker_name(match.group(1).strip())
    return None


tests = [
    ('秦羽问道。', '秦羽'),
    ('林凡沉默了片刻，缓缓说道：', '林凡'),
    ('萧炎沉声道：', '萧炎'),
    ('小医仙笑道：', '小医仙'),
    ('"你什么意思？"秦羽问道。', '秦羽'),
    ('林凡说道："今天天气不错。"', '林凡'),
    ('他冷冷道："不可能！"', '他'),
    ('秦羽淡淡道："随便你。"', '秦羽'),
    ('那人低声道："小声点。"', '那人'),
    ('秦羽冷笑一声：', None),  # 不匹配，"冷笑一声"不是标准模式
]

print('角色名提取测试结果（最终修复）：')
print('=' * 60)
all_passed = True

for text, expected in tests:
    result = extract_name(text)
    status = '✅' if result == expected else '❌'
    if result != expected:
        all_passed = False
    
    print(f'{status} "{text}"')
    print(f'   期望: {expected}, 实际: {result}')
    print()

print('=' * 60)
if all_passed:
    print('✅ 所有测试通过！')
else:
    print('❌ 部分测试未通过，需要进一步调整')
