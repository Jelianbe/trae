# -*- coding: utf-8 -*-
"""完整 Pipeline 评估脚本（角色识别 + 情绪标注）

评估目标：
1. 角色识别准确率（speaker）
2. 情绪标注准确率（emotion_label）
3. 综合评估：系统能否完成文本分析工作
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pipeline_runner import PipelineRunner


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_speaker(speaker: str) -> str:
    """标准化角色名，便于比较"""
    if not speaker:
        return ""
    # 去除常见前缀
    speaker = speaker.replace("未知", "").strip()
    # 去除"角色"后缀
    if speaker.endswith("角色"):
        speaker = speaker[:-2]
    return speaker


def find_target_sentence(sentences, target_text: str):
    """在句子列表中找到目标句子"""
    target_text = target_text.strip()
    for s in sentences:
        if s.text.strip() == target_text:
            return s
        # 也尝试包含匹配
        if target_text in s.text:
            return s
    return None


def evaluate_pipeline(gt_data: list, runner: PipelineRunner):
    """评估完整 pipeline"""
    
    results = {
        'total': len(gt_data),
        'speaker_correct': 0,
        'emotion_correct': 0,
        'both_correct': 0,
        'errors': [],
        'by_style': defaultdict(lambda: {
            'speaker_correct': 0, 'emotion_correct': 0, 'total': 0
        }),
        'by_role_challenge': defaultdict(lambda: {
            'speaker_correct': 0, 'total': 0
        }),
        'by_emotion_challenge': defaultdict(lambda: {
            'emotion_correct': 0, 'total': 0
        }),
        'speaker_confusion': defaultdict(lambda: defaultdict(int)),
        'emotion_confusion': defaultdict(lambda: defaultdict(int)),
    }
    
    for item in gt_data:
        item_id = item['id']
        text = item['text']
        context_before = item.get('context_before', '')
        context_after = item.get('context_after', '')
        style = item['style']
        
        gt_speaker = item['speaker']
        gt_emotion = item['emotion_label']
        
        role_challenge = item.get('role_challenge', 'unknown')
        emotion_challenge = item.get('emotion_challenge', 'unknown')
        
        # 构造完整文本
        full_text = f"{context_before}\n{text}\n{context_after}"
        
        try:
            # 调用 pipeline
            chapter_results = runner.analyze_chapters(full_text, force=True)
            
            # 提取所有句子
            all_sentences = []
            for cr in chapter_results:
                all_sentences.extend(cr.sentences)
            
            # 找到目标句子
            target_sentence = find_target_sentence(all_sentences, text)
            
            if target_sentence:
                pred_speaker = target_sentence.speaker
                pred_emotion = target_sentence.emotion
            else:
                # 找不到目标句子，使用默认值
                pred_speaker = ""
                pred_emotion = "neutral"
                print(f"警告: {item_id} 找不到目标句子: {text[:30]}")
            
        except Exception as e:
            print(f"错误: {item_id} pipeline 执行失败: {e}")
            pred_speaker = ""
            pred_emotion = "neutral"
        
        # 标准化角色名
        gt_speaker_norm = normalize_speaker(gt_speaker)
        pred_speaker_norm = normalize_speaker(pred_speaker)
        
        # 统计
        results['by_style'][style]['total'] += 1
        results['by_role_challenge'][role_challenge]['total'] += 1
        results['by_emotion_challenge'][emotion_challenge]['total'] += 1
        
        speaker_ok = (gt_speaker_norm == pred_speaker_norm) or (not gt_speaker_norm and not pred_speaker_norm)
        emotion_ok = (gt_emotion == pred_emotion)
        
        if speaker_ok:
            results['speaker_correct'] += 1
            results['by_style'][style]['speaker_correct'] += 1
            results['by_role_challenge'][role_challenge]['speaker_correct'] += 1
        
        if emotion_ok:
            results['emotion_correct'] += 1
            results['by_style'][style]['emotion_correct'] += 1
            results['by_emotion_challenge'][emotion_challenge]['emotion_correct'] += 1
        
        if speaker_ok and emotion_ok:
            results['both_correct'] += 1
        
        if not speaker_ok or not emotion_ok:
            results['errors'].append({
                'id': item_id,
                'text': text[:40],
                'gt_speaker': gt_speaker,
                'pred_speaker': pred_speaker,
                'gt_emotion': gt_emotion,
                'pred_emotion': pred_emotion,
                'style': style,
            })
        
        results['speaker_confusion'][gt_speaker][pred_speaker] += 1
        results['emotion_confusion'][gt_emotion][pred_emotion] += 1
    
    return results


def print_report(results: dict):
    """打印评估报告"""
    
    total = results['total']
    
    print("=" * 80)
    print("完整 Pipeline 评估报告")
    print("=" * 80)
    
    # 总体结果
    print(f"\n=== 总体结果 ===")
    print(f"测试样本数: {total}")
    print(f"角色识别正确: {results['speaker_correct']} ({results['speaker_correct']/total:.1%})")
    print(f"情绪标注正确: {results['emotion_correct']} ({results['emotion_correct']/total:.1%})")
    print(f"两者都正确: {results['both_correct']} ({results['both_correct']/total:.1%})")
    
    # 按文体统计
    print(f"\n=== 按文体统计 ===")
    print(f"{'文体':<8} {'角色准确率':<15} {'情绪准确率':<15} {'总数':<6}")
    print("-" * 50)
    for style, stats in sorted(results['by_style'].items()):
        s_acc = stats['speaker_correct'] / stats['total'] if stats['total'] > 0 else 0
        e_acc = stats['emotion_correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"{style:<8} {s_acc:.1%}            {e_acc:.1%}            {stats['total']}")
    
    # 角色识别挑战类型
    print(f"\n=== 角色识别挑战类型 ===")
    challenges = sorted(results['by_role_challenge'].items(), key=lambda x: x[1]['total'], reverse=True)
    for challenge, stats in challenges[:8]:
        acc = stats['speaker_correct'] / stats['total'] if stats['total'] > 0 else 0
        challenge_short = challenge[:50] + '...' if len(challenge) > 50 else challenge
        print(f"{challenge_short:<55} {stats['speaker_correct']:>2}/{stats['total']:<2} {acc:.0%}")
    
    # 情绪标注挑战类型
    print(f"\n=== 情绪标注挑战类型 ===")
    challenges = sorted(results['by_emotion_challenge'].items(), key=lambda x: x[1]['total'], reverse=True)
    for challenge, stats in challenges[:8]:
        acc = stats['emotion_correct'] / stats['total'] if stats['total'] > 0 else 0
        challenge_short = challenge[:50] + '...' if len(challenge) > 50 else challenge
        print(f"{challenge_short:<55} {stats['emotion_correct']:>2}/{stats['total']:<2} {acc:.0%}")
    
    # 错误案例
    if results['errors']:
        print(f"\n=== 错误案例（前15条）===")
        for e in results['errors'][:15]:
            speaker_mark = "✓" if e['gt_speaker'] == e['pred_speaker'] else "✗"
            emotion_mark = "✓" if e['gt_emotion'] == e['pred_emotion'] else "✗"
            print(f"{e['id']}: 角色{speaker_mark} 情绪{emotion_mark} | {e['text'][:25]}")
            if e['gt_speaker'] != e['pred_speaker']:
                print(f"       角色: GT={e['gt_speaker']} Pred={e['pred_speaker']}")
            if e['gt_emotion'] != e['pred_emotion']:
                print(f"       情绪: GT={e['gt_emotion']} Pred={e['pred_emotion']}")


def main():
    gt_path = Path(__file__).parent.parent / 'tests' / 'role_emotion_gt_50.json'
    if not gt_path.exists():
        print(f"错误: 测试数据不存在 - {gt_path}")
        return
    
    gt_data = load_gt(gt_path)
    print(f"加载测试数据: {len(gt_data)} 条\n")
    
    # 创建 pipeline runner
    runner = PipelineRunner()
    
    # 评估
    results = evaluate_pipeline(gt_data, runner)
    
    # 打印报告
    print_report(results)
    
    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    
    total = results['total']
    speaker_acc = results['speaker_correct'] / total
    emotion_acc = results['emotion_correct'] / total
    both_acc = results['both_correct'] / total
    
    print(f"角色识别准确率: {speaker_acc:.1%}")
    print(f"情绪标注准确率: {emotion_acc:.1%}")
    print(f"综合准确率（两者都对）: {both_acc:.1%}")
    
    print("\n系统评估:")
    if both_acc >= 0.5:
        print("✅ 系统能够完成基本的文本分析工作")
    elif both_acc >= 0.3:
        print("⚠️ 系统能完成部分工作，但需要优化")
    else:
        print("❌ 系统当前状态不足以完成文本分析工作")
    
    print("\n模块评估:")
    if speaker_acc >= 0.5:
        print(f"  角色识别: {speaker_acc:.1%} ✅")
    else:
        print(f"  角色识别: {speaker_acc:.1%} ❌ 需要优化")
    
    if emotion_acc >= 0.5:
        print(f"  情绪标注: {emotion_acc:.1%} ✅")
    else:
        print(f"  情绪标注: {emotion_acc:.1%} ❌ 需要优化")


if __name__ == '__main__':
    main()
