# -*- coding: utf-8 -*-
"""检查暗影会在完整文本分析中的检测情况"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '1'

from pipeline.nlp_basics import get_nlp

urban_text = Path("tests/test_novel_urban.txt").read_text(encoding='utf-8')

nlp = get_nlp()
result = nlp.analyze(urban_text)

# Print all ORG entities
print("\n所有ORG实体:")
for e in result.entities:
    if e.type == 'ORG':
        print(f"  {e.text} (confidence={e.confidence})")
