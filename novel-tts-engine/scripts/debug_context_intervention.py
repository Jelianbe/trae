# -*- coding: utf-8 -*-
"""排查上下文干预失败原因"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import EmotionExtractor


# 模拟前句
MOCK_PREV_SENTENCES = {
    'gen_005': ('唉，这件事就这么定了吧。', 'sadness'),
    'gen_007': ('我真的很难过。', 'sadness'),
    'gen_008': ('这件事没得商量！', 'anger'),
    'gen_009': ('你太过分了！', 'anger'),
    'gen_010': ('没想到会是这样……', 'sadness'),
    'gen_011': ('这么多年了，我还是会想起她。', 'sadness'),
    'gen_012': ('哈哈，打得好！', 'joy'),
    'gen_013': ('时间不早了，我该走了。', 'sadness'),
    'gen_014': ('明天就要分别了。', 'sadness'),
    'gen_015': ('我们之间，就这样吧。', 'sadness'),
    'gen_016': ('后面有东西在追我们！', 'fear'),
    'gen_017': ('看来你也不过如此。', 'joy'),
    'gen_018': ('这点小事难不倒我。', 'joy'),
    'gen_019': ('你敢！', 'anger'),
    'gen_020': ('够了！我不想再听你解释！', 'anger'),
}


def main():
    extractor = EmotionExtractor()
    
    gt_path = Path(__file__).parent.parent / 'tests' / 'emotion_gt_generalization.json'
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    
    print("=" * 100)
    print("排查上下文干预失败原因")
    print("=" * 100)
    
    # 统计失败模式
    failure_modes = {
        '前句预测错误': [],
        '前句置信度<0.5': [],
        '当前句有情绪信号': [],
        '其他': [],
    }
    
    for item in gt_data:
        item_id = item['id']
        text = item['text']
        gt_l2 = item['emotion_label']
        
        if item_id not in MOCK_PREV_SENTENCES:
            continue
        
        prev_text, expected_prev_emotion = MOCK_PREV_SENTENCES[item_id]
        prev_result = extractor.classify(prev_text)
        prev_emotion = prev_result.emotion_label
        prev_confidence = prev_result.confidence
        
        # 当前句预测
        result = extractor.classify(text, context_hint=prev_emotion, context_confidence=prev_confidence)
        pred_l2 = result.emotion_label
        
        # 检查是否正确
        if pred_l2 == gt_l2:
            continue  # 正确，跳过
        
        # 排查失败原因
        print(f"\n{'─' * 100}")
        print(f"ID: {item_id}")
        print(f"当前句: {text}")
        print(f"GT情绪: {gt_l2}, 预测情绪: {pred_l2}")
        print(f"前句: {prev_text}")
        print(f"前句预测: {prev_emotion} (期望: {expected_prev_emotion}), 置信度: {prev_confidence:.2f}")
        
        # 分类失败模式
        if prev_emotion != expected_prev_emotion:
            failure_modes['前句预测错误'].append(item_id)
            print(f"失败模式: 前句预测错误")
        elif prev_confidence < 0.5:
            failure_modes['前句置信度<0.5'].append(item_id)
            print(f"失败模式: 前句置信度<0.5")
        else:
            # 检查当前句是否有情绪信号
            result_no_context = extractor.classify(text)
            if result_no_context.confidence > 0.35:
                failure_modes['当前句有情绪信号'].append(item_id)
                print(f"失败模式: 当前句有情绪信号 (置信度: {result_no_context.confidence:.2f})")
            else:
                failure_modes['其他'].append(item_id)
                print(f"失败模式: 其他")
    
    print(f"\n{'=' * 100}")
    print("失败模式统计")
    print("=" * 100)
    for mode, ids in failure_modes.items():
        print(f"{mode}: {len(ids)} 条")
        if ids:
            print(f"  样本: {ids}")


if __name__ == '__main__':
    main()
