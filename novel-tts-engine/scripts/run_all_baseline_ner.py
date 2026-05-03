# -*- coding: utf-8 -*-
"""运行所有基线NER测试确认无回归"""
import sys
from pathlib import Path

# 设置项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analysis_reports.评估脚本.evaluate_generalization_v3 import evaluate_ner
import json

test_files = [
    {
        'name': '斗破苍穹',
        'text': project_root / 'tests' / 'test_novel_doupo_ch1-10.txt',
        'gt': project_root / 'tests' / 'test_novel_doupo_ground_truth.json',
        'baseline': 85.7,
    },
    {
        'name': '都市爽文',
        'text': project_root / 'tests' / 'test_novel_urban_ch1-3.txt',
        'gt': project_root / 'tests' / 'test_novel_urban_ground_truth.json',
        'baseline': 90.9,
    },
    {
        'name': '西幻爽文',
        'text': project_root / 'tests' / 'test_novel_western_ch1-3.txt',
        'gt': project_root / 'tests' / 'test_novel_western_ground_truth.json',
        'baseline': 100.0,
    },
    {
        'name': '修真爽文',
        'text': project_root / 'tests' / 'test_novel_cultivation_ch1-3.txt',
        'gt': project_root / 'tests' / 'test_novel_cultivation_ground_truth.json',
        'baseline': 100.0,
    },
]

print("=" * 80)
print("基线NER测试（误合并检测修复后）")
print("=" * 80)

all_passed = True
for test in test_files:
    print(f"\n{'─' * 80}")
    print(f"【{test['name']}】")
    print(f"{'─' * 80}")
    
    try:
        text = test['text'].read_text(encoding='utf-8')
        gt = json.load(test['gt'].open(encoding='utf-8'))
        
        ner_score = evaluate_ner(text, gt.get("entities", {}))
        
        status = "✅" if ner_score >= test['baseline'] else "❌"
        print(f"  NER F1: {ner_score} (基线: {test['baseline']}) {status}")
        
        if ner_score < test['baseline']:
            all_passed = False
            print(f"  ⚠️ 低于基线 {test['baseline']}")
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        all_passed = False

print(f"\n{'=' * 80}")
if all_passed:
    print("✅ 所有基线测试通过，无回归")
else:
    print("❌ 存在基线回归，需要调查")
print(f"{'=' * 80}")
