# -*- coding: utf-8 -*-
"""双层标注评估脚本（角色 + 情绪）

评估目标：
1. 角色识别准确率（speaker）
2. 情绪标注准确率（emotion_label）
3. 按文体、挑战类型统计
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import EmotionExtractor


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate_emotion(gt_data: list, extractor: EmotionExtractor):
    """评估情绪标注"""
    
    results = {
        'total': len(gt_data),
        'correct': 0,
        'errors': [],
        'by_style': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'by_challenge': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'by_emotion': defaultdict(lambda: {'correct': 0, 'total': 0, 'pred': defaultdict(int)}),
        'confusion': defaultdict(lambda: defaultdict(int)),
    }
    
    for item in gt_data:
        text = item['text']
        gt_emotion = item['emotion_label']
        style = item['style']
        challenge = item.get('emotion_challenge', 'unknown')
        
        # 预测情绪
        result = extractor.classify(text)
        pred_emotion = result.emotion_label
        
        # 统计
        results['by_style'][style]['total'] += 1
        results['by_challenge'][challenge]['total'] += 1
        results['by_emotion'][gt_emotion]['total'] += 1
        results['by_emotion'][gt_emotion]['pred'][pred_emotion] += 1
        
        if gt_emotion == pred_emotion:
            results['correct'] += 1
            results['by_style'][style]['correct'] += 1
            results['by_challenge'][challenge]['correct'] += 1
            results['by_emotion'][gt_emotion]['correct'] += 1
        else:
            results['errors'].append({
                'id': item['id'],
                'text': text[:50],
                'gt': gt_emotion,
                'pred': pred_emotion,
                'style': style,
                'challenge': challenge[:30] + '...' if len(challenge) > 30 else challenge,
            })
            results['confusion'][gt_emotion][pred_emotion] += 1
    
    return results


def print_report(emotion_results: dict):
    """打印评估报告"""
    
    print("=" * 80)
    print("双层标注评估报告")
    print("=" * 80)
    
    # 总体结果
    total = emotion_results['total']
    correct = emotion_results['correct']
    accuracy = correct / total if total > 0 else 0
    
    print(f"\n=== 情绪标注总体结果 ===")
    print(f"总数: {total}")
    print(f"正确: {correct}")
    print(f"准确率: {accuracy:.1%}")
    
    # 按文体统计
    print(f"\n=== 按文体统计 ===")
    print(f"{'文体':<10} {'正确':<8} {'总数':<8} {'准确率':<10}")
    print("-" * 40)
    for style, stats in sorted(emotion_results['by_style'].items()):
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"{style:<10} {stats['correct']:<8} {stats['total']:<8} {acc:.1%}")
    
    # 按情绪类别统计
    print(f"\n=== 按情绪类别统计 ===")
    print(f"{'情绪':<10} {'正确':<8} {'总数':<8} {'准确率':<10} {'主要误判'}")
    print("-" * 60)
    for emotion, stats in sorted(emotion_results['by_emotion'].items()):
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        # 找出主要误判
        wrong_preds = [(p, c) for p, c in stats['pred'].items() if p != emotion]
        wrong_preds.sort(key=lambda x: -x[1])
        main_wrong = wrong_preds[0] if wrong_preds else (None, 0)
        wrong_info = f"→{main_wrong[0]}({main_wrong[1]})" if main_wrong[0] else "-"
        print(f"{emotion:<10} {stats['correct']:<8} {stats['total']:<8} {acc:.1%}      {wrong_info}")
    
    # 按挑战类型统计
    print(f"\n=== 按挑战类型统计 ===")
    challenges = sorted(emotion_results['by_challenge'].items(), key=lambda x: x[1]['total'], reverse=True)
    for challenge, stats in challenges[:10]:
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        challenge_short = challenge[:40] + '...' if len(challenge) > 40 else challenge
        print(f"{challenge_short:<45} {stats['correct']:>3}/{stats['total']:<3} {acc:.1%}")
    
    # 错误案例
    if emotion_results['errors']:
        print(f"\n=== 错误案例（前20条）===")
        for e in emotion_results['errors'][:20]:
            print(f"{e['id']}: {e['text'][:30]:30s} GT={e['gt']:10s} Pred={e['pred']:10s}")
    
    # 混淆矩阵
    print(f"\n=== 混淆矩阵 ===")
    emotions = ['neutral', 'joy', 'anger', 'sadness', 'surprise', 'fear']
    header = "GT\\Pred"
    print(f"{header:<10}", end='')
    for e in emotions:
        print(f"{e[:6]:<8}", end='')
    print()
    for gt_e in emotions:
        print(f"{gt_e[:8]:<10}", end='')
        for pred_e in emotions:
            count = emotion_results['confusion'][gt_e][pred_e]
            print(f"{count:<8}", end='')
        print()


def main():
    gt_path = Path(__file__).parent.parent / 'tests' / 'role_emotion_gt_50.json'
    if not gt_path.exists():
        print(f"错误: 测试数据不存在 - {gt_path}")
        return
    
    gt_data = load_gt(gt_path)
    print(f"加载测试数据: {len(gt_data)} 条")
    
    extractor = EmotionExtractor()
    
    # 评估情绪标注
    emotion_results = evaluate_emotion(gt_data, extractor)
    
    # 打印报告
    print_report(emotion_results)
    
    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    
    total_acc = emotion_results['correct'] / emotion_results['total']
    
    print(f"情绪标注准确率: {total_acc:.1%}")
    
    # 按文体
    print("\n按文体:")
    for style, stats in sorted(emotion_results['by_style'].items()):
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        status = "✅" if acc >= 0.7 else "⚠️" if acc >= 0.5 else "❌"
        print(f"  {style}: {acc:.1%} {status}")
    
    # 挑战类型分析
    print("\n挑战类型分析:")
    simple_correct = 0
    simple_total = 0
    context_correct = 0
    context_total = 0
    
    for challenge, stats in emotion_results['by_challenge'].items():
        if '明确' in challenge or '简单' in challenge or '信号明确' in challenge:
            simple_correct += stats['correct']
            simple_total += stats['total']
        elif '上下文' in challenge or '依赖' in challenge:
            context_correct += stats['correct']
            context_total += stats['total']
    
    if simple_total > 0:
        print(f"  简单情绪（明确信号）: {simple_correct}/{simple_total} = {simple_correct/simple_total:.1%}")
    if context_total > 0:
        print(f"  上下文依赖: {context_correct}/{context_total} = {context_correct/context_total:.1%}")


if __name__ == '__main__':
    main()
