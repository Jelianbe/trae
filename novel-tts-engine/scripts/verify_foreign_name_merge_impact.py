# -*- coding: utf-8 -*-
"""对比验证：西方名字合并对NER的影响

分别在 enable_foreign_name_merge=False 和 enable_foreign_name_merge=True
下运行三份测试文本的NER评估，验证修改是否引入回归。
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

import json
import re
import pipeline.entity_clusterer as ec
import pipeline.entity_linker as el
from pipeline.nlp_basics import get_nlp, NLPBasics
from pipeline.character_manager import CharacterManager
from pipeline.context_diversity_validator import get_context_validator, reset_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker

BASE_DIR = Path(__file__).parent.parent
TEST_DIR = BASE_DIR / "tests"

TEST_CASES = [
    ("都市", TEST_DIR / "test_novel_urban.txt", TEST_DIR / "test_novel_urban_ground_truth.json"),
    ("西幻", TEST_DIR / "test_novel_western.txt", TEST_DIR / "test_novel_western_ground_truth.json"),
    ("斗破", TEST_DIR / "test_novel_doupo_ch1-10.txt", TEST_DIR / "test_novel_doupo_ground_truth.json"),
]


def evaluate_ner_with_setting(text, ground_truth, enable_foreign_name_merge):
    """运行 NER 评估，使用指定的 enable_foreign_name_merge 设置"""
    reset_context_validator()
    
    # 创建独立实例，不修改全局单例
    nlp = NLPBasics(use_offline=True, enable_foreign_name_merge=enable_foreign_name_merge)
    # analyze() 内部会自动初始化 HanLP
    result = nlp.analyze(text)
    
    # 兼容两种GT格式
    entities = ground_truth.get("entities", ground_truth)
    gt_persons = set(entities.get("persons", []))
    gt_speaking_persons = set(entities.get("speaking_persons", gt_persons))
    gt_all = gt_persons
    
    # 上下文多样性验证
    validator = get_context_validator(
        mode='speaker_role',
        min_occurrences=2,
        high_conf_threshold=3,
        diversity_threshold=2,
        whitelist=gt_all,
    )
    validated_entities = validator.validate(result.entities, text)
    
    # 说话角色过滤器
    semantic_ranker = get_semantic_ranker()
    semantic_ranker.load_model()
    role_filter = SpeakerRoleFilter(
        semantic_ranker=semantic_ranker,
        l2_threshold=0.7,
    )
    role_entities = role_filter.filter(validated_entities, text, nlp)
    
    # 实体链接
    linker = el.get_entity_linker()
    linker.set_ground_truth(
        persons=entities.get("persons", []),
        speaking_persons=entities.get("speaking_persons", []),
        aliases=entities.get("aliases", {}),
    )
    linked_entities = linker.link(role_entities, text)
    
    # 取高置信度实体
    high_conf_entities = []
    for e in linked_entities:
        conf = getattr(e, 'confidence', 1.0)
        if conf >= 0.5:
            if conf == 0.65 and not getattr(e, 'is_linked', False):
                continue
            high_conf_entities.append(e)
    
    # 计算 PER F1
    actual_persons = set()
    for e in high_conf_entities:
        if e.type == 'PER':
            name = getattr(e, 'standard_name', '') or e.text
            actual_persons.add(name)
    
    def calc_f1(gt, actual):
        if not gt:
            return 100.0
        tp = len(gt & actual)
        recall = tp / len(gt)
        precision = tp / len(actual) if actual else 0
        if recall + precision == 0:
            return 0.0
        return 2 * recall * precision / (recall + precision) * 100
    
    f1 = calc_f1(gt_speaking_persons, actual_persons)
    
    # 统计细节
    matched = gt_speaking_persons & actual_persons
    missed = gt_speaking_persons - actual_persons
    false_pos = actual_persons - gt_speaking_persons
    
    return {
        "f1": round(f1, 1),
        "matched": sorted(matched),
        "missed": sorted(missed),
        "false_positives": sorted(false_pos),
        "total_detected": len([e for e in high_conf_entities if e.type == 'PER']),
    }


def main():
    print("=" * 70)
    print("对比验证：西方名字合并 (enable_foreign_name_merge) 对 NER 的影响")
    print("=" * 70)
    
    results = {}
    
    for genre, test_file, gt_file in TEST_CASES:
        print(f"\n{'='*70}")
        print(f"【{genre}】")
        print(f"  测试文件: {test_file.name}")
        print(f"{'='*70}")
        
        novel_text = test_file.read_text(encoding='utf-8')
        gt = json.loads(gt_file.read_text(encoding='utf-8'))
        
        for setting, label in [(False, "关闭"), (True, "开启")]:
            print(f"\n  {label} (enable_foreign_name_merge={setting})")
            result = evaluate_ner_with_setting(novel_text, gt, enable_foreign_name_merge=setting)
            
            if setting not in results:
                results[setting] = {}
            results[setting][genre] = result
            
            print(f"    F1: {result['f1']}")
            print(f"    检测到的 PER 实体数: {result['total_detected']}")
            print(f"    匹配GT: {result['matched']}")
            if result['missed']:
                print(f"    漏报: {result['missed']}")
            if result['false_positives']:
                print(f"    误报: {result['false_positives']}")
    
    # 汇总对比表
    print(f"\n\n{'='*70}")
    print("汇总对比表")
    print(f"{'='*70}")
    print(f"{'题材':<8} {'关闭F1':>8} {'开启F1':>8} {'变化':>8}")
    print("-" * 35)
    
    for genre, test_file, gt_file in TEST_CASES:
        f1_off = results[False][genre]['f1']
        f1_on = results[True][genre]['f1']
        diff = f1_on - f1_off
        sign = "+" if diff >= 0 else ""
        print(f"{genre:<8} {f1_off:>8.1f} {f1_on:>8.1f} {sign}{diff:>7.1f}")


if __name__ == "__main__":
    main()
