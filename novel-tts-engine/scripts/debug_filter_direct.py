#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""详细调试_filter_false_persons"""
from pipeline.nlp_basics import NLPBasics
from pipeline.nlp_basics import Entity

nlp = NLPBasics()

# 直接测试_filter_false_persons
test_entities = [
    Entity(text='萧炎冷', type='PER', start=0, end=1),
    Entity(text='萧炎承', type='PER', start=0, end=1),
    Entity(text='萧炎', type='PER', start=0, end=1),
]

print("Before filtering:")
for e in test_entities:
    print(f"  {e.text} (len={len(e.text)}, last_char='{e.text[-1]}')")

result = nlp._filter_false_persons(test_entities)

print("\nAfter filtering:")
for e in result:
    print(f"  {e.text}")

# 检查FALSE_PERSON_ENDINGS是否包含'冷'和'承'
print("\nChecking FALSE_PERSON_ENDINGS...")
# 我们需要查看方法内部的集合
import inspect
source = inspect.getsource(nlp._filter_false_persons)
print("'冷' in source:", "'冷'" in source)
print("'承' in source:", "'承'" in source)
