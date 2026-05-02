# -*- coding: utf-8 -*-
"""
FO-07 在都市和修仙文本中的效果对比
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp, filter_chapter_title_entities
from pipeline.context_diversity_validator import ContextDiversityValidator, get_context_validator, reset_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.entity_linker import get_entity_linker, reset_entity_linker
import pipeline.entity_clusterer as ec

test_files = {
    '都市': ('tests/test_novel_urban.txt', {'林远', '苏晴', '赵铁柱'}),
    '修仙': ('tests/test_novel_cultivation.txt', {'李云天', '苏明月', '张三'}),
}

nlp = get_nlp()
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()

for name, (file_path, gt_persons) in test_files.items():
    print("=" * 80)
    print(f"{name}文本 FO-07 效果分析")
    print("=" * 80)
    
    text = Path(file_path).read_text(encoding='utf-8')
    result = nlp.analyze(text)
    per_entities = [e for e in result.entities if e.type == 'PER']
    per_texts = set(e.text for e in per_entities)
    
    gt_found = per_texts & gt_persons
    non_gt = per_texts - gt_persons
    
    print(f"  HanLP原始PER: {len(per_entities)}个, {len(per_texts)}个唯一名称")
    print(f"  GT人物被找到: {sorted(gt_found)}")
    print(f"  非GT实体(假阳性候选): {sorted(non_gt)}")
    print(f"  非GT实体数量: {len(non_gt)}")
    
    # 统计非GT实体出现次数
    from collections import Counter
    per_counter = Counter(e.text for e in per_entities)
    freq_non_gt = [(n, per_counter[n]) for n in non_gt if per_counter[n] >= 2]
    if freq_non_gt:
        print(f"  出现>=2次的非GT实体: {freq_non_gt}")
    
    # 对比有/无FO-07
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
    
    gt_all = gt_persons  # 简化白名单
    
    validator_old = OldValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2, whitelist=gt_all)
    validated_old = validator_old.validate([e for e in result.entities], text)
    
    validator_new = ContextDiversityValidator(mode='speaker_role', min_occurrences=2, high_conf_threshold=3, diversity_threshold=2, whitelist=gt_all)
    validated_new = validator_new.validate([e for e in result.entities], text)
    
    def get_high_conf(entities):
        return set(e.text for e in entities if e.type == 'PER' and getattr(e, 'confidence', 1.0) >= 0.5)
    
    high_old = get_high_conf(validated_old)
    high_new = get_high_conf(validated_new)
    
    tp_old = len(gt_persons & high_old)
    fp_old = len(high_old - gt_persons)
    tp_new = len(gt_persons & high_new)
    fp_new = len(high_new - gt_persons)
    
    def calc_f1(tp, fp, total_gt):
        recall = tp / total_gt
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * recall * precision / (recall + precision) * 100 if (recall + precision) > 0 else 0
        return recall * 100, precision * 100, f1
    
    r_o, p_o, f1_o = calc_f1(tp_old, fp_old, len(gt_persons))
    r_n, p_n, f1_n = calc_f1(tp_new, fp_new, len(gt_persons))
    
    print(f"\n  旧版验证器: TP={tp_old}, FP={fp_old}, F1={f1_o:.1f}")
    print(f"  新版(FO-07): TP={tp_new}, FP={fp_new}, F1={f1_n:.1f}")
    
    if fp_old != fp_new:
        print(f"\n  假阳性变化:")
        print(f"    被FO-07过滤: {sorted(fp_old - fp_new)}")
        print(f"    被FO-07引入: {sorted(fp_new - fp_old)}")
    
    if high_old != high_new:
        print(f"\n  高置信实体变化:")
        for n in sorted(high_new - high_old):
            print(f"    + {n} (FO-07提升)")
        for n in sorted(high_old - high_new):
            print(f"    - {n} (FO-07过滤)")
    
    print()
