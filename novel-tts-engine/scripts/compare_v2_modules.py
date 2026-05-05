# -*- coding: utf-8 -*-
"""v2 改进模块对比评估脚本

直接对比 v1（标准版）和 v2（改进版）的 *_v2.py 文件。

版本定义：
- v1: D:\trae\novel-tts-engine\pipeline\emotion_extractor.py
- v2: D:\trae\说说看法\emotion_extractor_v2.py

运行方式：
    python scripts/compare_v2_modules.py
"""

import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
V1_PIPELINE = PROJECT_ROOT / 'pipeline'
V2_DIR = Path(r'D:\trae\说说看法')
GT_PATH = PROJECT_ROOT / 'tests' / 'role_emotion_gt_100.json'


def load_v1_extractor():
    """加载 v1 情绪提取器"""
    # 保存原始 sys.path
    original_path = sys.path.copy()
    # 清除 pipeline 模块缓存
    for mod in list(sys.modules.keys()):
        if mod.startswith('pipeline'):
            del sys.modules[mod]
    
    # 插入 v1 的父目录
    sys.path.insert(0, str(V1_PIPELINE.parent))
    
    try:
        from pipeline.emotion_extractor import get_emotion_extractor
        return get_emotion_extractor()
    finally:
        sys.path = original_path


def load_v2_extractor():
    """加载 v2 情绪提取器"""
    # 保存原始 sys.path
    original_path = sys.path.copy()
    # 清除可能存在的 v2 模块缓存
    for mod in list(sys.modules.keys()):
        if mod in ('emotion_extractor_v2',):
            del sys.modules[mod]
    
    # 插入 v2 目录
    v2_dir_str = str(V2_DIR)
    if v2_dir_str not in sys.path:
        sys.path.insert(0, v2_dir_str)
    
    try:
        import emotion_extractor_v2
        return emotion_extractor_v2.get_emotion_extractor()
    finally:
        sys.path = original_path
        # 清理 v2 模块
        if 'emotion_extractor_v2' in sys.modules:
            del sys.modules['emotion_extractor_v2']


def evaluate_emotion_extractor(extractor, test_cases: list) -> dict:
    """评估情绪提取器"""
    results = []
    
    for case in test_cases:
        text = case['text']
        gt_emotion = case['emotion_label']  # 修正：使用正确的字段名
        
        try:
            result = extractor.classify(text)
            pred_emotion = result.emotion_label
            pred_class = result.emotion_class
            confidence = result.confidence
            
            results.append({
                'text': text,
                'gt_emotion': gt_emotion,
                'pred_emotion': pred_emotion,
                'pred_class': pred_class,
                'confidence': confidence,
                'correct_l2': pred_emotion == gt_emotion,
            })
        except Exception as e:
            results.append({
                'text': text,
                'gt_emotion': gt_emotion,
                'pred_emotion': 'error',
                'pred_class': 'error',
                'confidence': 0.0,
                'correct_l2': False,
                'error': str(e),
            })
    
    total = len(results)
    correct_l2 = sum(1 for r in results if r['correct_l2'])
    
    # 按情绪统计
    by_emotion = defaultdict(lambda: {'total': 0, 'correct': 0})
    for r in results:
        gt = r['gt_emotion']
        by_emotion[gt]['total'] += 1
        if r['correct_l2']:
            by_emotion[gt]['correct'] += 1
    
    # 混淆矩阵
    confusion = defaultdict(lambda: defaultdict(int))
    for r in results:
        confusion[r['gt_emotion']][r['pred_emotion']] += 1
    
    # 按文体统计
    by_style = defaultdict(lambda: {'total': 0, 'correct': 0})
    for i, r in enumerate(results):
        style = test_cases[i].get('style', '未知')
        by_style[style]['total'] += 1
        if r['correct_l2']:
            by_style[style]['correct'] += 1
    
    return {
        'total': total,
        'correct_l2': correct_l2,
        'accuracy_l2': correct_l2 / total if total > 0 else 0,
        'by_emotion': {k: dict(v) for k, v in by_emotion.items()},
        'by_style': {k: dict(v) for k, v in by_style.items()},
        'confusion': {k: dict(v) for k, v in confusion.items()},
        'results': results,
    }


def map_l2_to_l1(emotion: str) -> str:
    """L2 → L1 映射"""
    if emotion in ('joy', 'anger', 'surprise'):
        return 'excited'
    elif emotion in ('sadness', 'fear'):
        return 'subdued'
    else:
        return 'neutral'


def evaluate_l1(eval_result: dict) -> float:
    """计算 L1 准确率"""
    correct = 0
    for r in eval_result['results']:
        gt_l1 = map_l2_to_l1(r['gt_emotion'])
        pred_l1 = r['pred_class']
        if gt_l1 == pred_l1:
            correct += 1
    return correct / eval_result['total'] if eval_result['total'] > 0 else 0


