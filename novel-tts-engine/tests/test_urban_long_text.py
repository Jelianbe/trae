"""都市长文本基线测试

读取 urban_long_text_test.txt，按段落解析对话，
调用说话人匹配器，与 answer_key.json 对比。

支持两种运行方式：
1. pytest: pytest tests/test_urban_long_text.py -v（使用隔离数据库）
2. 独立运行: python tests/test_urban_long_text.py（使用生产库，仅用于基线跑数）

R-022 架构重构（2026-05-16）：
- 添加 pytest 格式测试类，使用 conftest.py 提供的临时数据库 fixture
- 保留原有 main() 函数用于基线跑数场景
"""

import json
import re
import sys
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


def parse_text_file(text_path: str):
    """解析测试文本文件，提取对话段落。
    
    返回: [(dialogue_text, context_before, context_after, ...), ...]
    """
    with open(text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 去空行
    non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]
    
    dialogues = []
    for idx, (line_num, text) in enumerate(non_empty):
        # 判断是否是对话（包含引号）
        if '"' in text or "'" in text or '""' in text or "''" in text:
            # 提取引号内的内容
            match = re.search(r'["""](.+?)["""]', text)
            if match:
                dialogue_content = match.group(1)

                # 提取引号前旁白前缀（H-20260516-10）
                # 格式：赵总监皱起眉头问道："谁批准的？" → prefix="赵总监皱起眉头问道"
                prefix_narration = ''
                colon_idx = text.find('：')
                quote_idx = text.find('"')
                if quote_idx == -1:
                    quote_idx = text.find("'")
                if colon_idx >= 0 and quote_idx >= 0 and colon_idx < quote_idx:
                    prefix_narration = text[:colon_idx].strip()

                # 复合行处理（H-20260516-10）
                # 格式："对话1"张总侧过身，"对话2" → between="张总侧过身"
                all_quotes = list(re.finditer(r'["""](.+?)["""]', text))
                if len(all_quotes) >= 2:
                    between = text[all_quotes[0].end():all_quotes[1].start()]
                    if between.strip():
                        prefix_narration = between.strip()
                
                # 前文：前面所有非空行，取最近 3 行
                # H-20260516-11: 含引号的行保留但引号内容替换为 [对话]
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
                
                # 后文：后面 2 行非空行
                # H-20260516-11: 同上
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
                    'has_prefix': bool(prefix_narration)  # H-20260516-11: 标记是否有旁白
                })
    
    return dialogues


