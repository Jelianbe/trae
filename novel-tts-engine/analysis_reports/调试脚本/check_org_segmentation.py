# -*- coding: utf-8 -*-
"""检查组织名分词"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

from pipeline.nlp_basics import get_nlp

nlp = get_nlp()

test_sentences = [
    "我们是暗影会的调查员",
    "暗影会的人来了",
    "让暗影会陷入混乱",
]

for sent in test_sentences:
    result = nlp.analyze(sent)
    print(f"\n句子: {sent}")
    print(f"  分词: {[t.text for t in result.tokens]}")
    print(f"  词性: {[t.pos for t in result.tokens]}")
    orgs = [e.text for e in result.entities if e.type == 'ORG']
    print(f"  ORG实体: {orgs}")
