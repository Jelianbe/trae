"""无预注册角色场景测试

不向角色库预注册任何角色，测试系统的自动发现能力。

用法: python tests/test_no_registration.py
"""

import json
import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


def parse_text_file(text_path: str):
    """解析测试文本文件，提取对话段落。"""
    with open(text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]
    
    dialogues = []
    for idx, (line_num, text) in enumerate(non_empty):
        if '"' in text or "'" in text or '""' in text or "''" in text:
            match = re.search(r'["""](.+?)["""]', text)
            if match:
                dialogue_content = match.group(1)
                prefix_narration = ''
                prefix = text[:match.start()]
                if prefix:
                    prefix_narration = prefix.strip()
                context_before = ''
                if idx > 0:
                    context_before = non_empty[idx-1][1]
                context_after = ''
                if idx < len(non_empty) - 1:
                    context_after = non_empty[idx+1][1]
                dialogues.append({
                    'text': text,
                    'context_before': context_before,
                    'context_after': context_after,
                    'prefix_narration': prefix_narration,
                })
    return dialogues


def run_no_registration(text_path: str, answer_path: str, title: str = "", relaxed: bool = False):
    """运行无预注册测试"""
    with open(answer_path, 'r', encoding='utf-8') as f:
        answer_key = json.load(f)
    
    char_manager = CharacterManager()
    # 注意：不预注册任何角色！
    
    matcher = SpeakerMatcher()
    matcher.char_manager = char_manager
    matcher._current_project_id = 'no_reg_test'
    
    dialogues = parse_text_file(str(text_path))
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"解析到 {len(dialogues)} 条对话")
    print(f"答案文件有 {len(answer_key['dialogues'])} 条答案")
    print(f"角色库角色数: {len(char_manager.get_eligible_characters('no_reg_test'))}")
    print(f"评估模式: {'宽松 (v2)' if relaxed else '严格 (v1)'}")
    print()
    
    if relaxed:
        from tests.eval_utils import is_relaxed_correct_with_context, is_relaxed_correct, normalize_for_eval
    
    correct = 0
    wrong = 0
    unknown = 0
    results = []
    
    for i, dialogue in enumerate(dialogues):
        if i >= len(answer_key['dialogues']):
            break
        
        expected = answer_key['dialogues'][i]
        expected_speaker = expected if isinstance(expected, str) else expected['speaker']
        
        context = DialogueContext(
            text=dialogue['text'],
            context_before=dialogue['context_before'],
            context_after=dialogue['context_after'],
            prefix_narration=dialogue.get('prefix_narration', '')
        )
        
        result = matcher.match_speaker(context)
        
        if result and result.character:
            predicted = result.character.name
            match_type = result.match_type
            confidence = result.confidence
            matcher.update_activity(result.character.id, predicted)
        else:
            predicted = 'UNKNOWN'
            match_type = 'none'
            confidence = 0.0
        
        # 判定逻辑
        if relaxed:
            prev_pred = results[-1]['predicted'] if results else None
            prev_exp = answer_key['dialogues'][i-1] if i > 0 else None
            if isinstance(prev_exp, dict):
                prev_exp = prev_exp['speaker']
            has_prefix = bool(dialogue.get('prefix_narration', '').strip())
            is_correct = is_relaxed_correct_with_context(
                predicted, expected_speaker,
                prev_predicted=prev_pred,
                prev_expected=prev_exp,
                is_continuation=not has_prefix,
            )
            # 但 "未知" 仍然判错
            if predicted == 'UNKNOWN':
                is_correct = False
        else:
            is_correct = (predicted == expected_speaker) or (expected_speaker == 'UNKNOWN' and predicted == 'UNKNOWN')
        
        if expected_speaker == 'UNKNOWN':
            unknown += 1
            status = 'SKIP'
        elif is_correct:
            correct += 1
            status = 'OK'
        else:
            wrong += 1
            status = 'WRONG'
        
        if status != 'SKIP':
            prefix = f"[{status:5s}] "
            if status == 'WRONG':
                display_predicted = predicted
                if relaxed:
                    display_predicted = f"{predicted} → {normalize_for_eval(predicted)}" if normalize_for_eval(predicted) != predicted else predicted
                print(f"{prefix}#{i+1:3d} 期望={expected_speaker}, 预测={display_predicted} (方法={match_type}, 置信度={confidence:.2f})")
            else:
                display_predicted = predicted
                if relaxed:
                    norm = normalize_for_eval(predicted)
                    if norm != predicted:
                        display_predicted = f"{predicted} (= {norm})"
                print(f"{prefix}#{i+1:3d} 期望={expected_speaker}, 预测={display_predicted}")
        
        results.append({
            'index': i + 1,
            'text': dialogue['text'],
            'expected': expected_speaker,
            'predicted': predicted,
            'match_type': match_type,
            'confidence': confidence,
            'is_correct': is_correct,
        })
    
    judgable = correct + wrong
    accuracy = correct / judgable if judgable > 0 else 0.0
    
    print()
    print(f"总计: {len(dialogues)} 条对话")
    print(f"可判断: {judgable} 条")
    print(f"正确: {correct} 条")
    print(f"错误: {wrong} 条")
    print(f"跳过(非角色库人物): {unknown} 条")
    print(f"准确率: {accuracy*100:.1f}%")
    
    return {
        'title': title,
        'relaxed': relaxed,
        'total': len(dialogues),
        'judgable': judgable,
        'correct': correct,
        'wrong': wrong,
        'unknown': unknown,
        'accuracy': accuracy,
        'results': results,
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='无预注册角色场景测试')
    parser.add_argument('--relaxed', action='store_true', help='使用宽松模式（v2）评估：命名变体算对、连续对话继承算对')
    args = parser.parse_args()
    
    # 都市职场测试
    urban_text = project_root / 'tests' / 'urban_long_text_test.txt'
    urban_answer = project_root / 'tests' / 'urban_long_text_answer_key.json'
    urban_result = run_no_registration(urban_text, urban_answer, "都市职场 - 无预注册", relaxed=args.relaxed)
    
    # 西幻测试
    fantasy_text = project_root / 'tests' / 'fantasy_long_text_test.txt'
    fantasy_answer = project_root / 'tests' / 'fantasy_long_text_answer_key.json'
    fantasy_result = run_no_registration(fantasy_text, fantasy_answer, "西幻 - 无预注册", relaxed=args.relaxed)
    
    # 保存结果
    suffix = '_relaxed' if args.relaxed else ''
    result_path = project_root / 'tests' / f'no_registration_result{suffix}.json'
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump({
            'urban': urban_result,
            'fantasy': fantasy_result,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存至: {result_path}")
