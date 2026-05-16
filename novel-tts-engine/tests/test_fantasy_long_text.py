"""Fantasy Long Text Speaker Recognition Baseline Test

支持两种运行方式：
1. pytest: pytest tests/test_fantasy_long_text.py -v（使用隔离数据库）
2. 独立运行: python tests/test_fantasy_long_text.py（使用生产库，仅用于基线跑数）

R-022 架构重构（2026-05-16）：
- 添加 pytest 格式测试类，使用 conftest.py 提供的临时数据库 fixture
- 保留原有 main() 函数用于基线跑数场景
"""
import sys, json, re, pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext, CharacterManager
from utils.config import DB_PATH

CHARACTERS = {
    '亚瑟': {'gender': 'male', 'aliases': {'亚瑟团长', '团长'}},
    '艾琳': {'gender': 'female', 'aliases': {'艾琳法师'}},
    '雷恩': {'gender': 'male', 'aliases': {'雷恩队长', '队长'}},
    '莉莉': {'gender': 'female', 'aliases': {'莉莉治疗师', '治疗师'}},
    '加文': {'gender': 'male', 'aliases': {'加文老战士', '老战士'}},
}

def setup_characters(char_manager: CharacterManager):
    for name, info in CHARACTERS.items():
        char_manager.add_character(
            name=name,
            project_id='fantasy_baseline',
            aliases=info['aliases'],
            gender=info['gender']
        )

