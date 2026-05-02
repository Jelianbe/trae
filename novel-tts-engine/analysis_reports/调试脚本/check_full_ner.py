# -*- coding: utf-8 -*-
"""检查"暗影会"在整个文本中的检测情况"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

from pipeline.nlp_basics import get_nlp

urban_text = Path("tests/test_novel_urban.txt").read_text(encoding='utf-8')

nlp = get_nlp()
result = nlp.analyze(urban_text)

orgs = set(e.text for e in result.entities if e.type == 'ORG')
persons = set(e.text for e in result.entities if e.type == 'PER')

print(f"检测到的组织: {orgs}")
print(f"检测到的{persons}: {persons}")
print(f"\n'暗影会'是否在ORG中: {'暗影会' in orgs}")
