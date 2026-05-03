#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
追踪"萧炎冷"在整个管道中的confidence变化
验证假设：统计验证结果是否在管道传输中被覆盖
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
from pipeline.nlp_basics import NLPBasics
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.entity_linker import get_entity_linker
from pipeline.semantic_ranker import get_semantic_ranker

nlp = NLPBasics()

with open('tests/test_novel_doupo_ch1-10.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("=" * 80)
print("追踪'萧炎冷'在管道中的confidence变化")
print("=" * 80)

# Step 1: NLPBasics分析
result = nlp.analyze(text)
print(f"\n[Step 1] nlp.analyze() 后:")
for e in result.entities:
    if '冷' in e.text:
        print(f"  实体: {e.text} (type={e.type}, confidence={e.confidence})")

# Step 2: ContextDiversityValidator
validator = ContextDiversityValidator()
validated = validator.validate(result.entities, text)
print(f"\n[Step 2] ContextDiversityValidator.validate() 后:")
for e in validated:
    if '冷' in e.text:
        print(f"  实体: {e.text} (type={e.type}, confidence={e.confidence})")

# Step 3: SpeakerRoleFilter
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
role_filter = SpeakerRoleFilter(
    semantic_ranker=semantic_ranker,
    l2_threshold=0.7,
)
role_entities = role_filter.filter(validated, text, nlp)
print(f"\n[Step 3] SpeakerRoleFilter.filter() 后:")
for e in role_entities:
    if '冷' in e.text:
        print(f"  实体: {e.text} (type={e.type}, confidence={e.confidence})")

# Step 4: EntityLinker
linker = get_entity_linker()
with open('tests/test_novel_doupo_ground_truth.json', 'r', encoding='utf-8') as f:
    gt = json.load(f)
entities_data = gt.get('entities', {})
linker.set_ground_truth(
    persons=entities_data.get('persons', []),
    speaking_persons=entities_data.get('speaking_persons', []),
    aliases=entities_data.get('aliases', {}),
)
linked = linker.link(role_entities, text)
print(f"\n[Step 4] EntityLinker.link() 后:")
for e in linked:
    if '冷' in e.text:
        print(f"  实体: {e.text} (type={e.type}, confidence={e.confidence}, is_linked={e.is_linked}, standard_name='{e.standard_name}')")

# Step 5: 最终过滤
high_conf = [e for e in linked if getattr(e, 'confidence', 1.0) >= 0.5]
print(f"\n[Step 5] 最终过滤 (confidence >= 0.5) 后:")
for e in high_conf:
    if '冷' in e.text:
        print(f"  实体: {e.text} (type={e.type}, confidence={e.confidence})")

print("\n" + "=" * 80)
print("结论：")
print("=" * 80)
