#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试完整分析流程中"萧炎冷"的来源"""
from pipeline.nlp_basics import NLPBasics

nlp = NLPBasics()

# 拦截关键方法
original_extract = nlp._extract_entities_from_pos
original_enhance = nlp._enhance_entities

def debug_extract(tokens):
    result = original_extract(tokens)
    texts = [e.text for e in result if '冷' in e.text or '承' in e.text]
    if texts:
        print(f"  [_extract_entities_from_pos] FOUND: {texts}")
    return result

def debug_enhance(tokens, pos_tags, base_entities, raw_text=None):
    result = original_enhance(tokens, pos_tags, base_entities, raw_text)
    texts = [e.text for e in result if '冷' in e.text or '承' in e.text]
    if texts:
        print(f"  [_enhance_entities] FOUND: {texts}")
    return result

nlp._extract_entities_from_pos = debug_extract
nlp._enhance_entities = debug_enhance

# 分析文本片段
with open('tests/test_novel_doupo_ch1-10.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("Analyzing full text...")
result = nlp.analyze(text)

final_texts = [e.text for e in result.entities if '冷' in e.text or '承' in e.text]
print(f"\nFinal entities with 冷/承: {final_texts}")
