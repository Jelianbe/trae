# -*- coding: utf-8 -*-
"""上下文干预实际场景验证

模拟真实对话流程：
1. 每条样本假设有一个"前句"，前句的情绪由规则系统预测
2. 当前句继承前句的情绪（如果满足门控条件）

实验设计：
- 为每条泛化样本构造一个模拟前句
- 前句的情绪由规则系统预测（而非 GT）
- 测试上下文干预的实际效果
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import EmotionExtractor


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# 模拟前句：为每条泛化样本构造一个情绪明确的前句
# 这些前句的情绪由规则系统预测，可能正确也可能错误
MOCK_PREV_SENTENCES = {
    # sadness 前句
    'gen_005': ('唉，这件事就这么定了吧。', 'sadness'),  # 明确的悲伤信号
    'gen_007': ('我真的很难过。', 'sadness'),  # 明确的悲伤信号
    'gen_010': ('没想到会是这样……', 'sadness'),  # 省略号+失望
    'gen_011': ('这么多年了，我还是会想起她。', 'sadness'),  # 思念
    'gen_013': ('时间不早了，我该走了。', 'sadness'),  # 离别
    'gen_014': ('明天就要分别了。', 'sadness'),  # 离别
    'gen_015': ('我们之间，就这样吧。', 'sadness'),  # 决绝
    
    # anger 前句
    'gen_008': ('这件事没得商量！', 'anger'),  # 明确的愤怒信号
    'gen_009': ('你太过分了！', 'anger'),  # 明确的愤怒信号
    'gen_019': ('你敢！', 'anger'),  # 威胁
    'gen_020': ('够了！我不想再听你解释！', 'anger'),  # 愤怒
    
    # joy 前句
    'gen_012': ('哈哈，打得好！', 'joy'),  # 战斗兴奋
    'gen_017': ('看来你也不过如此。', 'joy'),  # 轻蔑/得意
    'gen_018': ('这点小事难不倒我。', 'joy'),  # 自信
    
    # fear 前句
    'gen_016': ('后面有东西在追我们！', 'fear'),  # 恐惧
}


def main():
    extractor = EmotionExtractor()
    
    gt_path = Path(__file__).parent.parent / 'tests' / 'emotion_gt_generalization.json'
    gt_data = load_gt(gt_path)
    
    print("=" * 80)
    print("上下文干预实际场景验证")
    print("=" * 80)
    print(f"数据集: {len(gt_data)} 条泛化样本")
    print("实验设计: 每条样本有一个模拟前句，前句情绪由规则系统预测")
    print()
    
    # 第一轮：无上下文
    print("=" * 80)
    print("第一轮：无上下文干预")
    print("=" * 80)
    
    no_context_correct = 0
    no_context_errors = []
    
    for item in gt_data:
        text = item['text']
        gt_l2 = item['emotion_label']
        
        result = extractor.classify(text, context_hint=None, context_confidence=0.0)
        pred_l2 = result.emotion_label
        
        if gt_l2 == pred_l2:
            no_context_correct += 1
        else:
            no_context_errors.append({
                'id': item['id'],
                'text': text,
                'gt': gt_l2,
                'pred': pred_l2,
            })
    
    print(f"正确: {no_context_correct}/{len(gt_data)} = {no_context_correct/len(gt_data):.1%}")
    print(f"错误: {len(no_context_errors)} 条")
    
    # 第二轮：有上下文（实际场景）
    print()
    print("=" * 80)
    print("第二轮：有上下文干预（实际场景）")
    print("=" * 80)
    
    with_context_correct = 0
    with_context_errors = []
    corrected = []
    
    for item in gt_data:
        text = item['text']
        gt_l2 = item['emotion_label']
        item_id = item['id']
        
        # 获取模拟前句
        if item_id in MOCK_PREV_SENTENCES:
            prev_text, expected_prev_emotion = MOCK_PREV_SENTENCES[item_id]
            
            # 前句情绪由规则系统预测
            prev_result = extractor.classify(prev_text)
            prev_emotion = prev_result.emotion_label
            prev_confidence = prev_result.confidence
            
            # 当前句继承前句情绪
            result = extractor.classify(text, context_hint=prev_emotion, context_confidence=prev_confidence)
        else:
            # 没有模拟前句，使用无上下文预测
            result = extractor.classify(text, context_hint=None, context_confidence=0.0)
        
        pred_l2 = result.emotion_label
        
        if gt_l2 == pred_l2:
            with_context_correct += 1
            # 检查是否是被纠正的
            for e in no_context_errors:
                if e['id'] == item_id:
                    corrected.append({
                        'id': item_id,
                        'text': text,
                        'gt': gt_l2,
                        'before': e['pred'],
                        'after': pred_l2,
                    })
                    break
        else:
            with_context_errors.append({
                'id': item_id,
                'text': text,
                'gt': gt_l2,
                'pred': pred_l2,
            })
    
    print(f"正确: {with_context_correct}/{len(gt_data)} = {with_context_correct/len(gt_data):.1%}")
    print(f"错误: {len(with_context_errors)} 条")
    print(f"纠正: {len(corrected)} 条")
    
    # 显示被纠正的样本
    if corrected:
        print()
        print("-" * 80)
        print(f"被纠正的样本 ({len(corrected)} 条)")
        print("-" * 80)
        for c in corrected:
            print(f"{c['id']}: {c['text'][:30]:30s} GT={c['gt']:10s} {c['before']:10s} → {c['after']:10s}")
    
    # 总结
    print()
    print("=" * 80)
    print("实验结论")
    print("=" * 80)
    print(f"无上下文正确率: {no_context_correct}/{len(gt_data)} = {no_context_correct/len(gt_data):.1%}")
    print(f"有上下文正确率: {with_context_correct}/{len(gt_data)} = {with_context_correct/len(gt_data):.1%}")
    print(f"纠正率: {len(corrected)}/{len(no_context_errors)} = {len(corrected)/max(len(no_context_errors), 1):.1%}")
    print()
    
    if with_context_correct / len(gt_data) >= 0.5:
        print("✅ 达成目标：泛化样本准确率 >= 50%")
    else:
        print(f"❌ 未达标：泛化样本准确率 {with_context_correct/len(gt_data):.1%} < 50%")
        print("   需要排查错误级联案例，调门控阈值")


if __name__ == '__main__':
    main()
