# -*- coding: utf-8 -*-
"""
分析v2方案导致NER下降的原因
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp, Entity
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
print("分析v2方案NER下降原因")
print("=" * 80)

# Step 1-2: NLP + ContextDiversityValidator
nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']

validator = get_context_validator(mode='speaker_role', whitelist=gt_speaking_persons)
validated = validator.validate(per_entities, text)

# 检查统计信息
stats = validator._collect_context_stats(per_entities, text)

print(f"\n【PER实体统计】")
unique_entities = set(e.text for e in per_entities)
print(f"唯一PER实体数: {len(unique_entities)}")

# 检查哪些实体被标记为误合并
mis_merged = validator._detect_mis_merged_entities(per_entities, stats, text)
print(f"\n【被标记为误合并的实体】: {len(mis_merged)}")
for e in sorted(mis_merged):
    entity_count = stats.get(e, {}).get('occurrences', 0)
    diversity = len(stats.get(e, {}).get('right_neighbors', set()))
    print(f"  {e}: 出现{entity_count}次, 右邻字{diversity}种")
    
    # 检查该实体是否是GT中的人物
    if e in gt_persons:
        print(f"    ⚠️ 是GT中的人物！")

# 检查哪些前缀触发了误合并
print(f"\n【误合并的前缀分析】")
for entity in sorted(mis_merged):
    for suffix_len in [1, 2]:
        if len(entity) <= suffix_len:
            continue
        prefix = entity[:-suffix_len]
        if prefix in stats:
            prefix_count = stats[prefix]['occurrences']
            entity_count = stats.get(entity, {}).get('occurrences', 0)
            ratio = entity_count / prefix_count * 100 if prefix_count > 0 else 0
            print(f"  {entity} → {prefix}({prefix_count}次), 比率={ratio:.1f}%")
            if entity in gt_persons:
                print(f"    ⚠️ {entity}是GT人物，但被误杀！")

# Step 3-4: 完整pipeline
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
final_texts = set()
for e in final_entities:
    name = e.standard_name if e.standard_name else e.text
    final_texts.add(name)

# 计算指标
tp_set = final_texts & gt_persons
fp_set = final_texts - gt_persons
fn_set = gt_persons - final_texts

tp = len(tp_set)
fp = len(fp_set)
fn = len(fn_set)

print(f"\n【最终结果】")
print(f"TP: {tp} - {sorted(tp_set)}")
print(f"FP: {fp} - {sorted(fp_set)}")
print(f"FN: {fn} - {sorted(fn_set)}")

precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

print(f"Precision: {precision:.1f}%")
print(f"Recall: {recall:.1f}%")
print(f"F1: {f1:.1f}")

# 对比v1和v2的误杀
print(f"\n【被v2方案过滤掉的GT实体】")
for entity in sorted(fn_set):
    # 检查是否因为误合并检测被过滤
    if entity in mis_merged:
        print(f"  {entity}: 被误合并检测过滤 ❌")
    else:
        print(f"  {entity}: 被其他环节过滤")

print("\n" + "=" * 80)
