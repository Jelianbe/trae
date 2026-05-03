# -*- coding: utf-8 -*-
"""
检查NER评估的别名映射逻辑
"""
import sys
from pathlib import Path
import json
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import get_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.entity_linker import get_entity_linker
from pipeline.semantic_ranker import get_semantic_ranker

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

# 读取GT
gt_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ground_truth.json'
ground_truth = json.loads(gt_file.read_text(encoding='utf-8'))

gt_persons = set(ground_truth['entities']['persons'])
gt_speaking_persons = set(ground_truth['entities']['speaking_persons'])
gt_aliases = ground_truth['entities']['aliases']

print("=" * 80)
print("检查NER评估的别名映射逻辑")
print("=" * 80)

# Step 1-4: 完整pipeline
nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']

validator = get_context_validator(mode='speaker_role', whitelist=gt_speaking_persons)
validated = validator.validate(per_entities, text)

semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
role_entities = speaker_filter.filter(validated, text, nlp)

linker = get_entity_linker()
linker.set_ground_truth(
    persons=list(gt_persons),
    speaking_persons=list(gt_speaking_persons),
    aliases=gt_aliases,
)
linked = linker.link(role_entities, text)

final_entities = [e for e in linked if e.confidence >= 0.5]

print(f"\n【最终实体详情】")
for e in sorted(final_entities, key=lambda x: x.text):
    name = e.standard_name if e.standard_name else e.text
    print(f"  text={e.text}, standard_name={e.standard_name}, is_linked={e.is_linked}, confidence={e.confidence:.2f}")

# 检查别名映射
print(f"\n【别名映射检查】")
for e in final_entities:
    if e.standard_name:
        print(f"  {e.text} → {e.standard_name}")
        
        # 检查该standard_name是否在GT persons中
        if e.standard_name in gt_persons:
            print(f"    ✅ 在GT persons中")
        else:
            print(f"    ⚠️ 不在GT persons中")
        
        # 检查该standard_name的别名
        for canonical, aliases in gt_aliases.items():
            if e.text in aliases or e.text == canonical:
                print(f"    别名关系: {e.text} 是 {canonical} 的别名")

# 构建预测集（考虑别名）
print(f"\n【构建预测集】")
predicted_with_aliases = set()
for e in final_entities:
    # 添加standard_name
    if e.standard_name:
        predicted_with_aliases.add(e.standard_name)
    # 添加原始text
    predicted_with_aliases.add(e.text)
    
    # 如果是别名，也添加canonical name
    for canonical, aliases in gt_aliases.items():
        if e.text in aliases:
            predicted_with_aliases.add(canonical)
        if e.standard_name and e.standard_name in aliases:
            predicted_with_aliases.add(canonical)

print(f"预测集（含别名扩展）: {sorted(predicted_with_aliases)}")

# 计算指标（考虑别名）
tp_set = predicted_with_aliases & gt_persons
fp_set = predicted_with_aliases - gt_persons
fn_set = gt_persons - predicted_with_aliases

tp = len(tp_set)
fp = len(fp_set)
fn = len(fn_set)

precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

print(f"\n【NER指标（别名扩展后）】")
print(f"  TP: {tp} - {sorted(tp_set)}")
print(f"  FP: {fp} - {sorted(fp_set)}")
print(f"  FN: {fn} - {sorted(fn_set)}")
print(f"  Precision: {precision:.1f}%")
print(f"  Recall: {recall:.1f}%")
print(f"  F1: {f1:.1f}")

print("\n" + "=" * 80)
