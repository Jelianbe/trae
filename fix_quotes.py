# -*- coding: utf-8 -*-
import json

# 正确的中文引号
LEFT_QUOTE = '\u201c'  # " (U+201C)
RIGHT_QUOTE = '\u201d'  # " (U+201D)

# 读取原始文件
with open(r'd:\trae\novel-tts-engine\tests\test_novel_ground_truth.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 为 dialogue_speakers 添加中文引号
for item in data['dialogue_speakers']:
    text = item['text']
    # 如果已经有引号，先移除
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # 添加中文引号
    item['text'] = f'{LEFT_QUOTE}{text}{RIGHT_QUOTE}'

# 保存文件
with open(r'd:\trae\novel-tts-engine\tests\test_novel_ground_truth.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'已为 {len(data["dialogue_speakers"])} 条对话添加中文引号')
print(f'示例: {data["dialogue_speakers"][0]["text"]}')
