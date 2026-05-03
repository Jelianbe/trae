#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
情绪标注跨小说泛化评估脚本

用途：
1. 验证情绪标注器在新小说上的泛化准确率（目标 ≥60%）
2. 输出准确率、混淆矩阵、每情绪 F1

使用方法：
    python scripts/evaluate_emotion_on_new_novel.py --gt tests/modern_30_ground_truth.json --input tests/modern_30_dialogues.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emotion_tagger import get_emotion_tagger


@dataclass
class EvaluationResult:
    total: int
    correct: int
    incorrect: int
    accuracy: float
    confusion_matrix: Dict[str, Dict[str, int]]
    per_emotion_precision: Dict[str, float]
    per_emotion_recall: Dict[str, float]
    per_emotion_f1: Dict[str, float]
    errors: List[Tuple[int, str, str, str]]  # (id, text, expected, predicted)


def load_data(gt_path: str, input_path: str) -> Tuple[List[dict], List[dict]]:
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    with open(input_path, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    return gt_data, input_data


def evaluate(
    input_data: List[dict],
    gt_data: List[dict],
) -> EvaluationResult:
    tagger = get_emotion_tagger()
    
    gt_map = {item['id']: item for item in gt_data}
    input_map = {item['id']: item for item in input_data}
    
    all_ids = sorted(set(gt_map.keys()) & set(input_map.keys()))
    
    total = len(all_ids)
    correct = 0
    incorrect = 0
    errors = []
    
    confusion_matrix = defaultdict(lambda: defaultdict(int))
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    
    for item_id in all_ids:
        text = input_map[item_id]['text']
        expected = gt_map[item_id]['emotion']
        
        predicted = tagger.tag(text)
        
        confusion_matrix[expected][predicted] += 1
        
        if predicted == expected:
            correct += 1
            tp[expected] += 1
        else:
            incorrect += 1
            fp[predicted] += 1
            fn[expected] += 1
            errors.append((item_id, text, expected, predicted))
    
    accuracy = correct / total if total > 0 else 0
    
    per_emotion_precision = {}
    per_emotion_recall = {}
    per_emotion_f1 = {}
    
    all_emotions = set()
    for e in gt_data:
        all_emotions.add(e['emotion'])
    for err in errors:
        all_emotions.add(err[2])
        all_emotions.add(err[3])
    
    for emotion in sorted(all_emotions):
        p = tp[emotion] / (tp[emotion] + fp[emotion]) if (tp[emotion] + fp[emotion]) > 0 else 0
        r = tp[emotion] / (tp[emotion] + fn[emotion]) if (tp[emotion] + fn[emotion]) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        per_emotion_precision[emotion] = p
        per_emotion_recall[emotion] = r
        per_emotion_f1[emotion] = f1
    
    return EvaluationResult(
        total=total,
        correct=correct,
        incorrect=incorrect,
        accuracy=accuracy,
        confusion_matrix=dict(confusion_matrix),
        per_emotion_precision=dict(per_emotion_precision),
        per_emotion_recall=dict(per_emotion_recall),
        per_emotion_f1=dict(per_emotion_f1),
        errors=errors,
    )


def print_results(result: EvaluationResult) -> None:
    print("\n" + "=" * 70)
    print("情绪标注跨小说泛化评估结果")
    print("=" * 70)
    
    print(f"\n总测试数: {result.total}")
    print(f"正确数: {result.correct}")
    print(f"错误数: {result.incorrect}")
    print(f"准确率: {result.accuracy:.1%}")
    
    print(f"\n目标: ≥60%")
    if result.accuracy >= 0.60:
        print("✅ 泛化可接受")
    elif result.accuracy >= 0.50:
        print("⚠️ 准确率偏低，需要从新书中重新统计关键词")
    else:
        print("❌ 准确率过低，建议使用 ML 模型替代规则")
    
    print("\n" + "-" * 50)
    print("混淆矩阵 (行=预期, 列=预测)")
    print("-" * 50)
    
    all_emotions = sorted(set(result.per_emotion_f1.keys()))
    header = "预期\\预测\t" + "\t".join(all_emotions)
    print(header)
    for expected in all_emotions:
        row = [str(result.confusion_matrix.get(expected, {}).get(predicted, 0)) for predicted in all_emotions]
        print(f"{expected}\t\t" + "\t".join(row))
    
    print("\n" + "-" * 50)
    print("每情绪 F1 分数")
    print("-" * 50)
    for emotion in all_emotions:
        f1 = result.per_emotion_f1.get(emotion, 0)
        p = result.per_emotion_precision.get(emotion, 0)
        r = result.per_emotion_recall.get(emotion, 0)
        print(f"  {emotion:<10} P={p:.2f}  R={r:.2f}  F1={f1:.2f}")
    
    if result.errors:
        print("\n" + "-" * 50)
        print("错误案例详情")
        print("-" * 50)
        for item_id, text, expected, predicted in result.errors:
            print(f"  ID {item_id}: 预期={expected}, 预测={predicted}")
            print(f"    文本: {text[:80]}")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="情绪标注跨小说泛化评估")
    parser.add_argument('--gt', required=True, help="GT标注文件路径")
    parser.add_argument('--input', required=True, help="输入对话文件路径")
    args = parser.parse_args()
    
    gt_data, input_data = load_data(args.gt, args.input)
    result = evaluate(input_data, gt_data)
    print_results(result)
    
    # 保存结果到文件
    output_path = PROJECT_ROOT / "analysis_reports" / "测试报告" / "情绪标注泛化测试报告.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": result.total,
            "correct": result.correct,
            "incorrect": result.incorrect,
            "accuracy": round(result.accuracy, 4),
            "per_emotion_f1": {k: round(v, 4) for k, v in result.per_emotion_f1.items()},
            "errors": [{"id": e[0], "text": e[1], "expected": e[2], "predicted": e[3]} for e in result.errors],
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_path}")


if __name__ == '__main__':
    main()
