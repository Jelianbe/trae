"""都市长文本基线测试

读取 urban_long_text_test.txt，按段落解析对话，
调用说话人匹配器，与 answer_key.json 对比。
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
                
                # 前文：前面所有非空行，取最近 3 行
                before_lines = []
                for prev_idx in range(idx-1, -1, -1):
                    prev_line = non_empty[prev_idx][1]
                    if prev_line and '"' not in prev_line and "'" not in prev_line:
                        before_lines.append(prev_line)
                    if len(before_lines) >= 3:
                        break
                before_lines.reverse()
                context_before = '。'.join(before_lines) + '。' if before_lines else ''
                
                # 后文：后面 2 行非空行
                after_lines = []
                for next_idx in range(idx+1, min(idx+5, len(non_empty))):
                    next_line = non_empty[next_idx][1]
                    if next_line and '"' not in next_line and "'" not in next_line:
                        after_lines.append(next_line)
                    if len(after_lines) >= 2:
                        break
                context_after = '。'.join(after_lines) + '。' if after_lines else ''
                
                dialogues.append({
                    'text': dialogue_content,
                    'context_before': context_before,
                    'context_after': context_after,
                    'raw_line': text,
                    'prefix_narration': prefix_narration
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
    matcher.current_project_id = 'test_project'
    
    # 解析文本
    dialogues = parse_text_file(str(text_path))
    print(f"解析到 {len(dialogues)} 条对话")
    print(f"答案文件有 {len(answer_key['dialogues'])} 条答案")
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
    print(f"准确率: {correct/(correct+wrong)*100:.1f}%" if (correct+wrong) > 0 else "N/A")
    
    # 保存结果
    result_data = {
        'total': len(dialogues),
        'judgable': len(dialogues) - unknown,
        'correct': correct,
        'wrong': wrong,
        'unknown': unknown,
        'accuracy': correct/(correct+wrong) if (correct+wrong) > 0 else 0,
        'results': results
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到 {result_path}")


if __name__ == '__main__':
    main()
