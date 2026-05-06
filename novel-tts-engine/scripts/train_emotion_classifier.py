# -*- coding: utf-8 -*-
"""
情绪分类器训练脚本
从 emotion_gt_100.json 训练决策树分类器
使用 extract_features() 输出作为特征向量
"""
import json
import sys
import os
import pickle
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.emotion_extractor import EmotionExtractor
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, accuracy_score
import numpy as np


def features_to_vector(features, text: str) -> list:
    """将 EmotionFeatures 转换为 ML 特征向量"""
    return [
        features.exclamation_density,
        features.exclamation_count,
        features.question_count,
        float(features.has_dirty_words),
        float(features.has_emotion_verb),
        float(features.has_emotion_adverb),
        float(features.has_mood_particle),
        float(features.is_exclamatory),
        float(features.is_rhetorical),
        float(features.is_imperative),
        float(features.has_short_sentences),
        float(features.has_repetition),
        len(text),  # 文本长度
        features.avg_sentence_len,
    ]


def main():
    extractor = EmotionExtractor()
    
    # 加载 GT 数据
    gt_path = Path(__file__).parent.parent / "tests" / "emotion_gt_100.json"
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    
    # 提取特征
    X = []
    y = []
    for item in gt_data:
        features = extractor.extract_features(item['text'])
        X.append(features_to_vector(features, item['text']))
        y.append(item['emotion_label'])
    
    X = np.array(X)
    y = np.array(y)
    
    # 训练决策树
    clf = DecisionTreeClassifier(
        max_depth=5,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
        class_weight='balanced'
    )
    
    # 交叉验证
    cv_scores = cross_val_score(clf, X, y, cv=5, scoring='f1_macro')
    print(f"交叉验证 Macro F1: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
    
    # 全量训练
    clf.fit(X, y)
    
    # 训练集评估
    y_pred = clf.predict(X)
    acc = accuracy_score(y, y_pred)
    print(f"训练集准确率: {acc:.3f}")
    print()
    print("分类报告:")
    print(classification_report(y, y_pred, zero_division=0))
    
    # 保存模型
    model_path = Path(__file__).parent.parent / "models" / "emotion_classifier_v2.pkl"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'classifier': clf,
        'feature_names': [
            'exclamation_density', 'exclamation_count', 'question_count',
            'has_dirty_words', 'has_emotion_verb', 'has_emotion_adverb',
            'has_mood_particle', 'is_exclamatory', 'is_rhetorical',
            'is_imperative', 'has_short_sentences', 'has_repetition',
            'text_length', 'avg_sentence_length'
        ],
        'labels': ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral']
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"模型已保存到: {model_path}")
    return clf


if __name__ == '__main__':
    main()
