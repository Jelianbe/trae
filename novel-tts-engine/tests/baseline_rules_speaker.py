# -*- coding: utf-8 -*-
"""规则系统说话人识别基线测试

使用 SpeakerMatcher (LegacyRuleMatcher) 在 100 条测试集上评估，
排除 speaker 为"未知"的条目（与 LLM benchmark 筛选一致），
拿真实基线数字，不依赖文档声称值。
"""
import sys
import json
import re
import os
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.character_manager import get_character_manager
from pipeline.legacy_rule_matcher import LegacyRuleMatcher
from pipeline.speaker_matcher_interface import DialogueContext


def filter_items(gt_data: list) -> list:
    """筛选出 speaker 非"未知"的条目，与 LLM benchmark 保持一致。"""
    filtered = []
    for item in gt_data:
        speaker = item.get('speaker', '')
        if speaker.startswith('未知'):
            continue
        if '/' in speaker:
            item = dict(item)
            item['speaker'] = speaker.split('/')[0]
        filtered.append(item)
    return filtered


def main():
    import sys
    # 支持命令行参数选择数据集
    dataset = sys.argv[1] if len(sys.argv) > 1 else 'role_emotion_gt_300.json'
    gt_path = project_root / "tests" / dataset
    print(f"使用数据集: {dataset}")
    print()
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    filtered = filter_items(gt_data)
    print(f"原始数据集: {len(gt_data)} 条")
    print(f"筛选后数据集: {len(filtered)} 条")
    print()

    cm = get_character_manager()
    sm = LegacyRuleMatcher(cm)
    project_id = "baseline_rules"
    sm.current_project_id = project_id

    # 预注册所有角色到 CM（让规则系统能找到）
    for item in filtered:
        ctx = (item.get('context_before', '') or '')[:100] + \
              (item.get('context_after', '') or '')[:100]
        sm.char_manager.find_or_create(
            item['speaker'],
            project_id=project_id,
            context=ctx,
        )

    results = []
    correct_count = 0
    style_stats = {}
    difficulty_stats = {}

    for i, item in enumerate(filtered):
        gt_speaker = item['speaker']
        text = item['text']
        style = item.get('style', '未知')
        context_before = item.get('context_before', '') or ''
        context_after = item.get('context_after', '') or ''
        role_challenge = item.get('role_challenge', '')

        # 构造 DialogueContext
        ctx = DialogueContext(
            text=text,
            context_before=context_before,
            context_after=context_after,
            chapter_id=1,
            speaker_hint=None,
            prev_speaker=None,
            mentioned_characters=[],
        )

        # 规则系统匹配
        result = sm.match_speaker(ctx)
        pred_speaker = result.character.name if result else None

        is_correct = (pred_speaker == gt_speaker) if pred_speaker else False
        if is_correct:
            correct_count += 1

        # 文体统计
        if style not in style_stats:
            style_stats[style] = {'correct': 0, 'total': 0}
        style_stats[style]['total'] += 1
        if is_correct:
            style_stats[style]['correct'] += 1

        # 难度统计
        if '代词消解' in role_challenge:
            diff_key = '代词消解'
        elif '显式提示' in role_challenge:
            diff_key = '显式提示'
        elif '别名' in role_challenge or '映射' in role_challenge:
            diff_key = '别名映射'
        else:
            diff_key = '其他'

        if diff_key not in difficulty_stats:
            difficulty_stats[diff_key] = {'correct': 0, 'total': 0}
        difficulty_stats[diff_key]['total'] += 1
        if is_correct:
            difficulty_stats[diff_key]['correct'] += 1

        match = "[OK]" if is_correct else "[XX]"
        print(f"  [{i+1:3d}/{len(filtered)}] {text[:20]:<20} GT={gt_speaker:<12} pred={pred_speaker or 'None':<12} {match}")

        results.append({
            "id": item['id'],
            "text": text,
            "style": style,
            "gt_speaker": gt_speaker,
            "pred_speaker": pred_speaker,
            "correct": is_correct,
        })

    accuracy = correct_count / len(filtered) if filtered else 0

    print()
    print("=" * 60)
    print("规则系统说话人识别基线")
    print("=" * 60)
    print(f"测试条目数: {len(filtered)}")
    print(f"正确数: {correct_count}")
    print(f"错误数: {len(filtered) - correct_count}")
    print(f"准确率: {accuracy:.1%}")
    print()

    print("按文体细分:")
    for style, stats in sorted(style_stats.items()):
        sa = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {style:<6}: {stats['correct']:>3}/{stats['total']:>3} = {sa:.1%}")
    print()

    print("按难度细分:")
    for diff, stats in sorted(difficulty_stats.items()):
        da = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {diff:<6}: {stats['correct']:>3}/{stats['total']:>3} = {da:.1%}")
    print()

    errors = [r for r in results if not r['correct']]
    print(f"错误 case ({len(errors)}):")
    for e in errors:
        print(f"  [{e['id']}] {e['text'][:25]:<25} GT={e['gt_speaker']:<12} pred={e['pred_speaker']}")

    # 保存结果
    result_path = project_root / "tests" / "baseline_rules_speaker_result.json"
    output = {
        "system": "LegacyRuleMatcher (SpeakerMatcher)",
        "total_items": len(filtered),
        "correct_count": correct_count,
        "error_count": len(filtered) - correct_count,
        "accuracy": round(accuracy, 3),
        "style_breakdown": {
            s: {
                "correct": v['correct'],
                "total": v['total'],
                "accuracy": round(v['correct'] / v['total'], 3) if v['total'] > 0 else 0
            }
            for s, v in style_stats.items()
        },
        "difficulty_breakdown": {
            d: {
                "correct": v['correct'],
                "total": v['total'],
                "accuracy": round(v['correct'] / v['total'], 3) if v['total'] > 0 else 0
            }
            for d, v in difficulty_stats.items()
        },
    }

    # P2-4: 基准锁定机制
    # 对比上次结果，如果准确率下降则告警
    if os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            prev_result = json.load(f)
        prev_accuracy = prev_result.get('accuracy', 0)
        if accuracy < prev_accuracy:
            print(f"\n{'='*60}")
            print(f"[WARN] P2-4 基准锁定告警：准确率下降！")
            print(f"   上次: {prev_accuracy:.1%} -> 本次: {accuracy:.1%}")
            print(f"   下降: {prev_accuracy - accuracy:.1%}")
            print(f"{'='*60}")
        else:
            print(f"\n[OK] P2-4 基准检查通过：{accuracy:.1%} >= {prev_accuracy:.1%}")

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print(f"结果已保存到: {result_path}")


if __name__ == "__main__":
    main()
