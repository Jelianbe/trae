# -*- coding: utf-8 -*-
"""v1 vs v2 情绪提取器在本地小说文本上的对比

用 v1（标准版）和 v2（改进版）分别处理本地小说文本，对比情绪分布。

运行方式：
    python scripts/compare_v2_on_novels.py
"""

import json
import sys
import time
from pathlib import Path
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
V1_PIPELINE = PROJECT_ROOT / 'pipeline'
V2_DIR = Path(r'D:\trae\说说看法')

# 本地小说文本
NOVEL_FILES = [
    PROJECT_ROOT / 'tests' / 'test_novel_urban.txt',        # 都市
    PROJECT_ROOT / 'tests' / 'test_novel_western.txt',      # 西幻
    PROJECT_ROOT / 'tests' / 'test_novel_doupo_ch1-10.txt', # 斗破苍穹
    PROJECT_ROOT / 'tests' / 'test_novel_guimi_ch1-10.txt', # 闺蜜
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


def split_into_sentences(text: str) -> list:
    """将文本按标点分割成句子（模拟 pipeline 的处理）"""
    import re
    # 按句号、问号、感叹号、省略号分割
    sentences = re.split(r'[。！？!?.…]+', text)
    # 过滤空行
    return [s.strip() for s in sentences if s.strip()][:200]  # 最多取 200 句


def evaluate_on_novel(extractor, text: str) -> dict:
    """在小说文本上评估情绪提取器"""
    sentences = split_into_sentences(text)
    
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
    
    # 统计
    total = len(results)
    by_emotion = defaultdict(int)
    for r in results:
        by_emotion[r['emotion']] += 1
    
    by_class = defaultdict(int)
    for r in results:
        by_class[r['class']] += 1
    
    # 找出高置信度的典型案例
    high_conf_examples = defaultdict(list)
    for r in results:
        if r['confidence'] >= 0.6:
            emotion = r['emotion']
            if len(high_conf_examples[emotion]) < 3:
                high_conf_examples[emotion].append(r)
    
    return {
        'total': total,
        'by_emotion': dict(by_emotion),
        'by_class': dict(by_class),
        'results': results,
        'high_conf_examples': {k: v for k, v in high_conf_examples.items()},
    }


def print_novel_comparison(novel_name: str, v1_result: dict, v2_result: dict):
    """打印小说对比报告"""
    print(f"\n{'='*80}")
    print(f"📖 {novel_name}")
    print(f"{'='*80}")
    print(f"分析句子数: {v1_result['total']}")
    
    # 情绪分布对比
    print(f"\n情绪分布对比（L2 细分类）")
    print(f"{'-'*60}")
    print(f"{'情绪':<12} {'v1 数量':<12} {'v1 占比':<12} {'v2 数量':<12} {'v2 占比':<12} {'差异':<10}")
    print(f"{'-'*60}")
    
    emotions = sorted(set(list(v1_result['by_emotion'].keys()) + list(v2_result['by_emotion'].keys())))
    for e in emotions:
        v1_count = v1_result['by_emotion'].get(e, 0)
        v2_count = v2_result['by_emotion'].get(e, 0)
        v1_pct = v1_count / v1_result['total'] * 100 if v1_result['total'] > 0 else 0
        v2_pct = v2_count / v2_result['total'] * 100 if v2_result['total'] > 0 else 0
        diff = v2_pct - v1_pct
        
        print(f"{e:<12} {v1_count:<12} {v1_pct:<11.1f}% {v2_count:<12} {v2_pct:<11.1f}% {'+' if diff>0 else ''}{diff:+.1f}%")
    
    # L1 分布对比
    print(f"\n情绪分布对比（L1 粗分类）")
    print(f"{'-'*60}")
    print(f"{'类别':<12} {'v1 数量':<12} {'v1 占比':<12} {'v2 数量':<12} {'v2 占比':<12} {'差异':<10}")
    print(f"{'-'*60}")
    
    classes = sorted(set(list(v1_result['by_class'].keys()) + list(v2_result['by_class'].keys())))
    for c in classes:
        v1_count = v1_result['by_class'].get(c, 0)
        v2_count = v2_result['by_class'].get(c, 0)
        v1_pct = v1_count / v1_result['total'] * 100 if v1_result['total'] > 0 else 0
        v2_pct = v2_count / v2_result['total'] * 100 if v2_result['total'] > 0 else 0
        diff = v2_pct - v1_pct
        
        print(f"{c:<12} {v1_count:<12} {v1_pct:<11.1f}% {v2_count:<12} {v2_pct:<11.1f}% {'+' if diff>0 else ''}{diff:+.1f}%")
    
    # v1 v2 差异案例
    v1_emotions = {r['text']: r['emotion'] for r in v1_result['results']}
    v2_emotions = {r['text']: r['emotion'] for r in v2_result['results']}
    
    different = []
    for text in v1_emotions:
        if text in v2_emotions and v1_emotions[text] != v2_emotions[text]:
            different.append({
                'text': text,
                'v1': v1_emotions[text],
                'v2': v2_emotions[text],
            })
    
    if different:
        print(f"\n情绪预测不同的句子（共 {len(different)} 条）")
        print(f"{'-'*80}")
        for i, d in enumerate(different[:15]):
            text_short = d['text'][:60] + '...' if len(d['text']) > 60 else d['text']
            print(f"  {i+1}. v1: {d['v1']}, v2: {d['v2']}")
            print(f"     {text_short}")


def main():
    print("="*80)
    print("v1 vs v2 情绪提取器在本地小说文本上的对比")
    print("="*80)
    
    # 加载提取器
    print(f"\n加载 v1 情绪提取器...")
    extractor_v1 = load_v1_extractor()
    print(f"  ✅ v1 加载成功")
    
    print(f"加载 v2 情绪提取器...")
    extractor_v2 = load_v2_extractor()
    print(f"  ✅ v2 加载成功")
    
    all_results = {}
    
    for novel_path in NOVEL_FILES:
        if not novel_path.exists():
            print(f"\n⚠️ 文件不存在: {novel_path}")
            continue
        
        novel_name = novel_path.stem
        
        print(f"\n📖 处理: {novel_name}...")
        with open(novel_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"  文件大小: {len(text)} 字符")
        
        t0 = time.time()
        v1_result = evaluate_on_novel(extractor_v1, text)
        t1 = time.time()
        print(f"  ✅ v1 完成: {v1_result['total']} 句, 耗时 {t1-t0:.1f}s")
        
        t2 = time.time()
        v2_result = evaluate_on_novel(extractor_v2, text)
        t3 = time.time()
        print(f"  ✅ v2 完成: {v2_result['total']} 句, 耗时 {t3-t2:.1f}s")
        
        print_novel_comparison(novel_name, v1_result, v2_result)
        
        all_results[novel_name] = {
            'v1': {
                'total': v1_result['total'],
                'by_emotion': v1_result['by_emotion'],
                'by_class': v1_result['by_class'],
            },
            'v2': {
                'total': v2_result['total'],
                'by_emotion': v2_result['by_emotion'],
                'by_class': v2_result['by_class'],
            },
        }
    
    # 导出 JSON 报告
    report_dir = PROJECT_ROOT / 'analysis_reports' / '优化报告'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = report_dir / 'v2本地小说对比评估报告_20260505.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\nJSON 报告已导出: {report_path}")


if __name__ == '__main__':
    main()
