#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试"萧炎冷"问题"""

from pipeline.nlp_basics import NLPBasics
import json

nlp = NLPBasics()
with open('tests/test_novel_doupo_ch1-10.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 查找包含'萧炎冷'的上下文
for keyword in ['萧炎冷', '萧炎冷笑道', '萧炎冷冷']:
    idx = text.find(keyword)
    if idx >= 0:
        context = text[max(0,idx-30):idx+50]
        print(f'Found "{keyword}" at position {idx}')
        print(f'Context: ...{context}...')
        print()

# 运行NLP分析查看结果
result = nlp.analyze(text)
entities = result.entities
for e in entities:
    if '冷' in e.text:
        print(f'Entity with 冷: {e.text} (type={e.type}, conf={e.confidence})')
