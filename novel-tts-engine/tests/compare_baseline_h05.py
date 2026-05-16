# -*- coding: utf-8 -*-
"""对比H-05优化前后的短文本基线结果

找出：
1. 当前错误的case（59条）
2. H-05优化后变正确的case
3. H-05优化后变错误的case（回归）
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.character_manager import get_character_manager
from pipeline.legacy_rule_matcher import LegacyRuleMatcher
from pipeline.speaker_matcher_interface import DialogueContext


def filter_items(gt_data: list) -> list:
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


def run_baseline(gt_path, project_id):
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    filtered = filter_items(gt_data)
    
    cm = get_character_manager()
    sm = LegacyRuleMatcher(cm)
    sm.current_project_id = project_id
    
    for item in filtered:
        ctx = (item.get('context_before', '') or '')[:100] + \
              (item.get('context_after', '') or '')[:100]
        sm.char_manager.find_or_create(
            item['speaker'],
            project_id=project_id,
            context=ctx,
        )
    
    results = {}
    for i, item in enumerate(filtered):
        ctx = DialogueContext(
            text=item['text'],
            context_before=item.get('context_before', '') or '',
            context_after=item.get('context_after', '') or '',
            chapter_id=1,
            speaker_hint=None,
            prev_speaker=None,
            mentioned_characters=[],
        )
        result = sm.match_speaker(ctx)
        pred_speaker = result.character.name if result else None
        results[item['id']] = {
            'text': item['text'],
            'style': item.get('style', ''),
            'gt_speaker': item['speaker'],
            'pred_speaker': pred_speaker,
            'role_challenge': item.get('role_challenge', ''),
            'context_before': item.get('context_before', ''),
            'context_after': item.get('context_after', ''),
            'correct': (pred_speaker == item['speaker']) if pred_speaker else False,
        }
    
    return results


def main():
    gt_path = project_root / "tests" / "role_emotion_gt_300.json"
    
    # 当前结果（H-05后）
    print("运行当前基线（H-05后）...")
    current_results = run_baseline(gt_path, "baseline_rules")
    
    # 加载上次保存的结果
    result_path = project_root / "tests" / "baseline_rules_speaker_result.json"
    
    # 分类
    correct = [r for r in current_results.values() if r['correct']]
    wrong = [r for r in current_results.values() if not r['correct']]
    
    print(f"\n总计: {len(current_results)} 条")
    print(f"正确: {len(correct)} 条")
    print(f"错误: {len(wrong)} 条")
    print(f"准确率: {len(correct)/len(current_results):.1%}")
    
    # 按文体分类错误
    style_errors = {}
    for r in wrong:
        style = r['style']
        if style not in style_errors:
            style_errors[style] = []
        style_errors[style].append(r)
    
    print("\n" + "="*60)
    print("按文体错误分布:")
    for style in sorted(style_errors.keys()):
        errs = style_errors[style]
        print(f"  {style}: {len(errs)}条错误")
    
    # 按role_challenge分类
    challenge_errors = {}
    for r in wrong:
        rc = r['role_challenge']
        if '代词' in rc:
            key = '代词消解'
        elif '显式' in rc:
            key = '显式提示'
        elif '别名' in rc or '映射' in rc or '头衔' in rc:
            key = '别名映射'
        else:
            key = '其他'
        if key not in challenge_errors:
            challenge_errors[key] = []
        challenge_errors[key].append(r)
    
    print("\n按难度分类错误:")
    for key in sorted(challenge_errors.keys()):
        errs = challenge_errors[key]
        print(f"  {key}: {len(errs)}条错误")
    
    # 输出所有错误case详情
    print("\n" + "="*60)
    print("错误案例详情:")
    print("="*60)
    
    for style in sorted(style_errors.keys()):
        err_count = len(style_errors[style])
        print(f"\n[{style}] ({err_count}条错误)")
        for i, r in enumerate(style_errors[style], 1):
            print(f"  {i}. GT={r['gt_speaker']:<12} pred={r['pred_speaker'] or 'None':<12}")
            print(f"     文本: {r['text']}")
            print(f"     前文: {r['context_before'][:60]}")
            rc_short = r['role_challenge'][:80]
            print(f"     挑战: {rc_short}")
            print()
    
    # 保存详细结果
    output = {
        "total": len(current_results),
        "correct_count": len(correct),
        "error_count": len(wrong),
        "accuracy": round(len(correct)/len(current_results), 3),
        "style_errors": {s: len(errs) for s, errs in style_errors.items()},
        "challenge_errors": {k: len(errs) for k, errs in challenge_errors.items()},
        "error_cases": [
            {
                "text": r['text'],
                "style": r['style'],
                "gt_speaker": r['gt_speaker'],
                "pred_speaker": r['pred_speaker'],
                "role_challenge": r['role_challenge'],
                "context_before": r['context_before'][:100],
                "context_after": r['context_after'][:100],
            }
            for r in wrong
        ]
    }
    
    detail_path = project_root / "tests" / "short_text_error_detail.json"
    with open(detail_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存至: {detail_path}")


if __name__ == "__main__":
    main()
