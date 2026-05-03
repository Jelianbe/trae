# -*- coding: utf-8 -*-
"""
完整pipeline验证误合并检测修复效果

Pipeline: NLPBasics → ContextDiversityValidator → SpeakerRoleFilter → EntityLinker
"""
import sys
from pathlib import Path
import json

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
print("完整pipeline验证误合并检测修复效果")
print("=" * 80)

# Step 1: NLPBasics
nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']

print(f"\n【Step 1】NLPBasics分析")
print(f"  PER实体数: {len(per_entities)}")
print(f"  唯一PER: {len(set(e.text for e in per_entities))}")

# Step 2: ContextDiversityValidator（包含误合并检测）
validator = get_context_validator(mode='speaker_role', whitelist=gt_speaking_persons)
validated = validator.validate(per_entities, text)

print(f"\n【Step 2】统计验证 + 误合并检测后")
print(f"  实体数: {len(validated)}")
print(f"  唯一实体: {len(set(e.text for e in validated))}")

# 检查"萧炎冷"
xiaoyan_cold_after_step2 = [e for e in validated if '炎冷' in e.text]
if xiaoyan_cold_after_step2:
    print(f"  ⚠️ '萧炎冷'仍在结果中（confidence={xiaoyan_cold_after_step2[0].confidence:.2f}）")
else:
    print(f"  ✅ '萧炎冷'已过滤")

# Step 3: SpeakerRoleFilter
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()

speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
role_entities = speaker_filter.filter(validated, text, nlp)

print(f"\n【Step 3】SpeakerRoleFilter后")
print(f"  实体数: {len(role_entities)}")
print(f"  唯一实体: {len(set(e.text for e in role_entities))}")

# 检查"萧炎冷"
xiaoyan_cold_after_step3 = [e for e in role_entities if '炎冷' in e.text]
if xiaoyan_cold_after_step3:
    print(f"  ⚠️ '萧炎冷'仍在结果中（confidence={xiaoyan_cold_after_step3[0].confidence:.2f}）")
else:
    print(f"  ✅ '萧炎冷'已过滤")

# Step 4: EntityLinker
linker = get_entity_linker()
linker.set_ground_truth(
    persons=list(gt_persons),
    speaking_persons=list(gt_speaking_persons),
    aliases=gt_aliases,
)
linked = linker.link(role_entities, text)

print(f"\n【Step 4】EntityLinker后")
print(f"  实体数: {len(linked)}")

# Step 5: 最终过滤（confidence >= 0.5）
final_entities = [e for e in linked if e.confidence >= 0.5]
final_texts = set()
for e in final_entities:
    # 使用standard_name（如果已链接）或原始text
    name = e.standard_name if e.standard_name else e.text
    final_texts.add(name)

print(f"\n【Step 5】最终过滤后 (confidence >= 0.5)")
print(f"  最终实体数: {len(final_entities)}")
print(f"  唯一实体（标准化后）: {len(final_texts)}")

# 最终检查"萧炎冷"
has_xiaoyan_cold = any('炎冷' in e.text for e in final_entities)
print(f"  '萧炎冷'在最终结果中: {'是 ❌' if has_xiaoyan_cold else '否 ✅'}")

# 打印最终实体列表
print(f"\n  最终实体列表:")
for e in sorted(final_texts):
    print(f"    {e}")

# 计算NER指标
# TP: 预测和GT都有的
tp_set = final_texts & gt_persons
# FP: 预测有但GT没有
fp_set = final_texts - gt_persons
# FN: GT有但预测没有
fn_set = gt_persons - final_texts

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
if fp_set:
    print(f"    {sorted(fp_set)}")
print(f"  FN (漏报): {fn}")
if fn_set:
    print(f"    {sorted(fn_set)}")
print(f"  Precision: {precision:.1f}%")
print(f"  Recall: {recall:.1f}%")
print(f"  F1: {f1:.1f}")

# 达标检查
print(f"\n【达标检查】")
if f1 >= 85.7:
    print(f"  ✅ NER F1 = {f1:.1f} >= 85.7，达标")
else:
    print(f"  ⚠️ NER F1 = {f1:.1f} < 85.7")

if not has_xiaoyan_cold:
    print(f"  ✅ '萧炎冷'已正确过滤")
else:
    print(f"  ❌ '萧炎冷'仍在最终结果中")

print("\n" + "=" * 80)
print("验证完成")
print("=" * 80)
