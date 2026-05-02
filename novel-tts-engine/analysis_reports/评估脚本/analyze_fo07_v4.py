# -*- coding: utf-8 -*-
"""
FO-07 精确诊断：分析误报过滤
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}

nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']
per_texts = set(e.text for e in per_entities)

print(f"HanLP原始PER实体: {len(per_entities)}个, {len(per_texts)}个唯一名称")
print(f"唯一PER名称: {sorted(per_texts)}")
print()

# GT人物
gt_found = per_texts & gt_persons
gt_missing = gt_persons - per_texts
print(f"GT人物被HanLP找到: {sorted(gt_found)}")
if gt_missing:
    print(f"GT人物未被HanLP找到: {sorted(gt_missing)}")

# 非GT的PER实体（假阳性候选）
non_gt = per_texts - gt_persons
print(f"非GT的PER实体 (假阳性): {sorted(non_gt)}")
print()

# 统计每个非GT实体的出现次数
from collections import Counter
per_counter = Counter(e.text for e in per_entities)
print("非GT实体出现次数:")
for name, count in sorted(non_gt):
    count = per_counter[name]
    print(f"  {name}: {count}次")

# === 验证器对比 ===
print()
print("=" * 80)
print("验证器效果对比")
print("=" * 80)

class OldValidator(ContextDiversityValidator):
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

validator_old = OldValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2)
validated_old = validator_old.validate([e for e in result.entities], text)

validator_new = ContextDiversityValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2)
validated_new = validator_new.validate([e for e in result.entities], text)

# 对比
def summarize(entities):
    per = [e for e in entities if e.type == 'PER']
    texts = set(e.text for e in per)
    high = set(e.text for e in per if getattr(e, 'confidence', 1.0) >= 0.5)
    low = texts - high
    # TP/FP
    tp = high & gt_persons
    fp = high - gt_persons
    return texts, high, low, tp, fp

texts_o, high_o, low_o, tp_o, fp_o = summarize(validated_old)
texts_n, high_n, low_n, tp_n, fp_n = summarize(validated_new)

print(f"\n旧版验证器:")
print(f"  PER总数={len(texts_o)}, 高置信={len(high_o)}, 低置信={len(low_o)}")
print(f"  高置信GT(TP)={sorted(tp_o)}")
print(f"  高置信非GT(FP)={sorted(fp_o)}")

print(f"\n新版验证器(FO-07):")
print(f"  PER总数={len(texts_n)}, 高置信={len(high_n)}, 低置信={len(low_n)}")
print(f"  高置信GT(TP)={sorted(tp_n)}")
print(f"  高置信非GT(FP)={sorted(fp_n)}")

# 精确分析差异
if fp_o != fp_n:
    print(f"\n假阳性差异:")
    print(f"  旧版有新版无 (被FO-07过滤): {sorted(fp_o - fp_n)}")
    print(f"  新版有旧版无 (FO-07引入): {sorted(fp_n - fp_o)}")

# F1计算
def calc_f1(tp, fp, total_gt):
    recall = tp / total_gt
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * recall * precision / (recall + precision) * 100 if (recall + precision) > 0 else 0
    return recall * 100, precision * 100, f1

r_o, p_o, f1_o = calc_f1(len(tp_o), len(fp_o), len(gt_persons))
r_n, p_n, f1_n = calc_f1(len(tp_n), len(fp_n), len(gt_persons))

print(f"\nF1对比:")
print(f"  旧版: recall={r_o:.1f}%, precision={p_o:.1f}%, F1={f1_o:.1f}")
print(f"  新版: recall={r_n:.1f}%, precision={p_n:.1f}%, F1={f1_n:.1f}")

# === 详细分析被FO-07影响的实体 ===
print()
print("=" * 80)
print("FO-07 具体挽救/过滤的实体详情")
print("=" * 80)

# 查看每个非GT实体在两个验证器下的置信度
for name in sorted(non_gt):
    old_entries = [e for e in validated_old if e.text == name and e.type == 'PER']
    new_entries = [e for e in validated_new if e.text == name and e.type == 'PER']
    
    old_conf = max((getattr(e, 'confidence', 1.0) for e in old_entries), default=None)
    new_conf = max((getattr(e, 'confidence', 1.0) for e in new_entries), default=None)
    
    if old_conf != new_conf:
        count = per_counter[name]
        print(f"\n  {name} (出现{count}次):")
        print(f"    旧版置信度: {old_conf}")
        print(f"    新版置信度: {new_conf}")
        
        # 查看共现统计
        stats = validator_new._collect_context_stats([e for e in result.entities if e.type == 'PER'], text)
        if name in stats:
            s = stats[name]
            print(f"    右邻字多样性: {len(s['right_neighbors'])} -> {s['right_neighbors']}")
            print(f"    共现多样性: {s['co_occurrence_diversity']}")
            print(f"    高置信共现: {s['high_conf_co_occurrence']}")
            if s['co_occurrence']:
                top_co = sorted(s['co_occurrence'].items(), key=lambda x: x[1], reverse=True)[:5]
                print(f"    共现实体: {dict(top_co)}")
