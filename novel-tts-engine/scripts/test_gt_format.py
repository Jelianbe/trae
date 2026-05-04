# -*- coding: utf-8 -*-
"""Simple NER evaluation test for all 3 novels"""
import os
os.environ['DEBUG_NER'] = '0'

from analysis_reports.评估脚本.evaluate_generalization_v3 import evaluate_ner
import json

test_cases = [
    ("西幻", "tests/test_novel_western.txt", "tests/test_novel_western_ground_truth.json"),
    ("都市", "tests/test_novel_urban.txt", "tests/test_novel_urban_ground_truth.json"),
    ("修仙", "tests/test_novel.txt", "tests/test_novel_ground_truth.json"),
]

print("=" * 50)
print("NER评估GT格式修复验证")
print("=" * 50)

for style, txt_path, gt_path in test_cases:
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    
    # Test with full GT object
    score_full = evaluate_ner(text, gt)
    
    # Test with entities sub-object
    score_entities = evaluate_ner(text, gt.get('entities', gt))
    
    entities = gt.get('entities', gt)
    persons = entities.get('persons', [])
    speaking = entities.get('speaking_persons', [])
    locs = entities.get('locations', [])
    orgs = entities.get('organizations', [])
    
    print(f"\n{style}:")
    print(f"  NER分数(完整GT): {score_full}")
    print(f"  NER分数(entities): {score_entities}")
    print(f"  格式匹配: {'PASS' if score_full == score_entities else 'FAIL'}")
    print(f"  GT人物({len(persons)}): {persons}")
    print(f"  GT说话人物({len(speaking)}): {speaking}")
    print(f"  GT地点({len(locs)}): {locs}")
    print(f"  GT组织({len(orgs)}): {orgs}")

print("\n" + "=" * 50)
print("所有测试完成！")
print("=" * 50)