def setup_characters(char_manager: CharacterManager):
    """设置测试角色"""
    chars = [
        {"name": "赵总监", "aliases": ["赵总"], "id": 1},
        {"name": "李经理", "aliases": [], "id": 2},
        {"name": "吴工程师", "aliases": ["吴工"], "id": 3},
        {"name": "孙工", "aliases": [], "id": 4},
        {"name": "刘秘书", "aliases": [], "id": 5},
        {"name": "张总", "aliases": [], "id": 6}
    ]
    for char in chars:
        char_manager.add_character(
            name=char['name'],
            aliases=set(char['aliases']),
            project_id='test_project'
        )


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='都市长文本基线测试')
    parser.add_argument('--relaxed', action='store_true', help='使用宽松模式（v2）评估')
    args = parser.parse_args()
    
    relaxed = args.relaxed
    if relaxed:
        from tests.eval_utils import is_relaxed_correct_with_context, normalize_for_eval
    
    text_path = project_root / 'tests' / 'urban_long_text_test.txt'
    answer_path = project_root / 'tests' / 'urban_long_text_answer_key.json'
    result_path = project_root / 'tests' / 'urban_long_text_baseline_result.json'
    
    # 加载答案
    with open(answer_path, 'r', encoding='utf-8') as f:
        answer_key = json.load(f)
    
    # 初始化匹配器
    char_manager = CharacterManager()
    setup_characters(char_manager)
    matcher = SpeakerMatcher()
    matcher.char_manager = char_manager
    matcher._current_project_id = 'test_project'
    
    # 解析文本
    dialogues = parse_text_file(str(text_path))
    print(f"解析到 {len(dialogues)} 条对话")
    print(f"答案文件有 {len(answer_key['dialogues'])} 条答案")
    print(f"评估模式: {'宽松 (v2)' if relaxed else '严格 (v1)'}")
    print()
    
    # 运行匹配
    correct = 0
    wrong = 0
    unknown = 0
    results = []
    
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
            # P2-2: 更新最近说话人列表（模拟真实对话流）
            matcher.update_activity(result.character.id, predicted)
        else:
            predicted = 'UNKNOWN'
            match_type = 'none'
            confidence = 0.0
        
        expected_speaker = expected['speaker']
        
        if relaxed:
            prev_pred = results[-1]['predicted'] if results else None
            prev_exp = answer_key['dialogues'][i-1]['speaker'] if i > 0 else None
            has_prefix = bool(dialogue.get('prefix_narration', '').strip())
            is_correct = is_relaxed_correct_with_context(
                predicted, expected_speaker,
                prev_predicted=prev_pred,
                prev_expected=prev_exp,
                is_continuation=not has_prefix,
            )
            if predicted == 'UNKNOWN':
                is_correct = False
        else:
            is_correct = (predicted == expected_speaker) or (expected_speaker == 'UNKNOWN' and predicted == 'UNKNOWN')
        
        if expected_speaker == 'UNKNOWN':
            # 非角色库人物，不判断对错
            unknown += 1
            status = 'SKIP'
        elif is_correct:
            correct += 1
            status = 'OK'
        else:
            wrong += 1
            status = 'WRONG'
        
        results.append({
            'index': i + 1,
            'text': dialogue['text'][:30],
            'expected': expected_speaker,
            'predicted': predicted,
            'match_type': match_type,
            'confidence': confidence,
            'status': status
        })
        
        if status == 'WRONG':
            display_predicted = predicted
            if relaxed:
                norm = normalize_for_eval(predicted)
                if norm != predicted:
                    display_predicted = f"{predicted} → {norm}"
            print(f"[{i+1:3d}] [X] 预期={expected_speaker}, 预测={display_predicted} ({match_type}, {confidence:.2f})")
            print(f"       原文: {dialogue['raw_line'][:60]}")
        elif status == 'OK':
            display_predicted = predicted
            if relaxed:
                norm = normalize_for_eval(predicted)
                if norm != predicted:
                    display_predicted = f"{predicted} (= {norm})"
            print(f"[{i+1:3d}] [OK] {display_predicted}")
    
    print(f"\n{'='*60}")
    print(f"基线测试结果")
    print(f"{'='*60}")
    print(f"总对话数: {len(dialogues)}")
    print(f"可判断数: {len(dialogues) - unknown}")
    print(f"正确: {correct}")
    print(f"错误: {wrong}")
    print(f"跳过(非角色库): {unknown}")
    print(f"准确率: {correct/(correct+wrong)*100:.1f}%" if (correct+wrong) > 0 else "N/A")
    
    # 保存结果
    result_data = {
        'total': len(dialogues),
        'judgable': len(dialogues) - unknown,
        'correct': correct,
        'wrong': wrong,
        'unknown': unknown,
        'accuracy': correct/(correct+wrong) if (correct+wrong) > 0 else 0,
        'relaxed': relaxed,
        'results': results
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到 {result_path}")


if __name__ == '__main__':
    main()


# ===== pytest 测试类（R-022 架构重构） =====

class TestUrbanLongText:
    """城市职场长文本测试：使用 conftest.py 提供的隔离数据库 fixture。
    
    运行方式：pytest tests/test_urban_long_text.py -v
    """

    def test_all_dialogues(self, char_manager):
        """运行全部城市职场长文本对话，验证说话人识别准确率。"""
        text_path = project_root / 'tests' / 'urban_long_text_test.txt'
        answer_path = project_root / 'tests' / 'urban_long_text_answer_key.json'
        
        with open(answer_path, 'r', encoding='utf-8') as f:
            answer_key = json.load(f)
        
        chars = [
            {"name": "赵总监", "aliases": ["赵总"]},
            {"name": "李经理", "aliases": []},
            {"name": "吴工程师", "aliases": ["吴工"]},
            {"name": "孙工", "aliases": []},
            {"name": "刘秘书", "aliases": []},
            {"name": "张总", "aliases": []}
        ]
        for char in chars:
            char_manager.add_character(
                name=char['name'],
                aliases=set(char['aliases']),
                project_id='test_project'
            )
        
        matcher = SpeakerMatcher()
        matcher.char_manager = char_manager
        matcher._current_project_id = 'test_project'
        
        dialogues = parse_text_file(str(text_path))
        
        correct = 0
        wrong = 0
        unknown = 0
        results = []
        
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
            
            expected_speaker = expected['speaker']
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
            
            results.append({
                'index': i + 1,
                'text': dialogue['text'][:30],
                'expected': expected_speaker,
                'predicted': predicted,
                'match_type': match_type,
                'confidence': confidence,
                'status': status
            })
            
            if status == 'WRONG':
                print(f"[{i+1:3d}] [X] 预期={expected_speaker}, 预测={predicted} ({match_type}, {confidence:.2f})")
                print(f"       原文: {dialogue['raw_line'][:60]}")
            elif status == 'OK':
                print(f"[{i+1:3d}] [OK] {predicted}")
        
        print(f"\n{'='*60}")
        print(f"基线测试结果")
        print(f"{'='*60}")
        print(f"总对话数: {len(dialogues)}")
        print(f"可判断数: {len(dialogues) - unknown}")
        print(f"正确: {correct}")
        print(f"错误: {wrong}")
        print(f"跳过(非角色库): {unknown}")
        accuracy = correct/(correct+wrong)*100 if (correct+wrong) > 0 else 0
        print(f"准确率: {accuracy:.1f}%")
        
        result_data = {
            'total': len(dialogues),
            'judgable': len(dialogues) - unknown,
            'correct': correct,
            'wrong': wrong,
            'unknown': unknown,
            'accuracy': correct/(correct+wrong) if (correct+wrong) > 0 else 0,
            'results': results
        }
        
        result_path = project_root / 'tests' / 'urban_long_text_baseline_result.json'
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到 {result_path}")
        
        assert accuracy >= 80.0, f"城市职场长文本准确率 {accuracy:.1f}% 低于 80% 基线阈值"
