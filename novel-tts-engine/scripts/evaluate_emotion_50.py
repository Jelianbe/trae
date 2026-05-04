# -*- coding: utf-8 -*-
"""EmotionExtractor 三层标注体系验证脚本

验证目标：
- L1 粗分类准确率 >= 0.90
- L2 细分类 Macro F1 >= 0.85

数据集：50条人工标注对话（都市16 + 西幻9 + 修仙12 + 历史8）
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict
from pipeline.emotion_extractor import get_emotion_extractor, EmotionResult


def load_gt_data(filepath: str) -> list:
    """加载GT数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def calc_accuracy(predictions: list, ground_truth: list) -> float:
    """计算准确率"""
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(ground_truth) if ground_truth else 0.0


def calc_f1(predictions: list, ground_truth: list, labels: list) -> dict:
    """计算每个类别的 F1 和 Macro F1"""
    f1s = {}
    for label in labels:
        tp = sum(1 for p, g in zip(predictions, ground_truth) if p == label and g == label)
        fp = sum(1 for p, g in zip(predictions, ground_truth) if p == label and g != label)
        fn = sum(1 for p, g in zip(predictions, ground_truth) if p != label and g == label)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        f1s[label] = round(f1, 3)
    
    macro_f1 = sum(f1s.values()) / len(f1s)
    return f1s, round(macro_f1, 3)


def main():
    # 加载GT数据
    gt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'emotion_gt_50.json')
    gt_data = load_gt_data(gt_path)
    
    print("=" * 70)
    print("EmotionExtractor 三层标注体系验证")
    print("=" * 70)
    print(f"数据集: {len(gt_data)} 条")
    print(f"文体分布: 都市{sum(1 for d in gt_data if d['style'] == '都市')} + "
          f"西幻{sum(1 for d in gt_data if d['style'] == '西幻')} + "
          f"修仙{sum(1 for d in gt_data if d['style'] == '修仙')} + "
          f"历史{sum(1 for d in gt_data if d['style'] == '历史')}")
    print()
    
    # 初始化提取器
    extractor = get_emotion_extractor()
    
    # 收集预测结果
    pred_l1 = []  # emotion_class
    pred_l2 = []  # emotion_label
    gt_l1 = []
    gt_l2 = []
    
    # 按情绪类别统计
    results_by_emotion = defaultdict(list)
    
    for item in gt_data:
        text = item['text']
        gt_class = item['emotion_class']
        gt_label = item['emotion_label']
        
        # 预测
        result = extractor.classify(text)
        
        pred_l1.append(result.emotion_class)
        pred_l2.append(result.emotion_label)
        gt_l1.append(gt_class)
        gt_l2.append(gt_label)
        
        # 记录详细结果
        results_by_emotion[gt_label].append({
            'id': item['id'],
            'text': text,
            'gt_class': gt_class,
            'pred_class': result.emotion_class,
            'gt_label': gt_label,
            'pred_label': result.emotion_label,
            'correct_l1': result.emotion_class == gt_class,
            'correct_l2': result.emotion_label == gt_label,
            'confidence': result.confidence,
            'intensity': result.intensity,
        })
    
    # === L1 粗分类评估 ===
    print("=" * 70)
    print("L1 粗分类评估 (neutral / excited / subdued)")
    print("=" * 70)
    
    l1_labels = ['neutral', 'excited', 'subdued']
    l1_f1s, l1_macro_f1 = calc_f1(pred_l1, gt_l1, l1_labels)
    l1_accuracy = calc_accuracy(pred_l1, gt_l1)
    
    print(f"{'类别':<12} {'F1':>8}")
    print("-" * 25)
    for label in l1_labels:
        print(f"{label:<12} {l1_f1s[label]:>8.3f}")
    print("-" * 25)
    print(f"{'Macro F1':<12} {l1_macro_f1:>8.3f}")
    print(f"{'准确率':<12} {l1_accuracy:>8.3f}")
    print()
    
    # === L2 细分类评估 ===
    print("=" * 70)
    print("L2 细分类评估 (joy / anger / sadness / surprise / fear / neutral)")
    print("=" * 70)
    
    l2_labels = ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral']
    l2_f1s, l2_macro_f1 = calc_f1(pred_l2, gt_l2, l2_labels)
    l2_accuracy = calc_accuracy(pred_l2, gt_l2)
    
    print(f"{'类别':<12} {'F1':>8} {'GT数量':>8}")
    print("-" * 35)
    for label in l2_labels:
        gt_count = sum(1 for g in gt_l2 if g == label)
        print(f"{label:<12} {l2_f1s[label]:>8.3f} {gt_count:>8}")
    print("-" * 35)
    print(f"{'Macro F1':<12} {l2_macro_f1:>8.3f}")
    print(f"{'准确率':<12} {l2_accuracy:>8.3f}")
    print()
    
    # === 验证结果 ===
    print("=" * 70)
    print("验证结果")
    print("=" * 70)
    
    l1_pass = l1_accuracy >= 0.90
    l2_pass = l2_macro_f1 >= 0.85
    
    print(f"L1 准确率: {l1_accuracy:.3f} {'✅ 通过' if l1_pass else '❌ 未达标准 (目标 >= 0.90)'}")
    print(f"L2 Macro F1: {l2_macro_f1:.3f} {'✅ 通过' if l2_pass else '❌ 未达标准 (目标 >= 0.85)'}")
    print()
    
    # === 逐条对比（错误case） ===
    print("=" * 70)
    print("错误case分析")
    print("=" * 70)
    
    errors = []
    for item in gt_data:
        text = item['text']
        gt_class = item['emotion_class']
        gt_label = item['emotion_label']
        result = extractor.classify(text)
        
        if result.emotion_label != gt_label or result.emotion_class != gt_class:
            errors.append({
                'id': item['id'],
                'text': text[:30],
                'gt': f"{gt_class}/{gt_label}",
                'pred': f"{result.emotion_class}/{result.emotion_label}",
                'l1_ok': result.emotion_class == gt_class,
                'l2_ok': result.emotion_label == gt_label,
            })
    
    if errors:
        print(f"共 {len(errors)} 条错误：")
        print(f"{'ID':<10} {'对话':<30} {'GT':<20} {'预测':<20} {'L1':<4} {'L2':<4}")
        print("-" * 90)
        for e in errors:
            print(f"{e['id']:<10} {e['text']:<30} {e['gt']:<20} {e['pred']:<20} "
                  f"{'✅' if e['l1_ok'] else '❌':<4} {'✅' if e['l2_ok'] else '❌':<4}")
    else:
        print("全部正确！")
    
    print()
    
    # === 按文体统计 ===
    print("=" * 70)
    print("按文体统计")
    print("=" * 70)
    
    styles = ['都市', '西幻', '修仙', '历史']
    for style in styles:
        style_items = [item for item in gt_data if item['style'] == style]
        if not style_items:
            continue
        
        style_pred_l2 = []
        style_gt_l2 = []
        for item in style_items:
            result = extractor.classify(item['text'])
            style_pred_l2.append(result.emotion_label)
            style_gt_l2.append(item['emotion_label'])
        
        style_acc = calc_accuracy(style_pred_l2, style_gt_l2)
        print(f"{style}: L2准确率 = {style_acc:.3f} ({sum(1 for p, g in zip(style_pred_l2, style_gt_l2) if p == g)}/{len(style_items)})")


if __name__ == "__main__":
    main()
