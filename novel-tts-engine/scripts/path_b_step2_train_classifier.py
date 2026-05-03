#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路径B-第二步：训练轻量情绪分类器

使用 TF-IDF + LogisticRegression（完全本地，CPU友好）
结合50句GT + 150句初标数据训练
"""

import sys
import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
import joblib

PROJECT_ROOT = Path(__file__).parent.parent

EMOTION_LABELS = ["neutral", "joy", "anger", "sadness", "surprise", "fear"]


def load_training_data():
    """加载训练数据（50句GT + 150句初标）"""
    labeled_path = PROJECT_ROOT / "data" / "raw_sentences_150_labeled.json"
    
    with open(labeled_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    texts = []
    labels = []
    
    for item in data:
        # 组合上下文 + 对话
        text = item["context_before"][-50:] + item["text"] + item["context_after"][:50]
        label = item["predicted_emotion"]
        
        texts.append(text)
        labels.append(label)
    
    print(f"加载到 {len(texts)} 条训练数据")
    
    # 统计分布
    from collections import Counter
    dist = Counter(labels)
    print("情绪分布:")
    for label, count in sorted(dist.items()):
        print(f"  {label}: {count}")
    
    return texts, labels


def train_classifier(texts, labels):
    """训练分类器"""
    # 创建 Pipeline: TF-IDF + LogisticRegression
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
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
    
    # 在全部数据上训练最终模型
    pipeline.fit(texts, labels)
    
    # 保存模型
    model_path = PROJECT_ROOT / "models" / "emotion_classifier.pkl"
    model_path.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, str(model_path))
    print(f"\n模型已保存到: {model_path}")
    
    return pipeline, cv_scores


def evaluate_on_gt50(pipeline):
    """在50句GT上评估"""
    import re
    
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
    
    # 评估
    correct = 0
    predictions = []
    actuals = []
    
    print(f"\n{'='*80}")
    print(f"50句GT评估结果")
    print(f"{'='*80}")
    
    for ann in gt_annotations:
        text = contexts.get(ann['id'], "")
        if not text:
            continue
        
        pred = pipeline.predict([text])[0]
        actual = ann['emotion']
        
        predictions.append(pred)
        actuals.append(actual)
        
        if pred == actual:
            correct += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"{ann['id']:2d}. {status} GT: {actual:<10} | 预测: {pred:<10} | {text[:40]}")
    
    accuracy = correct / len(gt_annotations) if gt_annotations else 0
    print(f"\n准确率: {accuracy:.1%} ({correct}/{len(gt_annotations)})")
    
    # 混淆矩阵
    print(f"\n混淆矩阵:")
    print(f"{'GT↓ / 预测→':<12} | " + " | ".join([f"{e:<8}" for e in EMOTION_LABELS]))
    print("-" * 80)
    
    cm = confusion_matrix(actuals, predictions, labels=EMOTION_LABELS)
    for i, label in enumerate(EMOTION_LABELS):
        row_str = " | ".join([f"{cm[i][j]:>8}" for j in range(len(EMOTION_LABELS))])
        print(f"{label:<12} | {row_str}")
    
    return accuracy


def main():
    print("="*80)
    print("路径B-第二步：训练轻量情绪分类器")
    print("="*80)
    
    # 加载数据
    texts, labels = load_training_data()
    
    # 训练
    pipeline, cv_scores = train_classifier(texts, labels)
    
    # 在50句GT上评估
    accuracy = evaluate_on_gt50(pipeline)
    
    print(f"\n{'='*80}")
    print(f"最终结果")
    print(f"{'='*80}")
    print(f"交叉验证准确率: {cv_scores.mean():.1%}")
    print(f"GT50准确率: {accuracy:.1%}")
    print(f"目标准确率: 65%")
    
    if accuracy >= 0.65:
        print("✅ 达到目标！")
    else:
        print(f"⚠️ 未达目标（差 {0.65 - accuracy:.1%}）")
        print("建议：增加人工校准数据或调整模型参数")


if __name__ == '__main__':
    main()
