#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从《斗破苍穹》原文中抽取 50 句对话/描述句

用途：为情绪标注器验证创建真实文本测试集（GT）
抽取策略：覆盖不同章节、不同角色、不同场景
"""

import re
from pathlib import Path

# 读取原文
file_path = Path(r"d:\trae\novel-tts-engine\《斗破苍穹》【爱上阅读_www.isyd.net】.txt")
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

print(f"文件总长度: {len(text)} 字符")

# 找到"第一章"的位置
ch1_match = re.search(r'第[一二三四五六七八九十百千0-9]+章', text)
if ch1_match:
    start_pos = ch1_match.start()
    text = text[start_pos:]
    print(f"找到第一章，从位置 {start_pos} 开始")

# 取前 10 万字
text = text[:100000]
print(f"截取前 10 万字: {len(text)} 字符")

# 抽取句子（按句号、问号、感叹号分割）
sentences = re.split(r'[。！？\n]+', text)
sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

print(f"总句子数: {len(sentences)}")

# 抽取包含引号的对话句（中文引号 "" 和 ''）
dialogue_sentences = [s for s in sentences if '“' in s or '”' in s or '"' in s or '"' in s]
other_sentences = [s for s in sentences if '“' not in s and '”' not in s and '"' not in s and '"' not in s]

print(f"包含引号的句子: {len(dialogue_sentences)}")
print(f"其他句子: {len(other_sentences)}")

# 抽取 50 句：40 句对话 + 10 句描述
selected = []

# 均匀分布在不同章节抽取
import random
random.seed(42)

# 将对话句子分成若干组，从每组中抽取
group_size = max(1, len(dialogue_sentences) // 5)
for i in range(0, min(len(dialogue_sentences), 5 * group_size), group_size):
    group = dialogue_sentences[i:i+group_size]
    if group:
        selected.extend(random.sample(group, min(8, len(group))))

# 补充到 40 句对话
while len(selected) < 40 and dialogue_sentences:
    s = random.choice(dialogue_sentences)
    if s not in selected:
        selected.append(s)

# 添加 10 句描述
for s in other_sentences[:10]:
    if s not in selected:
        selected.append(s)

# 输出
print(f"\n共抽取 {len(selected)} 句：")
for i, s in enumerate(selected, 1):
    print(f"{i}. {s[:100]}")

# 写入文件
output_path = Path(r"d:\trae\novel-tts-engine\tests\emotion_test_sentences_raw.txt")
with open(output_path, 'w', encoding='utf-8') as f:
    for i, s in enumerate(selected, 1):
        f.write(f"{i}. {s}\n")

print(f"\n已写入: {output_path}")
print("请人工标注每句的情绪标签（joy/anger/sadness/surprise/fear/neutral）")
