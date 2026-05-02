# -*- coding: utf-8 -*-
"""
FO-07 完整NER流水线诊断
对比有/无FO-07时的完整NER F1分数
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pipeline.entity_clusterer as ec
import pipeline.entity_linker as el
from pipeline.nlp_basics import get_nlp, filter_chapter_title_entities
from pipeline.context_diversity_validator import get_context_validator, reset_context_validator, ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.entity_linker import get_entity_linker, reset_entity_linker

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

# GT数据
gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}
gt_orgs = {'圣骑士团', '北方魔法学院'}
gt_locs = {'灰石哨站', '王都'}
gt_all = gt_persons | gt_orgs | gt_locs

nlp = get_nlp()
result = nlp.analyze(text)
entities = list(result.entities)
print(f"HanLP原始识别: {len(entities)} 个实体")
print(f"  PER实体: {[e.text for e in entities if e.type == 'PER']}")
print()

# ================================================================
# 场景A: 不使用FO-07（旧版验证器，不统计共现）
# ================================================================
print("=" * 80)
print("场景A: 无FO-07（旧版验证逻辑）")
print("=" * 80)

reset_context_validator()
validator_a = ContextDiversityValidator(
    mode='speaker_role',
    min_occurrences=2,
    high_conf_threshold=3,
    diversity_threshold=2,
    whitelist=gt_all,
)
validated_a = validator_a.validate([e for e in entities], text)

# 说话角色过滤
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
role_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker, l2_threshold=0.7)
role_a = role_filter.filter(validated_a, text, nlp)

# 实体链接
reset_entity_linker()
linker = get_entity_linker()
linker.set_ground_truth(persons=list(gt_persons), speaking_persons=[], aliases={})
linked_a = linker.link(role_a, text)

high_conf_a = [e for e in linked_a if getattr(e, 'confidence', 1.0) >= 0.5]
actual_persons_a = set(e.text for e in high_conf_a if e.type == 'PER')
print(f"最终高置信PER实体 ({len(high_conf_a)}): {[e.text for e in high_conf_a]}")
print(f"实际人物: {actual_persons_a}")

recall_a = len(gt_persons & actual_persons_a) / len(gt_persons) if gt_persons else 1
precision_a = len(gt_persons & actual_persons_a) / len(actual_persons_a) if actual_persons_a else 0
f1_a = 2 * recall_a * precision_a / (recall_a + precision_a) * 100 if (recall_a + precision_a) > 0 else 0
print(f"人物F1: recall={recall_a:.2f}, precision={precision_a:.2f}, F1={f1_a:.1f}")

# 被过滤掉的GT实体
missing_a = gt_persons - actual_persons_a
if missing_a:
    print(f"缺失的GT人物: {missing_a}")

# ================================================================
# 场景B: 使用FO-07（新版验证器，统计共现）
# ================================================================
print()
print("=" * 80)
print("场景B: 有FO-07（新版验证逻辑）")
print("=" * 80)

reset_context_validator()
reset_entity_linker()

validator_b = ContextDiversityValidator(
    mode='speaker_role',
    min_occurrences=2,
    high_conf_threshold=3,
    diversity_threshold=2,
    whitelist=gt_all,
)
validated_b = validator_b.validate([e for e in entities], text)

role_b = role_filter.filter(validated_b, text, nlp)

linker = get_entity_linker()
linker.set_ground_truth(persons=list(gt_persons), speaking_persons=[], aliases={})
linked_b = linker.link(role_b, text)

high_conf_b = [e for e in linked_b if getattr(e, 'confidence', 1.0) >= 0.5]
actual_persons_b = set(e.text for e in high_conf_b if e.type == 'PER')
print(f"最终高置信PER实体 ({len(high_conf_b)}): {[e.text for e in high_conf_b]}")
print(f"实际人物: {actual_persons_b}")

recall_b = len(gt_persons & actual_persons_b) / len(gt_persons) if gt_persons else 1
precision_b = len(gt_persons & actual_persons_b) / len(actual_persons_b) if actual_persons_b else 0
f1_b = 2 * recall_b * precision_b / (recall_b + precision_b) * 100 if (recall_b + precision_b) > 0 else 0
print(f"人物F1: recall={recall_b:.2f}, precision={precision_b:.2f}, F1={f1_b:.1f}")

missing_b = gt_persons - actual_persons_b
if missing_b:
    print(f"缺失的GT人物: {missing_b}")

# ================================================================
# 差异分析
# ================================================================
print()
print("=" * 80)
print("对比结果")
print("=" * 80)
print(f"场景A F1: {f1_a:.1f}")
print(f"场景B F1: {f1_b:.1f}")
print(f"差异: {f1_b - f1_a:+.1f}")

# 对比两个场景的实际输出
if actual_persons_a != actual_persons_b:
    print(f"\n场景A有但场景B无: {actual_persons_a - actual_persons_b}")
    print(f"场景B有但场景A无: {actual_persons_b - actual_persons_a}")
else:
    print(f"\n两个场景的输出完全相同")

# 分析所有实体置信度分布
print()
print("所有实体置信度分布 (场景A vs 场景B):")
conf_a = {}
conf_b = {}
for e in high_conf_a:
    conf_a[e.text] = max(conf_a.get(e.text, 0), e.confidence)
for e in high_conf_b:
    conf_b[e.text] = max(conf_b.get(e.text, 0), e.confidence)

all_texts = set(list(conf_a.keys()) + list(conf_b.keys()))
for t in sorted(all_texts):
    a = conf_a.get(t, "N/A")
    b = conf_b.get(t, "N/A")
    marker = " GT" if t in gt_persons else ""
    print(f"  {t:15s}  A={a}  B={b}{marker}")
