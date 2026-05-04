# -*- coding: utf-8 -*-
"""上下文干预验证实验

验证目标：测试 context_hint 参数能否纠正 neutral 抢分问题

实验设计：
- 对于每条泛化样本，假设前一句的情绪是 GT 情绪（理论上限测试）
- 对比无上下文 vs 有上下文的预测结果
- 统计纠正了多少条

注意：这是理论上限测试，实际效果取决于真实对话的上下文
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import EmotionExtractor


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    extractor = EmotionExtractor()
    
    gt_path = Path(__file__).parent.parent / 'tests' / 'emotion_gt_generalization.json'
    gt_data = load_gt(gt_path)
    
    print("=" * 80)
    print("上下文干预验证实验")
    print("=" * 80)
    print(f"数据集: {len(gt_data)} 条泛化样本")
    print("实验设计: 假设前一句情绪 = GT 情绪（理论上限测试）")
    print()
    
    # 第一轮：无上下文
    print("=" * 80)
    print("第一轮：无上下文干预")
    print("=" * 80)
    
    no_context_errors = []
    no_context_correct = 0
    
    for item in gt_data:
        text = item['text']
        gt_l2 = item['emotion_label']
        
        result = extractor.classify(text, context_hint=None)
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
    
    print(f"正确: {no_context_correct}/{len(gt_data)}")
    print(f"错误: {len(no_context_errors)} 条")
    
    # 第二轮：有上下文（理论上限）
    print()
    print("=" * 80)
    print("第二轮：有上下文干预（理论上限）")
    print("=" * 80)
    
    with_context_errors = []
    with_context_correct = 0
    corrected = []  # 被纠正的样本
    
    for item in gt_data:
        text = item['text']
        gt_l2 = item['emotion_label']
        
        # 理论上限：假设前一句情绪 = GT 情绪
        result = extractor.classify(text, context_hint=gt_l2)
        pred_l2 = result.emotion_label
        
        if gt_l2 == pred_l2:
            with_context_correct += 1
            # 检查是否是被纠正的
            for e in no_context_errors:
                if e['id'] == item['id']:
                    corrected.append({
                        'id': item['id'],
                        'text': text,
                        'gt': gt_l2,
                        'before': e['pred'],
                        'after': pred_l2,
                    })
                    break
        else:
            with_context_errors.append({
                'id': item['id'],
                'text': text,
                'gt': gt_l2,
                'pred': pred_l2,
            })
    
    print(f"正确: {with_context_correct}/{len(gt_data)}")
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
    
    # 显示仍然错误的样本
    if with_context_errors:
        print()
        print("-" * 80)
        print(f"仍然错误的样本 ({len(with_context_errors)} 条)")
        print("-" * 80)
        for e in with_context_errors[:10]:
            print(f"{e['id']}: {e['text'][:30]:30s} GT={e['gt']:10s} Pred={e['pred']:10s}")
    
    # 总结
    print()
    print("=" * 80)
    print("实验结论")
    print("=" * 80)
    print(f"无上下文正确率: {no_context_correct}/{len(gt_data)} = {no_context_correct/len(gt_data):.1%}")
    print(f"有上下文正确率: {with_context_correct}/{len(gt_data)} = {with_context_correct/len(gt_data):.1%}")
    print(f"纠正率: {len(corrected)}/{len(no_context_errors)} = {len(corrected)/max(len(no_context_errors), 1):.1%}")
    print()
    
    if len(corrected) >= 3:
        print("✅ 上下文干预有效，值得继续优化")
    elif len(corrected) >= 1:
        print("⚠️ 上下文干预有一定效果，但需要更多优化")
    else:
        print("❌ 上下文干预无效，需要考虑其他方案")


if __name__ == '__main__':
    main()
