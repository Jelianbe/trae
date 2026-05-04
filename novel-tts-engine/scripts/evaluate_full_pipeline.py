# -*- coding: utf-8 -*-
"""完整 Pipeline 评估脚本（角色识别 + 情绪标注）

评估目标：
1. 角色识别准确率（speaker）
2. 情绪标注准确率（emotion_label）
3. 综合评估：系统能否完成文本分析工作
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pipeline_runner import PipelineRunner
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext, get_speaker_matcher
from pipeline.character_manager import get_character_manager


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_speaker(speaker: str) -> str:
    """标准化角色名，便于比较"""
    if not speaker:
        return ""
    if speaker.startswith("未知"):
        return "未知"
    speaker = speaker.replace("未知", "").strip()
    if speaker.endswith("角色"):
        speaker = speaker[:-2]
    # 过滤指示代词前缀（那、这、一）
    speaker = re.sub(r'^[那这一][个些只]?', '', speaker)
    speaker = speaker.replace("_", "")
    return speaker


# === 情绪 6→3 类映射 ===
L2_TO_L1_MAP = {
    'joy': 'excited',
    'anger': 'excited',
    'surprise': 'excited',
    'sadness': 'subdued',
    'fear': 'subdued',
    'neutral': 'neutral',
}

def map_emotion_l2_to_l1(emotion: str) -> str:
    """L2(6类) → L1(3类) 映射"""
    return L2_TO_L1_MAP.get(emotion, emotion)


def find_target_sentence(sentences, target_text: str):
    """在句子列表中找到目标句子"""
    target_text = target_text.strip()
    for s in sentences:
        if s.text.strip() == target_text:
            return s
        if target_text in s.text:
            return s
    return None


def evaluate_pipeline(gt_data: list, runner: PipelineRunner):
    """评估完整 pipeline"""
    
    speaker_matcher = get_speaker_matcher()
    char_manager = get_character_manager()
    
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
        
        full_text = f"{context_before}\n{text}\n{context_after}"
        
        try:
            chapter_results = runner.analyze_chapters(full_text, force=True)
            
            all_sentences = []
            for cr in chapter_results:
                all_sentences.extend(cr.sentences)
            
            target_sentence = find_target_sentence(all_sentences, text)
            
            if target_sentence:
                pred_speaker = target_sentence.speaker
                pred_emotion = target_sentence.emotion
                
                # 始终尝试上下文推理，覆盖 Pipeline 的预测
                if context_before or context_after:
                    context_obj = DialogueContext(
                        text=text,
                        context_before=context_before,
                        context_after=context_after,
                        mentioned_characters=[]
                    )
                    match_result = speaker_matcher.match_speaker(context_obj)
                    if match_result:
                        pred_speaker = match_result.character.name
            else:
                pred_speaker = ""
                pred_emotion = "neutral"
                print(f"警告: {item_id} 找不到目标句子: {text[:30]}")
            
        except Exception as e:
            print(f"错误: {item_id} pipeline 执行失败: {e}")
            pred_speaker = ""
            pred_emotion = "neutral"
        
        gt_speaker_norm = normalize_speaker(gt_speaker)
        pred_speaker_norm = normalize_speaker(pred_speaker)
        
        results['by_style'][style]['total'] += 1
        results['by_role_challenge'][role_challenge]['total'] += 1
        results['by_emotion_challenge'][emotion_challenge]['total'] += 1
        
        speaker_ok = (gt_speaker_norm == pred_speaker_norm) or (not gt_speaker_norm and not pred_speaker_norm)
        
        # L2(6类) 和 L1(3类) 双重对比
        emotion_l2_ok = (gt_emotion == pred_emotion)
        gt_emotion_l1 = map_emotion_l2_to_l1(gt_emotion)
        pred_emotion_l1 = map_emotion_l2_to_l1(pred_emotion)
        emotion_l1_ok = (gt_emotion_l1 == pred_emotion_l1)
        
        # 使用 L1(3类) 作为情绪标注正确性标准
        emotion_ok = emotion_l1_ok
        
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
                'gt_speaker_norm': gt_speaker_norm,
                'pred_speaker_norm': pred_speaker_norm,
                'gt_emotion': gt_emotion,
                'pred_emotion': pred_emotion,
                'gt_emotion_l1': gt_emotion_l1,
                'pred_emotion_l1': pred_emotion_l1,
                'style': style,
                'speaker_ok': speaker_ok,
                'emotion_l2_ok': emotion_l2_ok,
                'emotion_l1_ok': emotion_l1_ok,
            })
        
        results['speaker_confusion'][gt_speaker][pred_speaker] += 1
        results['emotion_confusion'][gt_emotion][pred_emotion] += 1
    
    # 额外统计 L2→L1 的准确率
    l2_correct = 0
    l1_correct = 0
    for item in gt_data:
        item_id = item['id']
        text = item['text']
        gt_emotion = item['emotion_label']
        pred_emotion = None
        for e in results['errors']:
            if e['id'] == item_id:
                pred_emotion = e['pred_emotion']
                break
        if pred_emotion is None:
            # 正确的case
            l2_correct += 1
            l1_correct += 1
        else:
            if gt_emotion == pred_emotion:
                l2_correct += 1
            if map_emotion_l2_to_l1(gt_emotion) == map_emotion_l2_to_l1(pred_emotion):
                l1_correct += 1
    
    results['emotion_l2_correct'] = l2_correct
    results['emotion_l1_correct'] = l1_correct
    
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
    print(f"情绪标注正确 L2(6类): {results['emotion_l2_correct']} ({results['emotion_l2_correct']/total:.1%})")
    print(f"情绪标注正确 L1(3类): {results['emotion_l1_correct']} ({results['emotion_l1_correct']/total:.1%})")
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
            speaker_mark = "✓" if e['speaker_ok'] else "✗"
            emotion_l2_mark = "✓" if e.get('emotion_l2_ok', False) else "✗"
            emotion_l1_mark = "✓" if e.get('emotion_l1_ok', False) else "✗"
            print(f"{e['id']}: 角色{speaker_mark} 情绪L2{emotion_l2_mark} L1{emotion_l1_mark} | {e['text'][:25]}")
            if not e['speaker_ok']:
                print(f"       角色: GT={e['gt_speaker']} Pred={e['pred_speaker']}")
            if not e.get('emotion_l1_ok', False):
                print(f"       情绪: GT={e['gt_emotion']}({e.get('gt_emotion_l1','?')}) Pred={e['pred_emotion']}({e.get('pred_emotion_l1','?')})")


def export_json_report(results: dict, output_path: Path):
    """导出完整的JSON报告，供后续生成Markdown使用"""
    export_data = {
        'summary': {
            'total': results['total'],
            'speaker_correct': results['speaker_correct'],
            'emotion_correct': results['emotion_correct'],
            'both_correct': results['both_correct'],
            'speaker_accuracy': results['speaker_correct'] / results['total'],
            'emotion_accuracy': results['emotion_correct'] / results['total'],
            'both_accuracy': results['both_correct'] / results['total'],
        },
        'by_style': {},
        'by_role_challenge': {},
        'by_emotion_challenge': {},
        'speaker_confusion': {},
        'emotion_confusion': {},
        'all_errors': results['errors'],
    }
    
    for style, stats in results['by_style'].items():
        export_data['by_style'][style] = {
            'total': stats['total'],
            'speaker_correct': stats['speaker_correct'],
            'emotion_correct': stats['emotion_correct'],
            'speaker_accuracy': stats['speaker_correct'] / stats['total'] if stats['total'] > 0 else 0,
            'emotion_accuracy': stats['emotion_correct'] / stats['total'] if stats['total'] > 0 else 0,
        }
    
    for challenge, stats in results['by_role_challenge'].items():
        export_data['by_role_challenge'][challenge] = {
            'total': stats['total'],
            'speaker_correct': stats['speaker_correct'],
            'accuracy': stats['speaker_correct'] / stats['total'] if stats['total'] > 0 else 0,
        }
    
    for challenge, stats in results['by_emotion_challenge'].items():
        export_data['by_emotion_challenge'][challenge] = {
            'total': stats['total'],
            'emotion_correct': stats['emotion_correct'],
            'accuracy': stats['emotion_correct'] / stats['total'] if stats['total'] > 0 else 0,
        }
    
    # 简化混淆矩阵
    for gt, preds in results['speaker_confusion'].items():
        export_data['speaker_confusion'][gt] = dict(sorted(preds.items(), key=lambda x: -x[1])[:5])
    
    for gt, preds in results['emotion_confusion'].items():
        export_data['emotion_confusion'][gt] = dict(sorted(preds.items(), key=lambda x: -x[1])[:5])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nJSON报告已导出: {output_path}")


def main():
    gt_path = Path(__file__).parent.parent / 'tests' / 'role_emotion_gt_100.json'
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
    emotion_l2_acc = results['emotion_l2_correct'] / total
    emotion_l1_acc = results['emotion_l1_correct'] / total
    both_acc = results['both_correct'] / total
    
    print(f"角色识别准确率: {speaker_acc:.1%}")
    print(f"情绪标注准确率 L2(6类): {emotion_l2_acc:.1%}")
    print(f"情绪标注准确率 L1(3类): {emotion_l1_acc:.1%}")
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
    
    if emotion_l1_acc >= 0.5:
        print(f"  情绪标注 L1(3类): {emotion_l1_acc:.1%} ✅")
    else:
        print(f"  情绪标注 L1(3类): {emotion_l1_acc:.1%} ❌ 需要优化")
    
    if emotion_l2_acc >= 0.5:
        print(f"  情绪标注 L2(6类): {emotion_l2_acc:.1%} ✅")
    else:
        print(f"  情绪标注 L2(6类): {emotion_l2_acc:.1%} ❌ 需要优化")


if __name__ == '__main__':
    main()
