# -*- coding: utf-8 -*-
"""
FO-07 完整NER诊断：包含ORG和LOC
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.entity_linker import get_entity_linker, reset_entity_linker

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}
gt_orgs = {'圣骑士团', '北方魔法学院'}
gt_locs = {'灰石哨站', '王都'}
gt_all = gt_persons | gt_orgs | gt_locs

nlp = get_nlp()
result = nlp.analyze(text)

print(f"HanLP原始实体: {len(result.entities)}个")
print()

# 按类型分组
from collections import Counter, defaultdict
by_type = defaultdict(list)
for e in result.entities:
    by_type[e.type].append(e.text)

for t in ['PER', 'ORG', 'LOC', 'DATE', 'TIME']:
    texts = by_type.get(t, [])
    print(f"  {t}: {len(texts)}个, 唯一={sorted(set(texts))}")
print()

# 查看GT组织和地点
print("GT组织识别情况:")
for org in sorted(gt_orgs):
    matches = [e for e in result.entities if e.text == org]
    print(f"  {org}: HanLP匹配={len(matches)}次")
    if not matches:
        # 看看有没有相似匹配
        similar = [e for e in result.entities if org.startswith(e.text) or e.text in org]
        print(f"    部分匹配: {[e.text for e in similar]}")

print("\nGT地点识别情况:")
for loc in sorted(gt_locs):
    matches = [e for e in result.entities if e.text == loc]
    print(f"  {loc}: HanLP匹配={len(matches)}次")
    if not matches:
        similar = [e for e in result.entities if loc.startswith(e.text) or e.text in loc]
        print(f"    部分匹配: {[e.text for e in similar]}")

# === 完整NER流水线对比 ===
print()
print("=" * 80)
print("完整NER流水线对比")
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

def run_pipeline(entities, use_fo07=True):
    validator = ContextDiversityValidator(
        mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2
    ) if use_fo07 else OldValidator(
        mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2
    )
    validated = validator.validate([e for e in entities], text)
    
    semantic_ranker = get_semantic_ranker()
    semantic_ranker.load_model()
    role_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker, l2_threshold=0.7)
    role = role_filter.filter(validated, text, nlp)
    
    reset_entity_linker()
    linker = get_entity_linker()
    linker.set_ground_truth(persons=list(gt_persons), speaking_persons=[], aliases={})
    linked = linker.link(role, text)
    
    return linked

linked_old = run_pipeline(result.entities, use_fo07=False)
linked_new = run_pipeline(result.entities, use_fo07=True)

high_old = [e for e in linked_old if getattr(e, 'confidence', 1.0) >= 0.5]
high_new = [e for e in linked_new if getattr(e, 'confidence', 1.0) >= 0.5]

# 按类型统计
def summarize(entities):
    by_type = defaultdict(set)
    for e in entities:
        by_type[e.type].add(e.text)
    return dict(by_type)

old_summary = summarize(high_old)
new_summary = summarize(high_new)

print(f"\n旧版高置信实体:")
for t in ['PER', 'ORG', 'LOC']:
    print(f"  {t}: {sorted(old_summary.get(t, set()))}")

print(f"\n新版(FO-07)高置信实体:")
for t in ['PER', 'ORG', 'LOC']:
    print(f"  {t}: {sorted(new_summary.get(t, set()))}")

# F1计算
def calc_f1(gt, actual):
    if not gt:
        return 100.0
    recall = len(gt & actual) / len(gt)
    precision = len(gt & actual) / len(actual) if actual else 0
    if recall + precision == 0:
        return 0
    return 2 * recall * precision / (recall + precision) * 100

old_per = calc_f1(gt_persons, old_summary.get('PER', set()))
old_org = calc_f1(gt_orgs, old_summary.get('ORG', set()))
old_loc = calc_f1(gt_locs, old_summary.get('LOC', set()))
old_avg = (old_per + old_org + old_loc) / 3

new_per = calc_f1(gt_persons, new_summary.get('PER', set()))
new_org = calc_f1(gt_orgs, new_summary.get('ORG', set()))
new_loc = calc_f1(gt_locs, new_summary.get('LOC', set()))
new_avg = (new_per + new_org + new_loc) / 3

print(f"\nF1对比:")
print(f"  旧版: PER={old_per:.1f}, ORG={old_org:.1f}, LOC={old_loc:.1f}, 平均={old_avg:.1f}")
print(f"  新版: PER={new_per:.1f}, ORG={new_org:.1f}, LOC={new_loc:.1f}, 平均={new_avg:.1f}")

# 找出差异
for t in ['PER', 'ORG', 'LOC']:
    gt_set = {'PER': gt_persons, 'ORG': gt_orgs, 'LOC': gt_locs}[t]
    old_set = old_summary.get(t, set())
    new_set = new_summary.get(t, set())
    
    if old_set != new_set:
        print(f"\n{t}差异:")
        print(f"  旧版有新版无: {old_set - new_set}")
        print(f"  新版有旧版无: {new_set - old_set}")
        print(f"  GT中有旧版缺失: {gt_set - old_set}")
        print(f"  GT中有新版缺失: {gt_set - new_set}")
    else:
        print(f"\n{t}: 无差异")
