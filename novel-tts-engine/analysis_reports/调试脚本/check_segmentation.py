# -*- coding: utf-8 -*-
"""诊断分词问题"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp

nlp = get_nlp()

sent = "暗影会不会轻易放过他"
result = nlp.analyze(sent)

print(f"句子: {sent}")
print(f"分词: {[t.text for t in result.tokens]}")
print(f"词性: {[t.pos for t in result.tokens]}")
print(f"实体: {[(e.text, e.type) for e in result.entities]}")
