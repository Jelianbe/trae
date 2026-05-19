"""端到端说话人识别准确率测试 — 西幻-有预注册

标准化基线测试 #2（E2E）：完整文本导入 → 自动分割 → 说话人识别
测试文件: tests/fantasy_long_text_test.txt
答案文件: tests/fantasy_long_text_answer_key.json
预期基线: ≥65.6%

架构说明：
- 读取完整文本文件，调用公共 API analyze_dialogue
- 系统自动完成：引号分割 → 旁白提取 → 说话人识别
- 预注册角色库，测试角色匹配能力

用法: python tests/baseline/test_fantasy_preset_e2e.py
"""
import sys
import re
import json
import tempfile
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher

# ===== 固定测试配置（不得随意修改） =====
TEST_FILE = str(Path(__file__).parent.parent / "fantasy_long_text_test.txt")
ANSWER_FILE = str(Path(__file__).parent.parent / "fantasy_long_text_answer_key.json")
CHARACTER_INFO = {
    '亚瑟': {'gender': 'male', 'aliases': {'亚瑟团长', '团长'}},
    '艾琳': {'gender': 'female', 'aliases': {'艾琳法师'}},
    '雷恩': {'gender': 'male', 'aliases': {'雷恩队长', '队长'}},
    '莉莉': {'gender': 'female', 'aliases': {'莉莉治疗师', '治疗师'}},
    '加文': {'gender': 'male', 'aliases': {'加文老战士', '老战士'}},
}
EXPECTED_BASELINE = 65.6


def load_answers(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 西幻答案文件格式: {"dialogues": ["亚瑟", "艾琳", ...]}
    return data.get('dialogues', [])


def build_answers_by_line(text_path, answer_list):
    """将数组形式的答案转换为按对话内容索引。
    
    读取原文，按行号（跳过空行）建立映射。
    """
    with open(text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]
    
    dialogue_to_speaker = {}
    idx = 0
    for line_num, text in non_empty:
        if idx >= len(answer_list):
            break
        speaker = answer_list[idx]
        # 提取引号内容作为 key
        match = re.search(r'["""](.+?)["""]', text)
        if match:
            dialogue_content = match.group(1)
            dialogue_to_speaker[dialogue_content] = speaker
            idx += 1
    
    return dialogue_to_speaker


def run():
    answer_list = load_answers(ANSWER_FILE)
    dialogue_to_speaker = build_answers_by_line(TEST_FILE, answer_list)
    
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        full_text = f.read()
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        char_manager = CharacterManager(db_path)
        for name, info in CHARACTER_INFO.items():
            char_manager.add_character(name, project_id='fantasy_e2e', aliases=info['aliases'], gender=info['gender'])
        
        matcher = SpeakerMatcher(char_manager)
        matcher._current_project_id = 'fantasy_e2e'
        
        # 调用公共 API：完整文本 → 自动分割 → 说话人识别
        results = matcher.analyze_dialogue(full_text, chapter_id=1)
        
        correct = 0
        total = 0
        unknown = 0
        errors = []
        
        for dialogue_content, speaker in results:
            if dialogue_content not in dialogue_to_speaker:
                continue
            
            expected = dialogue_to_speaker[dialogue_content]
            total += 1
            
            if expected == 'UNKNOWN':
                unknown += 1
                continue
            
            predicted = speaker.name if speaker else None
            
            if predicted is None:
                unknown += 1
                errors.append(("UNKNOWN", dialogue_content[:40], expected, predicted))
            elif predicted == expected:
                correct += 1
            else:
                errors.append(("FAIL", dialogue_content[:40], expected, predicted))
        
        judgable = total - unknown
        accuracy = correct / judgable * 100 if judgable > 0 else 0
        
        return accuracy, total, correct, unknown, errors
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


if __name__ == "__main__":
    accuracy, total, correct, unknown, errors = run()
    judgable = total - unknown
    status = "PASS" if accuracy >= EXPECTED_BASELINE else "FAIL"
    print(f"西幻-有预注册 (E2E): {accuracy:.1f}% ({correct}/{judgable}) [{status}] (预期≥{EXPECTED_BASELINE}%)")
    print(f"  总对话: {total}, 正确: {correct}, UNKNOWN: {unknown}")
    
    if errors:
        print("\n【错误详情】")
        for err_type, dialogue, expected, predicted in errors:
            print(f"  {err_type}: 预期={expected}, 预测={predicted}  对话: {dialogue}...")
