#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路径B-第二步（修正）：用GT50训练并评估ML上限

策略：
1. 从GT50 + emotion_test_sentences_with_context.txt 提取文本和标签
2. 用5折交叉验证评估ML模型的理论上限
3. 保存模型用于混合推理
"""

import sys
import re
import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

PROJECT_ROOT = Path(__file__).parent.parent

EMOTION_LABELS = ["neutral", "joy", "anger", "sadness", "surprise", "fear"]


def load_gt50():
    """加载GT50标注数据和上下文文本"""
    gt_path = PROJECT_ROOT / "tests" / "deepseek标注文件.txt"
    context_path = PROJECT_ROOT / "tests" / "emotion_test_sentences_with_context.txt"
    
    # 解析GT标注
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
            if len(parts) >= 2 and parts[0].isdigit():
                gt_annotations.append({
                    'id': int(parts[0]),
                    'emotion': parts[1],
                    'intensity': parts[2] if len(parts) > 2 else 'moderate',
                    'tone': parts[3] if len(parts) > 3 else '',
                })
    
    # 解析上下文
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
    
    # 组合
    texts = []
    labels = []
    
    for ann in gt_annotations:
        text = contexts.get(ann['id'], "")
        if text:
            texts.append(text)
            labels.append(ann['emotion'])
    
    print(f"加载到 {len(texts)} 条GT数据")
    
    # 统计分布
    from collections import Counter
    dist = Counter(labels)
    print("GT情绪分布:")
    for label, count in sorted(dist.items()):
        print(f"  {label}: {count}")
    
    return texts, labels


def train_and_evaluate(texts, labels):
    """训练并评估ML模型"""
    # Pipeline: TF-IDF + LogisticRegression
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            analyzer='char_wb',  # 字符级ngram更适合中文
        )),
        ('clf', LogisticRegression(
            max_iter=1000,
            C=1.0,
            random_state=42,
        ))
    ])
    
    # 5折交叉验证
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, texts, labels, cv=cv, scoring='accuracy')
    
    print(f"\n5折交叉验证结果:")
    print(f"  准确率: {cv_scores.mean():.3f} (±{cv_scores.std():.3f})")
    for i, score in enumerate(cv_scores):
        print(f"  Fold {i+1}: {score:.3f}")
    
    # 获取预测结果用于分析
    predictions = cross_val_predict(pipeline, texts, labels, cv=cv)
    
    # 混淆矩阵
    print(f"\n混淆矩阵:")
    print(f"{'GT↓ / 预测→':<12} | " + " | ".join([f"{e:<10}" for e in EMOTION_LABELS]))
    print("-" * 90)
    
    cm = confusion_matrix(labels, predictions, labels=EMOTION_LABELS)
    for i, label in enumerate(EMOTION_LABELS):
        row_str = " | ".join([f"{cm[i][j]:>10}" for j in range(len(EMOTION_LABELS))])
        print(f"{label:<12} | {row_str}")
    
    # 分类报告
    print(f"\n分类报告:")
    print(classification_report(labels, predictions, labels=EMOTION_LABELS, zero_division=0))
    
    # 详细对比
    print(f"\n详细对比:")
    for i, (text, actual, pred) in enumerate(zip(texts, labels, predictions)):
        status = "✅" if actual == pred else "❌"
        print(f"{i+1:2d}. {status} GT: {actual:<10} | 预测: {pred:<10} | {text[:50]}")
    
    # 在全部数据上训练最终模型
    pipeline.fit(texts, labels)
    
    # 保存模型
    model_path = PROJECT_ROOT / "models" / "emotion_classifier_gt50.pkl"
    model_path.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, str(model_path))
    print(f"\n模型已保存到: {model_path}")
    
    return pipeline, cv_scores.mean(), predictions


def main():
    print("="*80)
    print("路径B-第二步：用GT50评估ML理论上限")
    print("="*80)
    
    # 加载GT50
    texts, labels = load_gt50()
    
    # 训练评估
    pipeline, cv_accuracy, predictions = train_and_evaluate(texts, labels)
    
    print(f"\n{'='*80}")
    print(f"最终结果")
    print(f"{'='*80}")
    print(f"GT50交叉验证准确率: {cv_accuracy:.1%}")
    print(f"规则标注器准确率: 56.0%")
    print(f"目标准确率: 65%")
    
    if cv_accuracy >= 0.65:
        print("✅ ML模型达到目标！")
    else:
        print(f"⚠️ ML模型未达目标（差 {0.65 - cv_accuracy:.1%}）")
        print("说明：50句数据量有限，需要更多标注数据")


if __name__ == '__main__':
    main()
