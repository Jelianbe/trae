# -*- coding: utf-8 -*-
"""
精确复现评估脚本的NER评分，追踪FO-07的影响
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp, filter_chapter_title_entities
from pipeline.context_diversity_validator import get_context_validator, reset_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.entity_linker import get_entity_linker, reset_entity_linker
import pipeline.entity_clusterer as ec

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}
gt_orgs = {'圣骑士团', '北方魔法学院'}
gt_locs = {'灰石哨站', '王都'}

nlp = get_nlp()

# === 模拟评估脚本的_evaluate_ner ===
def evaluate_ner_with_fo07(use_fo07=True):
    reset_context_validator()
    reset_entity_linker()
    ec.reset_entity_clusterer()
    
    result = nlp.analyze(text)
    entities = list(result.entities)
    entities = filter_chapter_title_entities(entities, text)
    
    # 获取验证器
    validator = get_context_validator()
    
    # 说话角色过滤
    semantic_ranker = get_semantic_ranker()
    semantic_ranker.load_model()
    role_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker, l2_threshold=0.7)
    
    if not use_fo07:
        # 临时替换验证器为旧版逻辑
        class OldValidator(validator.__class__):
            def _calculate_confidence(self, entity, stat):
                if entity.text in self.whitelist:
                    return entity.confidence
                occ = stat['occurrences']
                diversity = len(stat['right_neighbors'])
                if occ < self.min_occurrences:
                    return 0.3
                if occ >= self.min_occurrences and diversity <= 1:
                    return 0.2
                if occ >= self.high_conf_threshold and diversity >= self.diversity_threshold:
                    return max(entity.confidence, 0.8)
                return entity.confidence
        # 使用旧版验证器重新验证
        old_v = OldValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2)
        entities = old_v.validate(entities, text)
    else:
        entities = validator.validate(entities, text)
    
    role_entities = role_filter.filter(entities, text, nlp)
    
    # 实体链接
    linker = get_entity_linker()
    linker.set_ground_truth(persons=list(gt_persons), speaking_persons=[], aliases={})
    linked_entities = linker.link(role_entities, text)
    
    # 提取高置信PER
    high_conf_per = set()
    for e in linked_entities:
        if e.type == 'PER' and getattr(e, 'confidence', 1.0) >= 0.5:
            high_conf_per.add(e.text)
    
    # 计算PER F1
    tp = len(gt_persons & high_conf_per)
    fp = len(high_conf_per - gt_persons)
    fn = len(gt_persons - high_conf_per)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) * 100 if (precision + recall) > 0 else 0
    
    return {
        'high_conf_per': sorted(high_conf_per),
        'tp': tp, 'fp': fp, 'fn': fn,
        'precision': precision * 100,
        'recall': recall * 100,
        'f1': f1,
    }

print("西幻文本 NER 评估复现")
print("=" * 80)

result_no = evaluate_ner_with_fo07(use_fo07=False)
print("\n无FO-07:")
print(f"  高置信PER: {result_no['high_conf_per']}")
print(f"  TP={result_no['tp']}, FP={result_no['fp']}, FN={result_no['fn']}")
print(f"  Precision={result_no['precision']:.1f}%, Recall={result_no['recall']:.1f}%, F1={result_no['f1']:.1f}")

result_yes = evaluate_ner_with_fo07(use_fo07=True)
print("\n有FO-07:")
print(f"  高置信PER: {result_yes['high_conf_per']}")
print(f"  TP={result_yes['tp']}, FP={result_yes['fp']}, FN={result_yes['fn']}")
print(f"  Precision={result_yes['precision']:.1f}%, Recall={result_yes['recall']:.1f}%, F1={result_yes['f1']:.1f}")

print(f"\nFO-07带来的变化: F1 {result_no['f1']:.1f} -> {result_yes['f1']:.1f} ({result_yes['f1'] - result_no['f1']:+.1f})")

# === 现在检查实际评估脚本中的score_ner逻辑 ===
# 评估脚本用的是 _score_ner 函数，它计算每个GT人物的F1
print()
print("=" * 80)
print("逐个人物F1分析 (模拟 _score_ner 逻辑)")
print("=" * 80)

# 获取实体
ec.reset_entity_clusterer()
result = nlp.analyze(text)
entities = list(result.entities)
entities = filter_chapter_title_entities(entities, text)
entities = get_context_validator().validate(entities, text)

semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
role_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker, l2_threshold=0.7)
role_entities = role_filter.filter(entities, text, nlp)

reset_entity_linker()
linker = get_entity_linker()
linker.set_ground_truth(persons=list(gt_persons), speaking_persons=[], aliases={})
linked_entities = linker.link(role_entities, text)

high_conf_per = set()
for e in linked_entities:
    if e.type == 'PER' and getattr(e, 'confidence', 1.0) >= 0.5:
        high_conf_per.add(e.text)

# 计算每个GT人物的F1
for person in sorted(gt_persons):
    in_system = person in high_conf_per
    tp = 1 if in_system else 0
    fp = len(high_conf_per - gt_persons)
    fn = 0 if in_system else 1
    p = tp / (tp + fp) if (tp + fp) > 0 else 0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * p * r / (p + r) * 100 if (p + r) > 0 else 0
    status = "✅" if in_system else "❌"
    print(f"  {status} {person}: F1={f1:.1f}")

# 平均F1
avg_f1 = sum(
    100.0 if p in high_conf_per else 0.0
    for p in gt_persons
) / len(gt_persons)
print(f"\n平均F1: {avg_f1:.1f}")
