#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试"萧炎冷"在完整评估中为什么仍存在"""
from pipeline.nlp_basics import NLPBasics

nlp = NLPBasics()
with open('tests/test_novel_doupo_ch1-10.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 临时添加调试输出
original_filter = nlp._filter_false_persons
def debug_filter(entities):
    result = original_filter(entities)
    filtered_texts = [e.text for e in entities if e.text not in [x.text for x in result]]
    if filtered_texts:
        print(f"  FILTERED: {filtered_texts}")
    return result
nlp._filter_false_persons = debug_filter

result = nlp.analyze(text)
for e in result.entities:
    if '冷' in e.text:
        print(f"FOUND: {e.text} (type={e.type})")
