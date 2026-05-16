# -*- coding: utf-8 -*-
"""Trace exactly which dialogue gets "修士" as its speaker"""
import sys
sys.path.insert(0, '.')

from pipeline.pipeline_runner import PipelineRunner

runner = PipelineRunner(speaker_matcher_type='legacy')
text = open(r'C:\Users\月笙如歌\Desktop\修仙传(1).txt', encoding='utf-8').read()

# Find the exact location around "修士们鱼贯而入"
idx = text.find('修士们鱼贯而入')
print(f"'修士们鱼贯而入' 在文本中的位置: {idx}")
print(f"\n上下文:\n{text[max(0,idx-100):idx+200]}")
print("\n---")

# Now find the next dialogue after that
after = text[idx+200:]
# Find the first dialogue (引号内容)
import re
dialogues = list(re.finditer(r'[\u201c\u300c]([^\u201d\u300d]*?)[\u201d\u300d]', after[:200]))
for d in dialogues[:3]:
    start = idx + 200 + d.start()
    # Get context before this dialogue
    ctx_start = max(0, start - 300)
    ctx_before = text[ctx_start:start]
    print(f"\n对话: {d.group()}")
    print(f"位置: {start}")
    print(f"context_before 尾部150字: ...{ctx_before[-150:]}")
