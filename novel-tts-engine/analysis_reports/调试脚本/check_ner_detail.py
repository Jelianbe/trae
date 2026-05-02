# -*- coding: utf-8 -*-
"""检查暗影会的NER分析"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '1'

from pipeline.nlp_basics import get_nlp

# Don't suppress output
nlp = get_nlp()

test_sentences = [
    "但我听到他们说一个叫暗影会的神秘组织",
    "我们是暗影会的调查员",
    "暗影会不会轻易放过他",
    "博士满意地说道",
    '"准备好了，博士。"对讲机里传来回应',
    "博士冷声喝道",
    "林雪，你怎么上来了？",
    "苏夜伸出手",
    "赵天行伸出手",
]

for sent in test_sentences:
    print(f"\n句子: {sent}")
    result = nlp.analyze(sent)
    for e in result.entities:
        print(f"  实体: {e.text} ({e.type}) confidence={e.confidence}")
