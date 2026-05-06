# -*- coding: utf-8 -*-
"""
情绪提取器测试网关
纯净验证脚本：不参与开发，仅用于回归测试
每次修改 emotion_extractor.py 后运行此脚本
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.emotion_extractor import EmotionExtractor


def run_gate():
    ext = EmotionExtractor()
    
    with open('tests/emotion_gt_100.json', 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    
    correct = 0
    neutral_count = 0
    errors = []
    
    for item in gt_data:
        r = ext.classify(item['text'])
        if r.emotion_label == item['emotion_label']:
            correct += 1
        if r.emotion_label == 'neutral':
            neutral_count += 1
        if r.emotion_label != item['emotion_label']:
            errors.append({
                'id': item['id'],
                'text': item['text'][:30],
                'gt': item['emotion_label'],
                'pred': r.emotion_label
            })
    
    # 脏词边界测试 - 用 GT 中的 neutral 样本验证
    dirty_fp = 0  # 误报
    for item in gt_data:
        if item['emotion_label'] == 'neutral':
            feat = ext.extract_features(item['text'])
            if feat.has_dirty_words:
                dirty_fp += 1
                print(f"  [WARN] 误报: {item['id']}: {item['text'][:30]}")
    
    # 打印结果
    print("=" * 60)
    print(" 情绪提取器测试网关")
    print("=" * 60)
    print()
    print(" 100 GT 测试集")
    print(f"  L2 准确率: {correct/100:.3f}  (基线: 0.290)")
    print(f"  Neutral 预测比例: {neutral_count/100:.3f}  (目标: <0.50)")
    print(f"  错误案例数: {len(errors)}")
    print()
    print(" 脏词边界测试")
    print(f"  误报数: {dirty_fp}  (目标: 0)")
    print()
    
    # 准出判断
    passed = True
    checks = [
        (correct/100 >= 0.29, f"L2 准确率 {correct/100:.3f} >= 0.290"),
        (dirty_fp == 0, f"脏词误报 {dirty_fp} == 0"),
    ]
    
    print(" 准出标准检查")
    for ok, desc in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            passed = False
        print(f"  [{status}] {desc}")
    print()
    
    if passed:
        print(" >>> 全部通过")
    else:
        print(" >>> 有未通过项，请检查修改")
    
    if errors:
        print()
        print(" --- Top 5 错误案例 ---")
        for e in errors[:5]:
            print(f"  {e['id']}: GT={e['gt']:15s} Pred={e['pred']:15s} | {e['text']}")
    
    print()
    print("=" * 60)
    return passed


if __name__ == '__main__':
    success = run_gate()
    sys.exit(0 if success else 1)