def parse_text_file(file_path: str) -> list:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]
    
    dialogues = []
    for idx, (line_num, text) in enumerate(non_empty):
        match = re.search(r'["""](.+?)["""]', text)
        if match:
            dialogue_content = match.group(1)
            
            prefix_narration = ''
            colon_idx = text.find('\uff1a')
            quote_idx = text.find('"')
            if quote_idx == -1: quote_idx = text.find("'")
            if colon_idx >= 0 and quote_idx >= 0 and colon_idx < quote_idx:
                prefix_narration = text[:colon_idx].strip()
            
            all_quotes = list(re.finditer(r'["""](.+?)["""]', text))
            if len(all_quotes) >= 2:
                between = text[all_quotes[0].end():all_quotes[1].start()]
                if between.strip():
                    prefix_narration = between.strip()
            
            before_lines = []
            for prev_idx in range(idx-1, -1, -1):
                prev_line = non_empty[prev_idx][1]
                if prev_line:
                    cleaned = re.sub(r'["""](.+?)["""]', '[对话]', prev_line)
                    if cleaned.strip():
                        before_lines.append(cleaned)
                if len(before_lines) >= 3:
                    break
            before_lines.reverse()
            context_before = '。'.join(before_lines) + '。' if before_lines else ''
            
            after_lines = []
            for next_idx in range(idx+1, min(idx+5, len(non_empty))):
                next_line = non_empty[next_idx][1]
                if next_line:
                    cleaned = re.sub(r'["""](.+?)["""]', '[对话]', next_line)
                    if cleaned.strip():
                        after_lines.append(cleaned)
                if len(after_lines) >= 2:
                    break
            context_after = '。'.join(after_lines) + '。' if after_lines else ''
            
            dialogues.append({
                'text': dialogue_content,
                'context_before': context_before,
                'context_after': context_after,
                'raw_line': text,
                'prefix_narration': prefix_narration,
                'has_prefix': bool(prefix_narration)
            })
    
    return dialogues

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='西幻长文本基线测试')
    parser.add_argument('--relaxed', action='store_true', help='使用宽松模式（v2）评估')
    args = parser.parse_args()
    
    relaxed = args.relaxed
    if relaxed:
        from tests.eval_utils import is_relaxed_correct_with_context, normalize_for_eval
    
    test_file = project_root / 'tests' / 'fantasy_long_text_test.txt'
    answer_file = project_root / 'tests' / 'fantasy_long_text_answer_key.json'
    
    with open(str(answer_file), 'r', encoding='utf-8') as f:
        answer_key = json.load(f)
    
    dialogues = parse_text_file(str(test_file))
    
    char_manager = CharacterManager(DB_PATH)
    setup_characters(char_manager)
    matcher = SpeakerMatcher()
    matcher.char_manager = char_manager
    matcher._current_project_id = 'fantasy_baseline'
    
    total_dialogues = len(dialogues)
    results = []
    correct = 0
    wrong = 0
    unknown = 0
    
    print(f"评估模式: {'宽松 (v2)' if relaxed else '严格 (v1)'}")
    print()
    
    for i, dialogue in enumerate(dialogues):
        if i >= len(answer_key['dialogues']):
            break
        
        expected = answer_key['dialogues'][i]
        
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
        
        if expected == 'UNKNOWN':
            status = 'skip'
            unknown += 1
        elif relaxed:
            prev_pred = results[-1]['predicted'] if results else None
            prev_exp = answer_key['dialogues'][i-1] if i > 0 else None
            has_prefix = bool(dialogue.get('prefix_narration', '').strip())
            ok = is_relaxed_correct_with_context(
                predicted, expected,
                prev_predicted=prev_pred,
                prev_expected=prev_exp,
                is_continuation=not has_prefix,
            )
            if predicted == 'UNKNOWN':
                ok = False
            if ok:
                status = 'ok'
                correct += 1
            else:
                status = 'wrong'
                wrong += 1
        elif predicted == expected:
            status = 'ok'
            correct += 1
        elif predicted == 'UNKNOWN':
            status = 'unknown'
            unknown += 1
        else:
            status = 'wrong'
            wrong += 1
        
        results.append({
            'index': i + 1,
            'text': dialogue['text'][:50],
            'expected': expected,
            'predicted': predicted,
            'status': status,
            'match_type': match_type,
            'confidence': confidence,
            'prefix_narration': dialogue.get('prefix_narration', '')[:30]
        })
        
        display_predicted = predicted
        if relaxed:
            norm = normalize_for_eval(predicted)
            if norm != predicted:
                display_predicted = f"{predicted}(={norm})"
        
        if status == 'ok':
            mark = '✅'
        elif status == 'skip':
            mark = '⏭️'
        else:
            mark = '❌'
        print(f'[{mark}] [{i+1:2d}] {display_predicted:12s} (expected: {expected}) - {match_type[:30]} | {dialogue["text"][:30]}')
    
    judgable = total_dialogues - unknown
    accuracy = correct / judgable * 100 if judgable > 0 else 0
    
    print(f'\n{"="*60}')
    print(f'总对话数: {total_dialogues}')
    print(f'可判断数: {judgable}')
    print(f'正确: {correct}')
    print(f'错误: {wrong}')
    print(f'跳过(非角色库): {unknown}')
    print(f'准确率: {accuracy:.1f}%')
    
    output_file = project_root / 'tests' / 'fantasy_long_text_baseline_result.json'
    with open(str(output_file), 'w', encoding='utf-8') as f:
        json.dump({
            'total': total_dialogues,
            'correct': correct,
            'wrong': wrong,
            'unknown': unknown,
            'accuracy': accuracy,
            'relaxed': relaxed,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f'\n结果已保存到 {output_file}')

if __name__ == '__main__':
    main()


# ===== pytest 测试类（R-022 架构重构） =====

class TestFantasyLongText:
    """西幻长文本测试：使用 conftest.py 提供的隔离数据库 fixture。
    
    运行方式：pytest tests/test_fantasy_long_text.py -v
    """

    def test_all_dialogues(self, speaker_matcher, fantasy_characters):
        """运行全部西幻长文本对话，验证说话人识别准确率。"""
        test_file = project_root / 'tests' / 'fantasy_long_text_test.txt'
        answer_file = project_root / 'tests' / 'fantasy_long_text_answer_key.json'
        
        with open(str(answer_file), 'r', encoding='utf-8') as f:
            answer_key = json.load(f)
        
        dialogues = parse_text_file(str(test_file))
        
        results = []
        correct = 0
        wrong = 0
        unknown = 0
        
        for i, dialogue in enumerate(dialogues):
            if i >= len(answer_key['dialogues']):
                break
            
            expected = answer_key['dialogues'][i]
            
            context = DialogueContext(
                text=dialogue['text'],
                context_before=dialogue['context_before'],
                context_after=dialogue['context_after'],
                prefix_narration=dialogue.get('prefix_narration', '')
            )
            
            result = speaker_matcher.match_speaker(context)
            
            if result and result.character:
                predicted = result.character.name
                match_type = result.match_type
                confidence = result.confidence
                speaker_matcher.update_activity(result.character.id, predicted)
            else:
                predicted = 'UNKNOWN'
                match_type = 'none'
                confidence = 0.0
            
            if expected == 'UNKNOWN':
                status = 'skip'
                unknown += 1
            elif predicted == expected:
                status = 'ok'
                correct += 1
            elif predicted == 'UNKNOWN':
                status = 'unknown'
                unknown += 1
            else:
                status = 'wrong'
                wrong += 1
            
            results.append({
                'index': i + 1,
                'text': dialogue['text'][:50],
                'expected': expected,
                'predicted': predicted,
                'status': status,
                'match_type': match_type,
                'confidence': confidence,
                'prefix_narration': dialogue.get('prefix_narration', '')[:30]
            })
            
            mark = '[OK]' if status == 'ok' else ('[SKIP]' if status == 'skip' else '[FAIL]')
            print(f'{mark} [{i+1:2d}] {predicted:6s} (expected: {expected}) - {match_type[:30]} | {dialogue["text"][:30]}')
        
        judgable = len(dialogues) - unknown
        accuracy = correct / judgable * 100 if judgable > 0 else 0
        
        print(f'\n{"="*60}')
        print(f'总对话数: {len(dialogues)}')
        print(f'可判断数: {judgable}')
        print(f'正确: {correct}')
        print(f'错误: {wrong}')
        print(f'跳过(非角色库): {unknown}')
        print(f'准确率: {accuracy:.1f}%')
        
        output_file = project_root / 'tests' / 'fantasy_long_text_baseline_result.json'
        with open(str(output_file), 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(dialogues),
                'correct': correct,
                'wrong': wrong,
                'unknown': unknown,
                'accuracy': accuracy,
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f'\n结果已保存到 {output_file}')
        
        assert accuracy >= 50.0, f"西幻长文本准确率 {accuracy:.1f}% 低于 50% 基线阈值"
