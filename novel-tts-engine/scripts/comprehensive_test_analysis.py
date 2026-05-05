# -*- coding: utf-8 -*-
"""
v1 vs v2 全面测试分析脚本

测试范围：
1. 双重测试文本（100条 GT + 198条 v2 自建）
2. v2 自建测试集专项分析
3. 4 部本地小说文本对比
4. "武断性"问题专项评估

运行方式：
    python scripts/comprehensive_test_analysis.py
"""

import json
import sys
import time
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
V1_PIPELINE = PROJECT_ROOT / 'pipeline'
V2_DIR = Path(r'D:\trae\说说看法')
GT_PATH = PROJECT_ROOT / 'tests' / 'role_emotion_gt_100.json'

NOVEL_FILES = [
    ('都市', PROJECT_ROOT / 'tests' / 'test_novel_urban.txt'),
    ('西幻', PROJECT_ROOT / 'tests' / 'test_novel_western.txt'),
    ('修仙', PROJECT_ROOT / 'tests' / 'test_novel_doupo_ch1-10.txt'),
    ('悬疑', PROJECT_ROOT / 'tests' / 'test_novel_guimi_ch1-10.txt'),
]


def load_v1_extractor():
    """加载 v1 情绪提取器"""
    original_path = sys.path.copy()
    for mod in list(sys.modules.keys()):
        if mod.startswith('pipeline'):
            del sys.modules[mod]
    
    sys.path.insert(0, str(V1_PIPELINE.parent))
    
    try:
        from pipeline.emotion_extractor import get_emotion_extractor
        return get_emotion_extractor()
    finally:
        sys.path = original_path


def load_v2_extractor():
    """加载 v2 情绪提取器"""
    original_path = sys.path.copy()
    for mod in list(sys.modules.keys()):
        if mod in ('emotion_extractor_v2',):
            del sys.modules[mod]
    
    v2_dir_str = str(V2_DIR)
    if v2_dir_str not in sys.path:
        sys.path.insert(0, v2_dir_str)
    
    try:
        import emotion_extractor_v2
        return emotion_extractor_v2.get_emotion_extractor()
    finally:
        sys.path = original_path
        if 'emotion_extractor_v2' in sys.modules:
            del sys.modules['emotion_extractor_v2']


def evaluate_on_test_cases(extractor, test_cases: list) -> dict:
    """评估测试用例"""
    results = []
    
    for case in test_cases:
        text = case['text']
        gt_emotion = case.get('emotion', case.get('emotion_label'))
        
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
                'genre': case.get('genre', 'unknown'),
                'difficulty': case.get('difficulty', 'unknown'),
                'correct_l2': pred_emotion == gt_emotion,
            })
        except Exception as e:
            results.append({
                'text': text,
                'gt_emotion': gt_emotion,
                'pred_emotion': 'error',
                'pred_class': 'error',
                'confidence': 0.0,
                'genre': case.get('genre', 'unknown'),
                'difficulty': case.get('difficulty', 'unknown'),
                'correct_l2': False,
                'error': str(e),
            })
    
    total = len(results)
    correct_l2 = sum(1 for r in results if r['correct_l2'])
    
    by_emotion = defaultdict(lambda: {'total': 0, 'correct': 0})
    for r in results:
        gt = r['gt_emotion']
        by_emotion[gt]['total'] += 1
        if r['correct_l2']:
            by_emotion[gt]['correct'] += 1
    
    by_genre = defaultdict(lambda: {'total': 0, 'correct': 0})
    for r in results:
        genre = r['genre']
        by_genre[genre]['total'] += 1
        if r['correct_l2']:
            by_genre[genre]['correct'] += 1
    
    by_difficulty = defaultdict(lambda: {'total': 0, 'correct': 0})
    for r in results:
        diff = r['difficulty']
        by_difficulty[diff]['total'] += 1
        if r['correct_l2']:
            by_difficulty[diff]['correct'] += 1
    
    confusion = defaultdict(lambda: defaultdict(int))
    for r in results:
        confusion[r['gt_emotion']][r['pred_emotion']] += 1
    
    return {
        'total': total,
        'correct_l2': correct_l2,
        'accuracy_l2': correct_l2 / total if total > 0 else 0,
        'by_emotion': {k: dict(v) for k, v in by_emotion.items()},
        'by_genre': {k: dict(v) for k, v in by_genre.items()},
        'by_difficulty': {k: dict(v) for k, v in by_difficulty.items()},
        'confusion': {k: dict(v) for k, v in confusion.items()},
        'results': results,
    }


