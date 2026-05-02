# -*- coding: utf-8 -*-
"""检查"暗影会"检测"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

from pipeline.nlp_basics import get_nlp

nlp = get_nlp()

test_sentences = [
    "但我听到他们说一个叫暗影会的神秘组织，似乎在暗中收集所有觉醒者。",
    "苏先生，我们是暗影会的调查员。",
    "他知道，暗影会不会轻易放过他。",
]

for sent in test_sentences:
    print(f"\n句子: {sent[:60]}...")
    result = nlp.analyze(sent)
    orgs = [e.text for e in result.entities if e.type == 'ORG']
    print(f"  组织: {orgs}")