def print_comparison_report(v1_result: dict, v2_result: dict, test_cases: list):
    """打印对比报告"""
    v1_acc = v1_result['accuracy_l2']
    v2_acc = v2_result['accuracy_l2']
    v1_l1 = evaluate_l1(v1_result)
    v2_l1 = evaluate_l1(v2_result)
    
    print(f"\n{'='*80}")
    print(f"情绪提取器对比评估报告")
    print(f"{'='*80}")
    print(f"\n指标                           v1（标准版）        v2（改进版）        变化")
    print(f"{'-'*80}")
    print(f"测试样本数                        {v1_result['total']:<16} {v2_result['total']:<16}")
    print(f"情绪标注准确率 L2（6类）           {v1_acc:.1%}              {v2_acc:.1%}              {'+' if v2_acc>v1_acc else ''}{v2_acc-v1_acc:+.1%}")
    print(f"情绪标注准确率 L1（3类）           {v1_l1:.1%}              {v2_l1:.1%}              {'+' if v2_l1>v1_l1 else ''}{v2_l1-v1_l1:+.1%}")
    
    # 按情绪统计
    print(f"\n按 GT 情绪分类统计")
    print(f"{'-'*80}")
    print(f"{'GT 情绪':<12} {'v1 正确/总数':<18} {'v1 准确率':<12} {'v2 正确/总数':<18} {'v2 准确率':<12} {'差异':<10}")
    print(f"{'-'*80}")
    
    all_emotions = sorted(set(list(v1_result['by_emotion'].keys()) + list(v2_result['by_emotion'].keys())))
    
    for emotion in all_emotions:
        v1_e = v1_result['by_emotion'].get(emotion, {})
        v2_e = v2_result['by_emotion'].get(emotion, {})
        
        v1_total = v1_e.get('total', 0)
        v1_correct = v1_e.get('correct', 0)
        v1_acc_e = v1_correct / v1_total if v1_total > 0 else 0
        
        v2_total = v2_e.get('total', 0)
        v2_correct = v2_e.get('correct', 0)
        v2_acc_e = v2_correct / v2_total if v2_total > 0 else 0
        
        diff = v2_acc_e - v1_acc_e
        
        print(f"{emotion:<12} {v1_correct}/{v1_total:<14} {v1_acc_e:<12.1%} {v2_correct}/{v2_total:<14} {v2_acc_e:<12.1%} {'+' if diff>0 else ''}{diff:+.1%}")
    
    # 按文体统计
    print(f"\n按文体统计")
    print(f"{'-'*80}")
    print(f"{'文体':<8} {'v1 正确/总数':<18} {'v1 准确率':<12} {'v2 正确/总数':<18} {'v2 准确率':<12} {'差异':<10}")
    print(f"{'-'*80}")
    
    all_styles = sorted(set(list(v1_result['by_style'].keys()) + list(v2_result['by_style'].keys())))
    
    for style in all_styles:
        v1_s = v1_result['by_style'].get(style, {})
        v2_s = v2_result['by_style'].get(style, {})
        
        v1_total = v1_s.get('total', 0)
        v1_correct = v1_s.get('correct', 0)
        v1_acc_s = v1_correct / v1_total if v1_total > 0 else 0
        
        v2_total = v2_s.get('total', 0)
        v2_correct = v2_s.get('correct', 0)
        v2_acc_s = v2_correct / v2_total if v2_total > 0 else 0
        
        diff = v2_acc_s - v1_acc_s
        
        print(f"{style:<8} {v1_correct}/{v1_total:<14} {v1_acc_s:<12.1%} {v2_correct}/{v2_total:<14} {v2_acc_s:<12.1%} {'+' if diff>0 else ''}{diff:+.1%}")
    
    # 混淆矩阵
    emotions_order = ['anger', 'fear', 'joy', 'neutral', 'sadness', 'surprise']
    
    print(f"\n情绪混淆矩阵 (v1)")
    print(f"{'-'*60}")
    header = f"{'GT/Pred':<10}" + ''.join([f"{e[:8]:<8}" for e in emotions_order])
    print(header)
    print(f"{'-'*60}")
    
    for gt_e in emotions_order:
        row = f"{gt_e:<10}"
        for pred_e in emotions_order:
            count = v1_result['confusion'].get(gt_e, {}).get(pred_e, 0)
            row += f"{count:<8}"
        print(row)
    
    print(f"\n情绪混淆矩阵 (v2)")
    print(f"{'-'*60}")
    header = f"{'GT/Pred':<10}" + ''.join([f"{e[:8]:<8}" for e in emotions_order])
    print(header)
    print(f"{'-'*60}")
    
    for gt_e in emotions_order:
        row = f"{gt_e:<10}"
        for pred_e in emotions_order:
            count = v2_result['confusion'].get(gt_e, {}).get(pred_e, 0)
            row += f"{count:<8}"
        print(row)
    
    # 改进/回归分析
    v1_wrong = {r['text']: r for r in v1_result['results'] if not r['correct_l2']}
    v2_wrong = {r['text']: r for r in v2_result['results'] if not r['correct_l2']}
    
    v1_only_wrong = set(v1_wrong.keys()) - set(v2_wrong.keys())
    v2_only_wrong = set(v2_wrong.keys()) - set(v1_wrong.keys())
    
    print(f"\n改进与回归分析")
    print(f"{'-'*80}")
    print(f"v1 错误数: {len(v1_wrong)}")
    print(f"v2 错误数: {len(v2_wrong)}")
    print(f"v2 修复的案例（v1 独有错误）: {len(v1_only_wrong)}")
    print(f"v2 新引入的错误（回归）: {len(v2_only_wrong)}")
    
    if v1_only_wrong:
        print(f"\n✅ v2 修复的案例（前 10 个）:")
        for i, text in enumerate(list(v1_only_wrong)[:10]):
            r1 = v1_wrong[text]
            idx = None
            for j, r in enumerate(v2_result['results']):
                if r['text'] == text:
                    idx = j
                    break
            if idx is not None:
                r2 = v2_result['results'][idx]
                text_short = text[:50] + '...' if len(text) > 50 else text
                print(f"  {i+1}. GT: {r1['gt_emotion']}, v1: {r1['pred_emotion']}, v2: {r2['pred_emotion']}")
                print(f"     {text_short}")
    
    if v2_only_wrong:
        print(f"\n⚠️ v2 新引入的错误（前 10 个）:")
        for i, text in enumerate(list(v2_only_wrong)[:10]):
            idx = None
            for j, r in enumerate(v1_result['results']):
                if r['text'] == text:
                    idx = j
                    break
            if idx is not None:
                r1 = v1_result['results'][idx]
                r2 = v2_wrong[text]
                text_short = text[:50] + '...' if len(text) > 50 else text
                print(f"  {i+1}. GT: {r1['gt_emotion']}, v1: {r1['pred_emotion']}, v2: {r2['pred_emotion']}")
                print(f"     {text_short}")


