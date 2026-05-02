#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试脚本：逐层检查evaluate_ner()中的实体过滤情况"""

import sys
import os
from pathlib import Path

# 确保项目根目录在sys.path中
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from pipeline.nlp_basics import get_nlp
from pipeline.character_manager import get_character_manager, CharacterManager
from pipeline.context_diversity_validator import get_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.entity_clusterer import get_entity_clusterer
from pipeline.entity_linker import get_entity_linker

def debug_ner_pipeline(text_file, gt_file):
    """逐层调试NER pipeline"""
    import json
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    with open(gt_file, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    
    entities = gt.get("entities", gt)
    gt_persons = set(entities.get("persons", []))
    gt_speaking_persons = set(entities.get("speaking_persons", gt_persons))
    gt_locations = set(entities.get("locations", []))
    gt_orgs = set(entities.get("organizations", []))
    gt_all = gt_persons | gt_locations | gt_orgs
    
    # 注册角色
    char_manager = get_character_manager()
    for name in gt.get("persons", []):
        aliases = set()
        if "aliases" in gt and name in gt["aliases"]:
            aliases = set(gt["aliases"][name])
        existing = char_manager.get_character_by_name(name)
        if not existing:
            char_manager.add_character(name, gender="unknown", aliases=aliases)
    
    print(f"GT角色: {gt_persons}")
    print(f"GT说话角色: {gt_speaking_persons}")
    print(f"文本长度: {len(text)}")
    print()
    
    # 第0层：原始NER
    nlp = get_nlp()
    result = nlp.analyze(text)
    original_entities = list(result.entities)
    print(f"[0] 原始NER实体: {len(original_entities)}")
    print(f"    示例: {[e.text for e in original_entities[:10]]}")
    print()
    
    # 第1层：上下文多样性验证
    validator = get_context_validator(
        mode='speaker_role',
        min_occurrences=2,
        high_conf_threshold=3,
        diversity_threshold=2,
        whitelist=gt_all,
    )
    validated_entities = validator.validate(original_entities, text)
    print(f"[1] 上下文验证后: {len(validated_entities)}")
    print(f"    示例: {[e.text for e in validated_entities[:10]]}")
    print()
    
    # 第2层：说话角色过滤
    semantic_ranker = get_semantic_ranker()
    semantic_ranker.load_model()
    role_filter = SpeakerRoleFilter(
        semantic_ranker=semantic_ranker,
        l2_threshold=0.7,
    )
    role_entities = role_filter.filter(validated_entities, text, nlp)
    print(f"[2] 说话角色过滤后: {len(role_entities)}")
    print(f"    示例: {[e.text for e in role_entities[:10]]}")
    print()
    
    # 第3层：角色聚类
    clusterer = get_entity_clusterer(
        semantic_ranker=semantic_ranker,
        merge_threshold=0.85,
        new_threshold=0.5,
        min_occurrences=2,
    )
    clustered_entities = clusterer.cluster(role_entities, text)
    print(f"[3] 角色聚类后: {len(clustered_entities)}")
    print(f"    示例: {[e.text for e in clustered_entities[:10]]}")
    print()
    
    # 第4层：实体链接
    linker = get_entity_linker()
    linker.set_ground_truth(
        persons=entities.get("persons", []),
        speaking_persons=entities.get("speaking_persons", []),
        aliases=entities.get("aliases", {}),
    )
    linked_entities = linker.link(clustered_entities, text)
    print(f"[4] 实体链接后: {len(linked_entities)}")
    print(f"    示例: {[(e.text, getattr(e, 'standard_name', ''), getattr(e, 'is_linked', False)) for e in linked_entities[:10]]}")
    print()
    
    # 最终过滤
    high_conf_entities = [e for e in linked_entities if getattr(e, 'confidence', 1.0) >= 0.5]
    print(f"[5] 高置信度过滤后: {len(high_conf_entities)}")
    actual_persons = set(e.text for e in high_conf_entities if e.type == 'PER')
    print(f"    实际PER: {actual_persons}")
    print(f"    GT PER: {gt_speaking_persons}")
    print(f"    匹配: {gt_speaking_persons & actual_persons}")
    print()
    
    # 计算F1
    if gt_speaking_persons:
        recall = len(gt_speaking_persons & actual_persons) / len(gt_speaking_persons)
        precision = len(gt_speaking_persons & actual_persons) / len(actual_persons) if actual_persons else 0
        f1 = 2 * recall * precision / (recall + precision) * 100 if (recall + precision) > 0 else 0
        print(f"召回率: {recall:.2%}")
        print(f"精确率: {precision:.2%}")
        print(f"F1: {f1:.1f}")
    else:
        print("GT为空")

if __name__ == "__main__":
    import os
    os.environ['DEBUG_NER'] = '0'
    
    print("=" * 60)
    print("调试: 都市异能")
    print("=" * 60)
    debug_ner_pipeline(
        "tests/test_novel_urban.txt",
        "tests/test_novel_urban_ground_truth.json"
    )
