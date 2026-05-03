#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
情绪标注能力验证脚本

用途：
1. 验证情绪标注器的准确性
2. 对比标注结果与预期情绪
3. 计算准确率、召回率、F1 分数

使用方法：
    python scripts/validate_emotion_tagger.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emotion_tagger import get_emotion_tagger, EmotionTagger


@dataclass
class TestSentence:
    """测试句子"""
    text: str
    expected_emotion: str
    speaker: str = ""
    description: str = ""


@dataclass
class EvaluationResult:
    """评估结果"""
    total: int
    correct: int
    incorrect: int
    accuracy: float
    errors: List[Tuple[str, str, str]]  # (text, expected, predicted)


def create_test_sentences() -> List[TestSentence]:
    """创建测试句子"""
    return [
        # 喜悦（Joy）测试
        TestSentence(
            text="萧炎笑道：\"太好了，我终于突破了！\"",
            expected_emotion="joy",
            description="角色高兴，使用'笑'和'太好了'"
        ),
        TestSentence(
            text="他高兴得跳了起来，心中充满了喜悦。",
            expected_emotion="joy",
            description="描述高兴情绪"
        ),
        TestSentence(
            text="\"哈哈，这次一定要让他们刮目相看！\"",
            expected_emotion="joy",
            description="使用'哈哈'表示开心"
        ),
        
        # 愤怒（Anger）测试
        TestSentence(
            text="萧炎怒喝道：\"放肆！你敢背叛我？\"",
            expected_emotion="anger",
            description="角色愤怒，使用'怒喝'"
        ),
        TestSentence(
            text="他气得浑身发抖，眼中冒出怒火。",
            expected_emotion="anger",
            description="描述愤怒情绪"
        ),
        TestSentence(
            text="\"混蛋！我绝不会放过你！\"",
            expected_emotion="anger",
            description="使用'混蛋'表示愤怒"
        ),
        
        # 悲伤（Sadness）测试
        TestSentence(
            text="萧炎低声叹息：\"她还是走了。\"",
            expected_emotion="sadness",
            description="角色悲伤，使用'叹息'"
        ),
        TestSentence(
            text="他心中一阵悲伤，泪水无声地滑落。",
            expected_emotion="sadness",
            description="描述悲伤情绪"
        ),
        TestSentence(
            text="\"唉，为什么会这样？\"",
            expected_emotion="sadness",
            description="使用'唉'表示叹息"
        ),
        
        # 惊讶（Surprise）测试
        TestSentence(
            text="萧炎惊讶地看着眼前的一切：\"这怎么可能？\"",
            expected_emotion="surprise",
            description="角色惊讶，使用'惊讶'"
        ),
        TestSentence(
            text="他简直不敢相信自己的眼睛。",
            expected_emotion="surprise",
            description="描述惊讶情绪"
        ),
        TestSentence(
            text="\"什么？你居然还活着？\"",
            expected_emotion="surprise",
            description="使用'什么'和'居然'表示惊讶"
        ),
        
        # 恐惧（Fear）测试
        TestSentence(
            text="萧炎心中一阵恐慌：\"太可怕了，我们快逃！\"",
            expected_emotion="fear",
            description="角色恐惧，使用'恐慌'"
        ),
        TestSentence(
            text="他吓得浑身发抖，不敢回头看。",
            expected_emotion="fear",
            description="描述恐惧情绪"
        ),
        TestSentence(
            text="\"危险！快躲开！\"",
            expected_emotion="fear",
            description="使用'危险'表示恐惧"
        ),
        
        # 中性（Neutral）测试
        TestSentence(
            text="萧炎缓缓睁开眼睛，目光扫过四周。",
            expected_emotion="neutral",
            description="描述动作，无明显情绪"
        ),
        TestSentence(
            text="他站起身来，走向门口。",
            expected_emotion="neutral",
            description="描述动作，无明显情绪"
        ),
        TestSentence(
            text="\"走吧，我们该出发了。\"",
            expected_emotion="neutral",
            description="普通对话，无明显情绪"
        ),
    ]


def evaluate_emotion_tagger(
    tagger: EmotionTagger,
    test_sentences: List[TestSentence]
) -> EvaluationResult:
    """
    评估情绪标注器
    
    Args:
        tagger: 情绪标注器实例
        test_sentences: 测试句子列表
    
    Returns:
        评估结果
    """
    total = len(test_sentences)
    correct = 0
    incorrect = 0
    errors = []
    
    print(f"\n{'='*60}")
    print(f"情绪标注器评估")
    print(f"{'='*60}\n")
    
    for i, sentence in enumerate(test_sentences, 1):
        predicted = tagger.tag(sentence.text, sentence.speaker)
        
        is_correct = predicted == sentence.expected_emotion
        
        if is_correct:
            correct += 1
            status = "✅"
        else:
            incorrect += 1
            status = "❌"
            errors.append((sentence.text, sentence.expected_emotion, predicted))
        
        print(f"{i:2d}. {status} 预期: {sentence.expected_emotion:<10} | "
              f"预测: {predicted:<10} | {sentence.description}")
        if not is_correct:
            print(f"    文本: {sentence.text[:60]}...")
    
    accuracy = correct / total if total > 0 else 0
    
    return EvaluationResult(
        total=total,
        correct=correct,
        incorrect=incorrect,
        accuracy=accuracy,
        errors=errors,
    )


def evaluate_multi_label_tagger(
    tagger: EmotionTagger,
) -> None:
    """评估多标签情绪标注"""
    print(f"\n{'='*60}")
    print(f"多标签情绪标注测试")
    print(f"{'='*60}\n")
    
    test_texts = [
        ("萧炎又惊又喜：\"太好了，你居然还活着！\"", ["surprise", "joy"]),
        ("他心中一阵后怕：\"刚才真是太危险了。\"", ["fear"]),
        ("她开心地笑着，眼中却含着泪水。", ["joy", "sadness"]),
    ]
    
    for text, expected_emotions in test_texts:
        result = tagger.tag_multi_label(text)
        print(f"文本: {text}")
        print(f"预期情绪: {expected_emotions}")
        print(f"预测情绪: {result}")
        print()


def print_summary(result: EvaluationResult) -> None:
    """打印评估摘要"""
    print(f"\n{'='*60}")
    print(f"评估摘要")
    print(f"{'='*60}")
    print(f"总测试数: {result.total}")
    print(f"正确数: {result.correct}")
    print(f"错误数: {result.incorrect}")
    print(f"准确率: {result.accuracy:.1%}")
    
    if result.errors:
        print(f"\n错误分析:")
        for text, expected, predicted in result.errors:
            print(f"  - 预期: {expected}, 预测: {predicted}")
            print(f"    文本: {text[:80]}...")
    
    print()


def main():
    """主函数"""
    # 获取情绪标注器实例
    tagger = get_emotion_tagger()
    
    # 创建测试句子
    test_sentences = create_test_sentences()
    
    # 评估单标签标注
    result = evaluate_emotion_tagger(tagger, test_sentences)
    print_summary(result)
    
    # 评估多标签标注
    evaluate_multi_label_tagger(tagger)
    
    # 判断是否达到目标
    if result.accuracy >= 0.70:
        print("✅ 达到目标准确率（≥70%），可用于 TTS 声音调整")
    elif result.accuracy >= 0.50:
        print("⚠️  准确率偏低（50-70%），建议调整关键词词典")
    else:
        print("❌ 准确率过低（<50%），建议使用 ML 模型替代规则")


if __name__ == '__main__':
    main()
