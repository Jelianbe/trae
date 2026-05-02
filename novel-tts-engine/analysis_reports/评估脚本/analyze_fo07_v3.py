# -*- coding: utf-8 -*-
"""
FO-07 精确诊断：逐步追踪NER流水线
对比有/无FO-07时每个阶段的实体变化
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.character_manager import CharacterManager

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}
gt_orgs = {'圣骑士团', '北方魔法学院'}
gt_locs = {'灰石哨站', '王都'}
gt_all = gt_persons | gt_orgs | gt_locs

nlp = get_nlp()
result = nlp.analyze(text)

print(f"HanLP原始实体数: {len(result.entities)}")
per_entities = [e for e in result.entities if e.type == 'PER']
print(f"PER实体数: {len(per_entities)}")
per_texts = sorted(set(e.text for e in per_entities))
print(f"PER实体列表: {per_texts}")
print()

# 查看每个GT人物在HanLP中的表现
print("GT人物在HanLP中的检测情况:")
for person in sorted(gt_persons):
    matches = [e for e in result.entities if e.text == person]
    variants = [e for e in result.entities if person.startswith(e.text) or e.text.startswith(person)[:-1]]
    print(f"  {person}: 精确匹配={len(matches)}次")
    if matches:
        confs = [getattr(e, 'confidence', 1.0) for e in matches]
        print(f"    置信度范围: {min(confs):.2f} ~ {max(confs):.2f}")

# 查看HanLP识别到但不在GT中的PER实体
print()
print("HanLP识别的额外PER实体 (不在GT中):")
non_gt_per = sorted(set(e.text for e in per_entities if e.text not in gt_persons))
for name in non_gt_per:
    count = sum(1 for e in per_entities if e.text == name)
    confs = [getattr(e, 'confidence', 1.0) for e in per_entities if e.text == name]
    print(f"  {name}: {count}次, 置信度 {min(confs):.2f}~{max(confs):.2f}")

# === 对比有/无FO-07的验证器 ===
print()
print("=" * 80)
print("对比验证器行为")
print("=" * 80)

# 创建一个没有FO-07效果的验证器（使用旧版_calculate_confidence逻辑）
class OldValidator(ContextDiversityValidator):
    """旧版验证器：不使用共现统计"""
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

# 场景A: 旧版验证器
validator_a = OldValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2)
validated_a = validator_a.validate([e for e in result.entities], text)

# 场景B: 新版验证器(FO-07)
validator_b = ContextDiversityValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2)
validated_b = validator_b.validate([e for e in result.entities], text)

def get_per_info(entities):
    per = [e for e in entities if e.type == 'PER']
    texts = set(e.text for e in per)
    high_conf = set(e.text for e in per if getattr(e, 'confidence', 1.0) >= 0.5)
    low_conf = set(e.text for e in per if getattr(e, 'confidence', 1.0) < 0.5)
    return texts, high_conf, low_conf

texts_a, high_a, low_a = get_per_info(validated_a)
texts_b, high_b, low_b = get_per_info(validated_b)

print(f"\n场景A (旧版): PER总数={len(texts_a)}, 高置信={len(high_a)}, 低置信={len(low_a)}")
print(f"  高置信PER: {sorted(high_a)}")
if low_a:
    print(f"  低置信PER: {sorted(low_a)}")

print(f"\n场景B (FO-07): PER总数={len(texts_b)}, 高置信={len(high_b)}, 低置信={len(low_b)}")
print(f"  高置信PER: {sorted(high_b)}")
if low_b:
    print(f"  低置信PER: {sorted(low_b)}")

# 找出差异
if high_a != high_b:
    print(f"\n差异: A有B无={high_a - high_b}, B有A无={high_b - high_a}")
else:
    print(f"\n验证器层面无差异")

# === 现在加上角色过滤器 ===
print()
print("=" * 80)
print("加上SpeakerRoleFilter后的效果")
print("=" * 80)

semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
role_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker, l2_threshold=0.7)

role_a = role_filter.filter(validated_a, text, nlp)
role_b = role_filter.filter(validated_b, text, nlp)

texts_ra, high_ra, low_ra = get_per_info(role_a)
texts_rb, high_rb, low_rb = get_per_info(role_b)

print(f"\n场景A (旧版+过滤): PER总数={len(texts_ra)}, 高置信={len(high_ra)}, 低置信={len(low_ra)}")
print(f"  高置信PER: {sorted(high_ra)}")

print(f"\n场景B (FO-07+过滤): PER总数={len(texts_rb)}, 高置信={len(high_rb)}, 低置信={len(low_rb)}")
print(f"  高置信PER: {sorted(high_rb)}")

if high_ra != high_rb:
    print(f"\n差异: A有B无={high_ra - high_rb}, B有A无={high_rb - high_ra}")
    
    # 详细分析被过滤掉的实体
    for name in high_rb - high_ra:
        print(f"\n  {name} 被旧版过滤但被FO-07保留:")
        # 查看旧版中这个实体的情况
        old_entries = [e for e in validated_a if e.text == name and e.type == 'PER']
        new_entries = [e for e in validated_b if e.text == name and e.type == 'PER']
        if old_entries:
            print(f"    旧版置信度: {old_entries[0].confidence}")
        if new_entries:
            print(f"    新版置信度: {new_entries[0].confidence}")
else:
    print(f"\n角色过滤器层面无差异")
