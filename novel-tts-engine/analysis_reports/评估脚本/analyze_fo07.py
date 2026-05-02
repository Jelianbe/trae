# -*- coding: utf-8 -*-
"""
FO-07 共现统计诊断脚本
分析西幻文本中哪些实体被共现统计挽救
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import ContextDiversityValidator

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

nlp = get_nlp()
result = nlp.analyze(text)

entities = list(result.entities)
print(f"HanLP原始识别实体数: {len(entities)}")
print()

# === 没有FO-07的验证（旧版）===
validator_old = ContextDiversityValidator(
    mode='speaker_role',
    min_occurrences=2,
    high_conf_threshold=3,
    diversity_threshold=2,
)
validated_old = validator_old.validate(entities[:], text)

# === 有FO-07的验证（新版）===
validator_new = ContextDiversityValidator(
    mode='speaker_role',
    min_occurrences=2,
    high_conf_threshold=3,
    diversity_threshold=2,
)
validated_new = validator_new.validate(entities[:], text)

# === 对比 ===
print("=" * 80)
print("FO-07 共现统计效果分析")
print("=" * 80)
print()

# 按实体文本分组
from collections import defaultdict
old_conf: dict[str, float] = {}
new_conf: dict[str, float] = {}
for e in validated_old:
    old_conf[e.text] = max(old_conf.get(e.text, 0), e.confidence)
for e in validated_new:
    new_conf[e.text] = max(new_conf.get(e.text, 0), e.confidence)

saved_entities = []
degraded_entities = []
for entity_text in set(list(old_conf.keys()) + list(new_conf.keys())):
    old_c = old_conf.get(entity_text, 0)
    new_c = new_conf.get(entity_text, 0)
    if new_c > old_c:
        saved_entities.append((entity_text, old_c, new_c))
    elif new_c < old_c:
        degraded_entities.append((entity_text, old_c, new_c))

print(f"被FO-07挽救的实体 (置信度提升): {len(saved_entities)} 个")
print("-" * 80)
for name, old_c, new_c in sorted(saved_entities, key=lambda x: x[2] - x[1], reverse=True):
    diff = new_c - old_c
    marker = " ✅" if old_c < 0.5 and new_c >= 0.5 else ""
    print(f"  {name:15s}  {old_c:.1f} -> {new_c:.1f}  (Δ{diff:+.1f}){marker}")

print()
print(f"被FO-07降低的实体: {len(degraded_entities)} 个")
print("-" * 80)
for name, old_c, new_c in sorted(degraded_entities, key=lambda x: x[2] - x[1]):
    diff = new_c - old_c
    print(f"  {name:15s}  {old_c:.1f} -> {new_c:.1f}  (Δ{diff:+.1f})")

# === 详细分析被挽救的关键实体 ===
print()
print("=" * 80)
print("关键实体挽救详情")
print("=" * 80)

gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}

for name, old_c, new_c in sorted(saved_entities, key=lambda x: x[2] - x[1], reverse=True):
    if old_c < 0.5 and new_c >= 0.5:
        is_gt = "GT实体" if name in gt_persons else "非GT"
        print(f"\n  {name} ({is_gt}):")
        print(f"    旧置信度: {old_c} (被过滤)")
        print(f"    新置信度: {new_c} (被保留)")
        
        # 查看共现统计
        stats = validator_new._collect_context_stats(entities, text)
        if name in stats:
            s = stats[name]
            print(f"    出现次数: {s['occurrences']}")
            print(f"    右邻字多样性: {len(s['right_neighbors'])}")
            print(f"    共现多样性: {s['co_occurrence_diversity']}")
            print(f"    与高置信度实体共现: {s['high_conf_co_occurrence']}次")
            
            if s['co_occurrence']:
                top_co = sorted(s['co_occurrence'].items(), key=lambda x: x[1], reverse=True)[:5]
                co_str = ', '.join(f"{k}({v}次)" for k, v in top_co)
                print(f"    主要共现实体: {co_str}")