def evaluate_on_novel(extractor, text: str, max_sentences: int = 200) -> dict:
    """评估小说文本"""
    sentences = re.split(r'[。！？!?…]+', text)
    sentences = [s.strip() for s in sentences if s.strip()][:max_sentences]
    
    results = []
    for s in sentences:
        try:
            result = extractor.classify(s)
            results.append({
                'text': s,
                'emotion': result.emotion_label,
                'class': result.emotion_class,
                'confidence': result.confidence,
            })
        except Exception:
            pass
    
    total = len(results)
    by_emotion = defaultdict(int)
    for r in results:
        by_emotion[r['emotion']] += 1
    
    by_class = defaultdict(int)
    for r in results:
        by_class[r['class']] += 1
    
    return {
        'total': total,
        'by_emotion': dict(by_emotion),
        'by_class': dict(by_class),
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


def evaluate_arbitrariness(v1_result: dict, v2_result: dict) -> dict:
    """评估武断性问题
    
    武断性表现：
    1. 高置信度但预测错误（过度自信）
    2. 明显有情绪信号却预测为 neutral（情绪麻木）
    3. 相似文本预测结果不一致（不一致性）
    """
    metrics = {
        'overconfidence': {'v1': 0, 'v2': 0, 'cases_v1': [], 'cases_v2': []},
        'emotion_blindness': {'v1': 0, 'v2': 0, 'cases_v1': [], 'cases_v2': []},
        'inconsistency': {'count': 0, 'pairs': []},
    }
    
    # 1. 过度自信：高置信度但预测错误
    for r in v1_result['results']:
        if r['confidence'] >= 0.6 and not r['correct_l2']:
            metrics['overconfidence']['v1'] += 1
            if len(metrics['overconfidence']['cases_v1']) < 5:
                metrics['overconfidence']['cases_v1'].append(r)
    
    for r in v2_result['results']:
        if r['confidence'] >= 0.6 and not r['correct_l2']:
            metrics['overconfidence']['v2'] += 1
            if len(metrics['overconfidence']['cases_v2']) < 5:
                metrics['overconfidence']['cases_v2'].append(r)
    
    # 2. 情绪麻木：GT 有明确情绪但预测为 neutral
    for r in v1_result['results']:
        if r['gt_emotion'] != 'neutral' and r['pred_emotion'] == 'neutral':
            metrics['emotion_blindness']['v1'] += 1
            if len(metrics['emotion_blindness']['cases_v1']) < 5:
                metrics['emotion_blindness']['cases_v1'].append(r)
    
    for r in v2_result['results']:
        if r['gt_emotion'] != 'neutral' and r['pred_emotion'] == 'neutral':
            metrics['emotion_blindness']['v2'] += 1
            if len(metrics['emotion_blindness']['cases_v2']) < 5:
                metrics['emotion_blindness']['cases_v2'].append(r)
    
    # 3. 不一致性：相同/相似文本在不同版本中预测不同
    v1_map = {r['text']: r for r in v1_result['results']}
    v2_map = {r['text']: r for r in v2_result['results']}
    
    for text in v1_map:
        if text in v2_map:
            r1 = v1_map[text]
            r2 = v2_map[text]
            if r1['pred_emotion'] != r2['pred_emotion']:
                metrics['inconsistency']['count'] += 1
                if len(metrics['inconsistency']['pairs']) < 10:
                    metrics['inconsistency']['pairs'].append({
                        'text': text[:80],
                        'v1': r1['pred_emotion'],
                        'v2': r2['pred_emotion'],
                        'gt': r1['gt_emotion'],
                    })
    
    return metrics


def main():
    print("="*80)
    print("v1 vs v2 全面测试分析")
    print("="*80)
    
    # 加载提取器
    print(f"\n加载 v1 情绪提取器...")
    extractor_v1 = load_v1_extractor()
    print(f"  ✅ v1 加载成功")
    
    print(f"加载 v2 情绪提取器...")
    extractor_v2 = load_v2_extractor()
    print(f"  ✅ v2 加载成功")
    
    # ========== 第一部分：双重测试文本 ==========
    print(f"\n{'='*60}")
    print(f"第一部分：双重测试文本全面测试")
    print(f"{'='*60}")
    
    # 100 条 GT
    print(f"\n加载 100 条 GT 测试集...")
    with open(GT_PATH, 'r', encoding='utf-8') as f:
        gt_100 = json.load(f)
    print(f"  ✅ {len(gt_100)} 条")
    
    # 198 条 v2 自建
    print(f"加载 198 条 v2 自建测试集...")
    v2_test_path = V2_DIR / 'test_emotion_200.py'
    original_path = sys.path.copy()
    if str(V2_DIR) not in sys.path:
        sys.path.insert(0, str(V2_DIR))
    
    def build_test_text(case):
        context = case.get('context_before', '')
        text = case['text']
        return context + text if context else text
    
    try:
        from test_emotion_200 import TEST_SET as v2_198
    finally:
        sys.path = original_path
        if 'test_emotion_200' in sys.modules:
            del sys.modules['test_emotion_200']
    
    v2_198_full = []
    for case in v2_198:
        v2_198_full.append({
            'text': build_test_text(case),
            'emotion': case['emotion'],
            'genre': case.get('genre', 'unknown'),
            'difficulty': case.get('difficulty', 'unknown'),
        })
    
    print(f"  ✅ {len(v2_198_full)} 条")
    
    # 评估
    all_results = {}
    
    print(f"\n评估 100 条 GT...")
    gt_v1 = evaluate_on_test_cases(extractor_v1, gt_100)
    gt_v2 = evaluate_on_test_cases(extractor_v2, gt_100)
    all_results['gt_100'] = {'v1': gt_v1, 'v2': gt_v2}
    print(f"  v1 L2: {gt_v1['accuracy_l2']:.1%}, v2 L2: {gt_v2['accuracy_l2']:.1%}")
    
    print(f"评估 198 条 v2 自建...")
    v198_v1 = evaluate_on_test_cases(extractor_v1, v2_198_full)
    v198_v2 = evaluate_on_test_cases(extractor_v2, v2_198_full)
    all_results['v2_198'] = {'v1': v198_v1, 'v2': v198_v2}
    print(f"  v1 L2: {v198_v1['accuracy_l2']:.1%}, v2 L2: {v198_v2['accuracy_l2']:.1%}")
    
    # ========== 第二部分：v2 自建测试集专项 ==========
    print(f"\n{'='*60}")
    print(f"第二部分：v2 自建测试集专项分析")
    print(f"{'='*60}")
    
    # 按文体分析
    print(f"\nv2 自建测试集按文体统计（v1 vs v2）:")
    genres = sorted(set(list(v198_v1['by_genre'].keys()) + list(v198_v2['by_genre'].keys())))
    for genre in genres:
        v1_g = v198_v1['by_genre'].get(genre, {})
        v2_g = v198_v2['by_genre'].get(genre, {})
        v1_acc = v1_g.get('correct', 0) / v1_g.get('total', 1) if v1_g.get('total', 0) > 0 else 0
        v2_acc = v2_g.get('correct', 0) / v2_g.get('total', 1) if v2_g.get('total', 0) > 0 else 0
        print(f"  {genre:<16}: v1={v1_acc:.1%}, v2={v2_acc:.1%}, {'+' if v2_acc>v1_acc else ''}{v2_acc-v1_acc:+.1%}")
    
    # ========== 第三部分：小说文本 ==========
    print(f"\n{'='*60}")
    print(f"第三部分：本地小说文本对比")
    print(f"{'='*60}")
    
    novel_results = {}
    
    for name, path in NOVEL_FILES:
        if not path.exists():
            print(f"  ⚠️ 文件不存在: {path}")
            continue
        
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"\n处理 {name} ({len(text)} 字符)...")
        
        t0 = time.time()
        nv1 = evaluate_on_novel(extractor_v1, text)
        t1 = time.time()
        
        t2 = time.time()
        nv2 = evaluate_on_novel(extractor_v2, text)
        t3 = time.time()
        
        novel_results[name] = {'v1': nv1, 'v2': nv2}
        
        print(f"  v1: {nv1['total']} 句, 耗时 {t1-t0:.3f}s")
        print(f"  v2: {nv2['total']} 句, 耗时 {t3-t2:.3f}s")
        print(f"  v1 情绪分布: {dict(nv1['by_emotion'])}")
        print(f"  v2 情绪分布: {dict(nv2['by_emotion'])}")
    
    all_results['novels'] = novel_results
    
    # ========== 第四部分：武断性评估 ==========
    print(f"\n{'='*60}")
    print(f"第四部分：武断性问题专项评估")
    print(f"{'='*60}")
    
    arb_gt = evaluate_arbitrariness(gt_v1, gt_v2)
    arb_198 = evaluate_arbitrariness(v198_v1, v198_v2)
    all_results['arbitrariness'] = {'gt_100': arb_gt, 'v2_198': arb_198}
    
    print(f"\n【100 条 GT 测试集】")
    print(f"  过度自信（v1）: {arb_gt['overconfidence']['v1']} 条")
    print(f"  过度自信（v2）: {arb_gt['overconfidence']['v2']} 条")
    print(f"  情绪麻木（v1）: {arb_gt['emotion_blindness']['v1']} 条")
    print(f"  情绪麻木（v2）: {arb_gt['emotion_blindness']['v2']} 条")
    print(f"  不一致性: {arb_gt['inconsistency']['count']} 条")
    
    print(f"\n【198 条 v2 自建测试集】")
    print(f"  过度自信（v1）: {arb_198['overconfidence']['v1']} 条")
    print(f"  过度自信（v2）: {arb_198['overconfidence']['v2']} 条")
    print(f"  情绪麻木（v1）: {arb_198['emotion_blindness']['v1']} 条")
    print(f"  情绪麻木（v2）: {arb_198['emotion_blindness']['v2']} 条")
    print(f"  不一致性: {arb_198['inconsistency']['count']} 条")
    
    # ========== 导出报告 ==========
    report_dir = PROJECT_ROOT / 'analysis_reports' / '优化报告'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = report_dir / '全面测试分析数据_20260505.json'
    
    def serialize_results(data):
        """序列化结果以便 JSON 存储"""
        if isinstance(data, dict):
            return {k: serialize_results(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [serialize_results(i) for i in data]
        elif isinstance(data, float):
            return round(data, 4)
        else:
            return data
    
    serializable = {
        'gt_100': {
            'v1': {
                'total': gt_v1['total'],
                'accuracy_l2': gt_v1['accuracy_l2'],
                'accuracy_l1': evaluate_l1(gt_v1),
                'by_emotion': gt_v1['by_emotion'],
                'by_genre': gt_v1['by_genre'],
                'by_difficulty': gt_v1['by_difficulty'],
                'confusion': gt_v1['confusion'],
            },
            'v2': {
                'total': gt_v2['total'],
                'accuracy_l2': gt_v2['accuracy_l2'],
                'accuracy_l1': evaluate_l1(gt_v2),
                'by_emotion': gt_v2['by_emotion'],
                'by_genre': gt_v2['by_genre'],
                'by_difficulty': gt_v2['by_difficulty'],
                'confusion': gt_v2['confusion'],
            },
        },
        'v2_198': {
            'v1': {
                'total': v198_v1['total'],
                'accuracy_l2': v198_v1['accuracy_l2'],
                'accuracy_l1': evaluate_l1(v198_v1),
                'by_emotion': v198_v1['by_emotion'],
                'by_genre': v198_v1['by_genre'],
                'by_difficulty': v198_v1['by_difficulty'],
                'confusion': v198_v1['confusion'],
            },
            'v2': {
                'total': v198_v2['total'],
                'accuracy_l2': v198_v2['accuracy_l2'],
                'accuracy_l1': evaluate_l1(v198_v2),
                'by_emotion': v198_v2['by_emotion'],
                'by_genre': v198_v2['by_genre'],
                'by_difficulty': v198_v2['by_difficulty'],
                'confusion': v198_v2['confusion'],
            },
        },
        'novels': {
            name: {
                'v1': {
                    'total': data['v1']['total'],
                    'by_emotion': data['v1']['by_emotion'],
                    'by_class': data['v1']['by_class'],
                    'sample_predictions': data['v1']['results'][:20],
                },
                'v2': {
                    'total': data['v2']['total'],
                    'by_emotion': data['v2']['by_emotion'],
                    'by_class': data['v2']['by_class'],
                    'sample_predictions': data['v2']['results'][:20],
                },
            }
            for name, data in novel_results.items()
        },
        'arbitrariness': {
            'gt_100': serialize_results(arb_gt),
            'v2_198': serialize_results(arb_198),
        },
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ JSON 数据已导出: {report_path}")
    print(f"\n测试分析完成！")


if __name__ == '__main__':
    main()
