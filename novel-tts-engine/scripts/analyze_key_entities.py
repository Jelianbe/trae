# -*- coding: utf-8 -*-
"""
详细分析"萧炎冷"和"纳兰肃"的统计信息
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp, Entity
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
print("详细分析萧炎冷和纳兰肃")
print("=" * 80)

# 获取NER结果
nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']

# 收集统计信息
validator = get_context_validator(mode='speaker_role', whitelist=gt_speaking_persons)
stats = validator._collect_context_stats(per_entities, text)

# 分析关键实体
key_entities = ['萧炎冷', '萧炎承', '纳兰肃', '萧炎', '纳兰', '纳兰嫣然']

print(f"\n【关键实体统计】")
for entity in key_entities:
    if entity in stats:
        stat = stats[entity]
        print(f"\n{entity}:")
        print(f"  出现次数: {stat['occurrences']}")
        print(f"  右邻字: {stat['right_neighbors']}")
        print(f"  右邻字种类: {len(stat['right_neighbors'])}")
        
        # 检查是否是GT中的人物
        if entity in gt_persons:
            print(f"  ⚠️ 是GT人物")
        
        # 检查可能的前缀
        for suffix_len in [1, 2]:
            if len(entity) > suffix_len:
                prefix = entity[:-suffix_len]
                if prefix in stats:
                    prefix_stat = stats[prefix]
                    ratio = stat['occurrences'] / prefix_stat['occurrences'] * 100
                    print(f"  前缀{prefix}: 出现{prefix_stat['occurrences']}次, 比率={ratio:.1f}%")

# 检查误合并检测结果
mis_merged = validator._detect_mis_merged_entities(per_entities, stats, text)
print(f"\n\n【误合并检测结果】")
print(f"被标记的实体: {sorted(mis_merged)}")

# 检查萧炎冷是否在mis_merged中
print(f"\n萧炎冷在mis_merged中: {'萧炎冷' in mis_merged}")
print(f"纳兰肃在mis_merged中: {'纳兰肃' in mis_merged}")
print(f"萧炎承在mis_merged中: {'萧炎承' in mis_merged}")

print("\n" + "=" * 80)
