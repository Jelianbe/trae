# -*- coding: utf-8 -*-
"""
验证误合并检测修复效果

测试目标：
1. "萧炎冷" 不应出现在False positives中
2. 真实角色名不应被误杀
3. NER F1应该 >= 85.7（保持现有水平）
"""
import sys
from pathlib import Path
import json
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp, Entity
from pipeline.context_diversity_validator import get_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.entity_linker import EntityLinker

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

# 读取GT
gt_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ground_truth.json'
ground_truth = json.loads(gt_file.read_text(encoding='utf-8'))

gt_persons = set(ground_truth['entities']['persons'])
gt_aliases = ground_truth['entities']['aliases']

print("=" * 80)
print("验证误合并检测修复效果")
print("=" * 80)

# Step 1: 基础NER分析
nlp = get_nlp()
result = nlp.analyze(text)
entities = list(result.entities)

per_entities = [e for e in entities if e.type == 'PER']
per_texts = set(e.text for e in per_entities)

print(f"\n【Step 1】基础NER分析")
print(f"  识别到的PER实体数: {len(per_entities)}")
print(f"  唯一PER实体: {len(per_texts)}")

# 检查"萧炎冷"是否在基础NER中
has_xiaoyan_cold_step1 = any('炎冷' in e.text for e in per_entities)
print(f"  '萧炎冷'在基础NER中: {'是' if has_xiaoyan_cold_step1 else '否'}")

# Step 2: ContextDiversityValidator（包含误合并检测）
validator = get_context_validator(mode='speaker_role', whitelist=set())
validated_entities = validator.validate(per_entities, text)

print(f"\n【Step 2】统计验证 + 误合并检测后")
print(f"  实体数: {len(validated_entities)}")

# 检查"萧炎冷"是否被正确过滤
has_xiaoyan_cold_step2 = any('炎冷' in e.text for e in validated_entities)
print(f"  '萧炎冷'在结果中: {'是' if has_xiaoyan_cold_step2 else '否 ✅'}")

# 打印低置信度实体（应该是被误合并检测标记的）
low_conf = [e for e in validated_entities if e.confidence < 0.5]
if low_conf:
    print(f"\n  低置信度实体（confidence < 0.5）:")
    for e in low_conf[:10]:
        print(f"    {e.text}: confidence={e.confidence:.2f}")

# Step 3: 最终过滤（confidence >= 0.5）
final_entities = [e for e in validated_entities if e.confidence >= 0.5]
final_texts = set(e.text for e in final_entities)

print(f"\n【Step 3】最终过滤后 (confidence >= 0.5)")
print(f"  最终PER实体数: {len(final_entities)}")
print(f"  唯一PER实体: {len(final_texts)}")

# 检查"萧炎冷"是否在最终结果中
has_xiaoyan_cold_final = any('炎冷' in e.text for e in final_entities)
print(f"  '萧炎冷'在最终结果中: {'是 ❌' if has_xiaoyan_cold_final else '否 ✅'}")

# 计算NER指标
def normalize_entity(text, aliases):
    """将实体文本标准化为GT中的名称"""
    for canonical, alias_list in aliases.items():
        if text == canonical or text in alias_list:
            return canonical
    return text

predicted_normalized = set()
for e in final_entities:
    normalized = normalize_entity(e.text, gt_aliases)
    predicted_normalized.add(normalized)

# 计算TP, FP, FN
tp_set = predicted_normalized & gt_persons
fp_set = predicted_normalized - gt_persons
fn_set = gt_persons - predicted_normalized

tp = len(tp_set)
fp = len(fp_set)
fn = len(fn_set)

precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

print(f"\n【NER指标】")
print(f"  TP (正确识别): {tp}")
print(f"    {sorted(tp_set)}")
print(f"  FP (误报): {fp}")
print(f"    {sorted(fp_set)}")
print(f"  FN (漏报): {fn}")
print(f"    {sorted(fn_set)}")
print(f"  Precision: {precision:.1f}%")
print(f"  Recall: {recall:.1f}%")
print(f"  F1: {f1:.1f}")

# 检查False positives
print(f"\n【误报分析】")
if fp_set:
    print(f"  所有误报: {sorted(fp_set)}")
    # 检查是否有"萧炎冷"类误报
    false_positives_with_cold = [e for e in fp_set if '炎冷' in e or ('冷' in e and len(e) >= 3)]
    if false_positives_with_cold:
        print(f"  包含'冷'字的误报: {false_positives_with_cold}")
    else:
        print(f"  ✅ 无'萧炎冷'类误报")
else:
    print(f"  ✅ 无误报")

# 验证是否达到85.7
print(f"\n【达标检查】")
if f1 >= 85.7:
    print(f"  ✅ NER F1 = {f1:.1f} >= 85.7，达标")
else:
    print(f"  ❌ NER F1 = {f1:.1f} < 85.7，未达标")

if not has_xiaoyan_cold_final:
    print(f"  ✅ '萧炎冷'已正确过滤")
else:
    print(f"  ❌ '萧炎冷'仍在最终结果中")

print("\n" + "=" * 80)
print("验证完成")
print("=" * 80)
