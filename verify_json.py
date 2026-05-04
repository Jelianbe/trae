# -*- coding: utf-8 -*-
import json

# 验证 JSON 格式
with open(r'd:\trae\novel-tts-engine\tests\test_novel_ground_truth.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'JSON格式正确，共 {len(data["dialogue_speakers"])} 条对话')

# 检查引号字符
LEFT_QUOTE = '\u201c'  # " (U+201C)
RIGHT_QUOTE = '\u201d'  # " (U+201D)

print(f'\n前5条对话:')
for i, item in enumerate(data["dialogue_speakers"][:5]):
    text = item["text"]
    has_left = text.startswith(LEFT_QUOTE)
    has_right = text.endswith(RIGHT_QUOTE)
    print(f'  {i+1}. {text} - {item["speaker"]} (左引号: {has_left}, 右引号: {has_right})')

# 检查所有对话是否都有正确的引号
all_correct = True
for i, item in enumerate(data["dialogue_speakers"]):
    text = item["text"]
    if not (text.startswith(LEFT_QUOTE) and text.endswith(RIGHT_QUOTE)):
        print(f'警告: 第{i+1}条对话引号不正确: {text}')
        all_correct = False

if all_correct:
    print(f'\n✓ 所有 {len(data["dialogue_speakers"])} 条对话都已正确添加中文引号')
