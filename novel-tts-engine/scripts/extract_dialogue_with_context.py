#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从《斗破苍穹》原文中抽取对话片段（含上下文）

用途：为情绪标注器验证创建真实文本测试集（GT）
策略：抽取完整对话片段，包含前后文，保持语义完整性

每段包含：
- 前文（1-2 句背景）
- 目标对话（需要标注的句子）
- 后文（1-2 句反应/ continuation）
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

# 取前 5 万字（保证上下文质量）
text = text[:50000]
print(f"截取前 5 万字: {len(text)} 字符")

# 按段落分割
paragraphs = text.split('\n')
paragraphs = [p.strip() for p in paragraphs if p.strip()]

print(f"总段落数: {len(paragraphs)}")

# 抽取包含对话的段落组
def extract_dialogue_contexts(paragraphs, window_size=3):
    """
    抽取对话上下文片段
    
    Args:
        paragraphs: 段落列表
        window_size: 窗口大小（前文 + 目标 + 后文）
    
    Returns:
        对话上下文列表
    """
    contexts = []
    
    for i in range(len(paragraphs)):
        para = paragraphs[i]
        # 判断是否包含对话
        if '“' in para or '"' in para:
            # 提取上下文窗口
            start = max(0, i - 1)
            end = min(len(paragraphs), i + 2)
            
            context = {
                'before': paragraphs[start:i] if i > 0 else [],
                'target': para,
                'after': paragraphs[i+1:end] if i+1 < len(paragraphs) else [],
            }
            contexts.append(context)
    
    return contexts

# 抽取对话上下文
contexts = extract_dialogue_contexts(paragraphs)
print(f"找到 {len(contexts)} 个对话片段")

# 均匀抽样 50 个
import random
random.seed(42)

if len(contexts) > 50:
    # 均匀分布抽样
    step = len(contexts) // 50
    selected = [contexts[i * step] for i in range(50)]
else:
    selected = contexts

# 输出
print(f"\n共抽取 {len(selected)} 个对话片段：")
print("=" * 80)

output_path = Path(r"d:\trae\novel-tts-engine\tests\emotion_test_sentences_with_context.txt")
with open(output_path, 'w', encoding='utf-8') as f:
    for i, ctx in enumerate(selected, 1):
        f.write(f"{'='*80}\n")
        f.write(f"#{i}\n")
        f.write(f"{'='*80}\n")
        
        if ctx['before']:
            f.write(f"【前文】\n")
            for p in ctx['before']:
                f.write(f"  {p}\n")
        
        f.write(f"\n【目标对话】（需要标注）\n")
        f.write(f"  {ctx['target']}\n")
        
        if ctx['after']:
            f.write(f"\n【后文】\n")
            for p in ctx['after']:
                f.write(f"  {p}\n")
        
        f.write(f"\n【情绪标注】（请填写）\n")
        f.write(f"  情绪: \n")
        f.write(f"  强度: mild/moderate/strong\n")
        f.write(f"  语气: （如傲慢、讥讽、慵懒等，可选）\n")
        f.write(f"  备注: （说话人、场景等，可选）\n")
        f.write(f"\n")
        
        # 打印到控制台
        print(f"\n#{i}")
        if ctx['before']:
            print(f"  【前文】 {ctx['before'][0][:80]}")
        print(f"  【目标】 {ctx['target'][:100]}")
        if ctx['after']:
            print(f"  【后文】 {ctx['after'][0][:80]}")
        print()

print(f"\n已写入: {output_path}")
print("请人工标注每个对话片段的情绪、强度、语气")
