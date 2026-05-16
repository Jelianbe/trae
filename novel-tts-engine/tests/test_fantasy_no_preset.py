"""西幻长文本测试 - 无预注册角色库模式

用于验证 SRL 角色发现在西幻文体中的效果。
不预注册任何角色，让系统动态发现角色。

运行方式: python tests/test_fantasy_no_preset.py
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

                # 提取引号前旁白前缀
                prefix_narration = ''
                colon_idx = text.find('：')
                quote_idx = text.find('"')
                if quote_idx == -1:
                    quote_idx = text.find("'")
                if colon_idx >= 0 and quote_idx >= 0 and colon_idx < quote_idx:
                    prefix_narration = text[:colon_idx].strip()

                # 复合行处理
                all_quotes = list(re.finditer(r'["""](.+?)["""]', text))
                if len(all_quotes) >= 2:
                    between = text[all_quotes[0].end():all_quotes[1].start()]
                    if between.strip():
                        prefix_narration = between.strip()
                
                # 前文：前面所有非空行，取最近 3 行
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
    text_path = project_root / 'tests' / 'fantasy_long_text_test.txt'
    answer_path = project_root / 'tests' / 'fantasy_long_text_answer_key.json'
    result_path = project_root / 'tests' / 'fantasy_no_preset_result.json'
    
    # 加载答案
    with open(answer_path, 'r', encoding='utf-8') as f:
        answer_data = json.load(f)
    # 西幻答案格式是简单的字符串列表 ["亚瑟", "艾琳", ...]
    if isinstance(answer_data, list):
        answer_key = answer_data
    elif isinstance(answer_data, dict) and 'dialogues' in answer_data:
        answer_data_inner = answer_data['dialogues']
        if isinstance(answer_data_inner, list) and len(answer_data_inner) > 0:
            if isinstance(answer_data_inner[0], str):
                answer_key = answer_data_inner
            else:
                answer_key = [d['speaker'] for d in answer_data_inner]
        else:
            answer_key = answer_data_inner
    else:
        answer_key = answer_data
    
    # 初始化匹配器（不预注册任何角色！）
    char_manager = CharacterManager()
    # 注意：这里不调用 setup_characters()
    
    matcher = SpeakerMatcher()
    matcher.char_manager = char_manager
    matcher._current_project_id = 'fantasy_no_preset'
    
    # 解析文本
    dialogues = parse_text_file(str(text_path))
    print(f"解析到 {len(dialogues)} 条对话")
    print(f"答案文件有 {len(answer_key)} 条答案")
    print(f"\n【测试模式】无预注册角色库 - SRL动态角色发现（西幻文体）")
    print(f"{'='*60}\n")
    
    # 运行匹配
    correct = 0
    wrong = 0
    unknown = 0
    created_chars = set()
    results = []
    
    for i, dialogue in enumerate(dialogues):
        if i >= len(answer_key):
            break
        
        expected_speaker = answer_key[i] if isinstance(answer_key, list) else answer_key['dialogues'][i]
        if isinstance(expected_speaker, dict):
            expected_speaker = expected_speaker['speaker']
        
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
            created_chars.add(predicted)
            matcher.update_activity(result.character.id, predicted)
        else:
            predicted = 'UNKNOWN'
            match_type = 'none'
            confidence = 0.0
        
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
    print(f"测试结果 - 西幻无预注册角色库模式")
    print(f"{'='*60}")
    print(f"总对话数: {len(dialogues)}")
    print(f"可判断数: {len(dialogues) - unknown}")
    print(f"正确: {correct}")
    print(f"错误: {wrong}")
    print(f"跳过(非角色库): {unknown}")
    accuracy = correct/(correct+wrong)*100 if (correct+wrong) > 0 else 0
    print(f"准确率: {accuracy:.1f}%")
    print(f"\n动态发现的角色 ({len(created_chars)} 个):")
    for name in sorted(created_chars):
        freq = char_manager.get_frequency(name, 'fantasy_no_preset') if hasattr(char_manager, 'get_frequency') else 'N/A'
        print(f"  - {name} (频次: {freq})")
    
    # 保存结果
    result_data = {
        'total': len(dialogues),
        'judgable': len(dialogues) - unknown,
        'correct': correct,
        'wrong': wrong,
        'unknown': unknown,
        'accuracy': correct/(correct+wrong) if (correct+wrong) > 0 else 0,
        'discovered_characters': sorted(list(created_chars)),
        'results': results
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到 {result_path}")


if __name__ == '__main__':
    main()
