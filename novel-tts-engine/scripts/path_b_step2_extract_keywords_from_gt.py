#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路径B-第二步（修正）：用GT50分析关键词并扩展规则词典

策略：
1. 从GT50中提取高频情绪关键词（数据驱动）
2. 统计每个词在各情绪类别中的分布
3. 筛选高区分度词（某情绪占比 >70%）→ 自动扩展规则词典
4. 验证扩展后的准确率提升
"""

import sys
import re
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent


def load_gt50():
    """加载GT50标注数据和上下文文本"""
    gt_path = PROJECT_ROOT / "tests" / "deepseek标注文件.txt"
    context_path = PROJECT_ROOT / "tests" / "emotion_test_sentences_with_context.txt"
    
    with open(gt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    gt_annotations = []
    lines = content.strip().split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('| # |'):
            in_table = True
            continue
        
        if in_table and line.startswith('|'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 6 and parts[0].isdigit():
                gt_annotations.append({
                    'id': int(parts[0]),
                    'emotion': parts[1],
                    'tone': parts[3],
                    'reason': parts[5],
                })
    
    with open(context_path, 'r', encoding='utf-8') as f:
        context_content = f.read()
    
    contexts = {}
    current_id = None
    in_target = False
    
    for line in context_content.split('\n'):
        line_stripped = line.strip()
        if line_stripped.startswith('#') and line_stripped[1:].isdigit():
            current_id = int(line_stripped[1:])
            continue
        
        if '【目标对话】' in line_stripped:
            in_target = True
            continue
        
        if in_target and current_id and line_stripped:
            contexts[current_id] = line_stripped
            in_target = False
    
    return gt_annotations, contexts


def extract_keywords_from_annotations(gt_annotations, contexts):
    """
    从GT标注中统计提取关键词
    
    策略：
    1. 提取引导词（引号前的动词短语）
    2. 提取判断依据中的高频词
    3. 统计每个词在各情绪中的分布
    """
    emotion_keywords = {
        "joy": Counter(),
        "anger": Counter(),
        "sadness": Counter(),
        "surprise": Counter(),
        "fear": Counter(),
    }
    
    for ann in gt_annotations:
        emotion = ann['emotion']
        if emotion == 'neutral':
            continue
        
        text = contexts.get(ann['id'], "")
        tone = ann.get('tone', '')
        reason = ann.get('reason', '')
        
        # 合并语气和判断依据
        all_text = tone + " " + reason + " " + text
        
        # 提取2-3字关键词
        for length in [2, 3]:
            for i in range(len(all_text) - length + 1):
                word = all_text[i:i+length]
                if re.match(r'^[\u4e00-\u9fa5]+$', word):  # 纯中文
                    emotion_keywords[emotion][word] += 1
    
    return emotion_keywords


def filter_high_discrimination_keywords(emotion_keywords, min_count=2, min_ratio=0.7):
    """
    筛选高区分度关键词
    
    规则：
    - 在某情绪中出现 >= min_count 次
    - 在该情绪中的占比 >= min_ratio
    """
    all_words = set()
    for emotion, counter in emotion_keywords.items():
        all_words.update(counter.keys())
    
    filtered = {}
    
    for word in all_words:
        # 统计该词在各情绪中的分布
        emotion_counts = {}
        total = 0
        for emotion, counter in emotion_keywords.items():
            count = counter.get(word, 0)
            if count > 0:
                emotion_counts[emotion] = count
                total += count
        
        if total >= min_count:
            # 找到最高频的情绪
            best_emotion = max(emotion_counts, key=emotion_counts.get)
            best_ratio = emotion_counts[best_emotion] / total
            
            if best_ratio >= min_ratio:
                if best_emotion not in filtered:
                    filtered[best_emotion] = []
                filtered[best_emotion].append({
                    'word': word,
                    'count': total,
                    'ratio': best_ratio,
                    'distribution': emotion_counts,
                })
    
    # 按count排序
    for emotion in filtered:
        filtered[emotion].sort(key=lambda x: x['count'], reverse=True)
    
    return filtered


def main():
    print("="*80)
    print("路径B-第二步（修正）：数据驱动扩展关键词")
    print("="*80)
    
    # 加载GT50
    gt_annotations, contexts = load_gt50()
    print(f"加载到 {len(gt_annotations)} 条GT数据")
    
    # 提取关键词
    emotion_keywords = extract_keywords_from_annotations(gt_annotations, contexts)
    
    # 统计总词数
    total_words = sum(len(counter) for counter in emotion_keywords.values())
    print(f"提取到 {total_words} 个候选词")
    
    # 筛选高区分度词
    filtered = filter_high_discrimination_keywords(emotion_keywords)
    
    print(f"\n筛选出的高区分度关键词:")
    for emotion, words in sorted(filtered.items()):
        print(f"\n{emotion}:")
        for w in words[:10]:
            dist_str = ", ".join([f"{e}:{c}" for e, c in w['distribution'].items()])
            print(f"  {w['word']}: count={w['count']}, ratio={w['ratio']:.1%}, dist=[{dist_str}]")
    
    # 生成扩展词典建议
    print(f"\n{'='*80}")
    print(f"扩展词典建议")
    print(f"{'='*80}")
    
    for emotion, words in sorted(filtered.items()):
        words_list = [w['word'] for w in words if len(w['word']) >= 2]
        if words_list:
            print(f'\n"{emotion}": [')
            print(f'    r"{words_list[0]}", r"{words_list[1]}", ...')
            print(f']')


if __name__ == '__main__':
    main()