def main():
    print("="*80)
    print("v2 改进模块对比评估脚本")
    print("="*80)
    print(f"\nv1（标准版）: {V1_PIPELINE}/emotion_extractor.py")
    print(f"v2（改进版）: {V2_DIR}/emotion_extractor_v2.py")
    print(f"测试集: {GT_PATH}")
    
    # 加载测试集
    with open(GT_PATH, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    
    print(f"\n加载测试集: {len(test_cases)} 条")
    
    # 加载 v1
    print(f"\n加载 v1 情绪提取器...")
    extractor_v1 = load_v1_extractor()
    print(f"  ✅ v1 加载成功")
    
    # 加载 v2
    print(f"加载 v2 情绪提取器...")
    extractor_v2 = load_v2_extractor()
    print(f"  ✅ v2 加载成功")
    
    # 评估 v1
    print(f"\n评估 v1...")
    t0 = time.time()
    v1_result = evaluate_emotion_extractor(extractor_v1, test_cases)
    t1 = time.time()
    print(f"  ✅ v1 评估完成: L2 准确率 = {v1_result['accuracy_l2']:.1%}, 耗时 {t1-t0:.1f}s")
    
    # 评估 v2
    print(f"评估 v2...")
    t2 = time.time()
    v2_result = evaluate_emotion_extractor(extractor_v2, test_cases)
    t3 = time.time()
    print(f"  ✅ v2 评估完成: L2 准确率 = {v2_result['accuracy_l2']:.1%}, 耗时 {t3-t2:.1f}s")
    
    # 打印对比报告
    print_comparison_report(v1_result, v2_result, test_cases)
    
    # 导出 JSON 报告
    report = {
        'v1': {
            'total': v1_result['total'],
            'accuracy_l2': v1_result['accuracy_l2'],
            'accuracy_l1': evaluate_l1(v1_result),
            'by_emotion': v1_result['by_emotion'],
            'by_style': v1_result['by_style'],
            'confusion': v1_result['confusion'],
        },
        'v2': {
            'total': v2_result['total'],
            'accuracy_l2': v2_result['accuracy_l2'],
            'accuracy_l1': evaluate_l1(v2_result),
            'by_emotion': v2_result['by_emotion'],
            'by_style': v2_result['by_style'],
            'confusion': v2_result['confusion'],
        },
    }
    
    report_dir = PROJECT_ROOT / 'analysis_reports' / '优化报告'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = report_dir / 'v2改进模块对比评估报告_20260505.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nJSON 报告已导出: {report_path}")


if __name__ == '__main__':
    main()
