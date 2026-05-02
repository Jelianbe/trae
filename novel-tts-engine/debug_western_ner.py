#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试西幻NER优化效果"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.nlp_basics import get_nlp, reset_nlp
import json

# 重置并加载西幻文本
reset_nlp()
nlp = get_nlp()

# 读取西幻文本
with open('tests/test_novel_western.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 读取GT
with open('tests/test_novel_western_ground_truth.json', 'r', encoding='utf-8') as f:
    gt = json.load(f)

gt_entities = gt['entities']
gt_speakers = set(gt_entities['speaking_persons'])
gt_persons = set(gt_entities['persons'])
gt_orgs = set(gt_entities['organizations'])
gt_locs = set(gt_entities['locations'])
print(f"GT标注的说话角色: {gt_speakers}")
print(f"GT标注的所有PER: {gt_persons}")
print(f"GT标注的ORG: {gt_orgs}")
print(f"GT标注的LOC: {gt_locs}")
print()

# 分析文本
result = nlp.analyze(text)

# 收集所有PER实体
per_entities = set()
for entity in result.entities:
    if entity.type == 'PER':
        per_entities.add(entity.text)

print(f"识别到的PER实体 (共{len(per_entities)}个):")
for name in sorted(per_entities):
    in_gt = name in gt_speakers
    print(f"  {'✅' if in_gt else '❌'} {name}")

print()

# 检查GT中但未被识别的角色
missing = gt_speakers - per_entities
if missing:
    print(f"GT中有但未被识别的角色 ({len(missing)}个):")
    for name in sorted(missing):
        print(f"  ❌ {name}")
else:
    print("✅ 所有GT角色都被识别到了！")

print()

# 检查被错误识别的角色（不在GT中）
false_positives = per_entities - gt_speakers
if false_positives:
    print(f"被错误识别的角色 ({len(false_positives)}个):")
    for name in sorted(false_positives):
        print(f"  ❌ {name}")

print()

# 计算简单F1
tp = len(per_entities & gt_speakers)
fp = len(per_entities - gt_speakers)
fn = len(gt_speakers - per_entities)

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

print(f"简单PER识别指标:")
print(f"  True Positives:  {tp}")
print(f"  False Positives: {fp}")
print(f"  False Negatives: {fn}")
print(f"  Precision: {precision:.4f}")
print(f"  Recall:    {recall:.4f}")
print(f"  F1 Score:  {f1:.4f}")
