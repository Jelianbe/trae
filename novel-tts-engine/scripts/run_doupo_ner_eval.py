# -*- coding: utf-8 -*-
"""运行斗破苍穹NER评估"""
import sys
from pathlib import Path

# 设置项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analysis_reports.评估脚本.evaluate_generalization_v3 import evaluate_ner
import json

text_file = project_root / 'tests' / 'test_novel_doupo_ch1-10.txt'
gt_file = project_root / 'tests' / 'test_novel_doupo_ground_truth.json'

text = text_file.read_text(encoding='utf-8')
gt = json.load(gt_file.open(encoding='utf-8'))

print("运行斗破苍穹NER评估...")
ner_score = evaluate_ner(text, gt.get("entities", {}))
print(f"\nNER F1: {ner_score}")
