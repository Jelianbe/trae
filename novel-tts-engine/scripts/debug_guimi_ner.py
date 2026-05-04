# -*- coding: utf-8 -*-
"""调试：诡秘之主NER为什么全部为空"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.nlp_basics import get_nlp
from pipeline.entity_linker import get_entity_linker
from pipeline.context_diversity_validator import get_context_validator, reset_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests", "test_novel_guimi_ch1-10.txt")

with open(SRC, "r", encoding="utf-8") as f:
    text = f.read()

# 只取前3000字
sample = text[:3000]

print("=== 第1步：NLP 基础分析 ===")
nlp = get_nlp()
result = nlp.analyze(sample)
print(f"Token数: {len(result.tokens)}")
print(f"实体数: {len(result.entities)}")

# 检查原始 NER 输出
print("\n原始 NER 实体 (前20):")
for e in result.entities[:20]:
    print(f"  [{e.type}] {e.text} (start={e.start}, end={e.end}, conf={e.confidence:.2f})")

per_entities = [e for e in result.entities if e.type == 'PER']
print(f"\nPER 实体数: {len(per_entities)}")
for e in per_entities:
    print(f"  {e.text}")

# 检查 filter_false_persons 的影响
print("\n=== 第2步：上下文多样性验证 ===")
reset_context_validator()
validator = get_context_validator()
validated = validator.validate(result.entities, sample)
print(f"验证后实体数: {len(validated)}")
for e in validated[:20]:
    print(f"  [{e.type}] {e.text} (conf={e.confidence:.2f})")

# 检查说话角色过滤
print("\n=== 第3步：说话角色过滤 ===")
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
role_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
filtered = role_filter.filter(validated, sample, nlp)
print(f"过滤后实体数: {len(filtered)}")
for e in filtered:
    print(f"  [{e.type}] {e.text} (conf={e.confidence:.2f})")

# 检查实体链接
print("\n=== 第4步：实体链接 ===")
linker = get_entity_linker()
linked = linker.link(filtered, sample)
print(f"链接后实体数: {len(linked)}")
for e in linked:
    sn = getattr(e, 'standard_name', '') or ''
    print(f"  [{e.type}] {e.text} -> {sn} (conf={e.confidence:.2f})")
