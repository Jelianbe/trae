# -*- coding: utf-8 -*-
"""EmotionExtractor 100条回归验证 + 20条泛化性验证

验证步骤：
1. 用 100 条数据验证无大回退（目标 F1 >= 0.85）
2. 用 20 条泛化样本验证（目标准确率 >= 0.65）
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import EmotionExtractor


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate(gt_data: list, extractor: EmotionExtractor, name: str):
    from sklearn.metrics import f1_score, accuracy_score, classification_report
    
    y_true_l1 = []
    y_pred_l1 = []
    y_true_l2 = []
    y_pred_l2 = []
    
    errors = []
    
    for item in gt_data:
        text = item['text']
        gt_l1 = item['emotion_class']
        gt_l2 = item['emotion_label']
        
        result = extractor.classify(text)
        pred_l1 = result.emotion_class
        pred_l2 = result.emotion_label
        
        y_true_l1.append(gt_l1)
        y_pred_l1.append(pred_l1)
        y_true_l2.append(gt_l2)
        y_pred_l2.append(pred_l2)
        
        if gt_l1 != pred_l1 or gt_l2 != pred_l2:
            errors.append({
                'id': item['id'],
                'text': text,
                'gt': f"{gt_l1}/{gt_l2}",
                'pred': f"{pred_l1}/{pred_l2}",
                'l1_ok': gt_l1 == pred_l1,
                'l2_ok': gt_l2 == pred_l2,
            })
    
    print(f"\n{'='*70}")
    print(f"{name}")
    print(f"{'='*70}")
    print(f"数据集: {len(gt_data)} 条")
    
    print(f"\n--- L1 粗分类 ---")
    print(classification_report(y_true_l1, y_pred_l1, digits=3, zero_division=0))
    
    print(f"\n--- L2 细分类 ---")
    print(classification_report(y_true_l2, y_pred_l2, digits=3, zero_division=0))
    
    l1_acc = accuracy_score(y_true_l1, y_pred_l1)
    l2_f1 = f1_score(y_true_l2, y_pred_l2, average='macro')
    
    print(f"\n=== 汇总 ===")
    print(f"L1 准确率: {l1_acc:.3f}")
    print(f"L2 Macro F1: {l2_f1:.3f}")
    
    if errors:
        print(f"\n--- 错误案例 ({len(errors)}条) ---")
        for e in errors[:20]:
            l1_mark = '✅' if e['l1_ok'] else '❌'
            l2_mark = '✅' if e['l2_ok'] else '❌'
            print(f"{e['id']}: {e['text'][:30]:30s} GT={e['gt']:20s} Pred={e['pred']:20s} L1={l1_mark} L2={l2_mark}")
    
    return {
        'l1_acc': l1_acc,
        'l2_f1': l2_f1,
        'errors': errors,
    }


def main():
    extractor = EmotionExtractor()
    
    results = {}
    
    gt_100_path = Path(__file__).parent.parent / 'tests' / 'emotion_gt_100.json'
    if gt_100_path.exists():
        gt_100 = load_gt(gt_100_path)
        results['100条回归'] = evaluate(gt_100, extractor, "100条回归验证")
    
    gt_gen_path = Path(__file__).parent.parent / 'tests' / 'emotion_gt_generalization.json'
    if gt_gen_path.exists():
        gt_gen = load_gt(gt_gen_path)
        results['20条泛化'] = evaluate(gt_gen, extractor, "20条泛化性验证")
    
    print(f"\n{'='*70}")
    print("最终结论")
    print(f"{'='*70}")
    
    if '100条回归' in results:
        r = results['100条回归']
        status_100 = '✅ 通过' if r['l2_f1'] >= 0.85 else '❌ 未达标'
        print(f"100条回归: L2 F1 = {r['l2_f1']:.3f} {status_100} (目标 >= 0.85)")
    
    if '20条泛化' in results:
        r = results['20条泛化']
        status_gen = '✅ 通过' if r['l1_acc'] >= 0.65 else '❌ 未达标'
        print(f"20条泛化: L1 准确率 = {r['l1_acc']:.3f} {status_gen} (目标 >= 0.65)")


if __name__ == '__main__':
    main()
