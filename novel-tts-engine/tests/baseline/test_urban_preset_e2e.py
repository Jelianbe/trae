"""端到端说话人识别准确率测试 — 都市-有预注册

标准化基线测试 #1（E2E）：完整文本导入 → 自动分割 → 说话人识别
测试文件: tests/urban_long_text_test.txt
答案文件: tests/urban_preset_answers.json
预期基线: ≥100.0%

架构说明：
- 读取完整文本文件，调用公共 API analyze_dialogue
- 系统自动完成：引号分割 → 旁白提取 → 说话人识别
- 标准答案按对话内容索引，与系统输出直接对比
- 无论内部实现如何改动，只要公共接口稳定，测试就不会崩溃

用法: python tests/baseline/test_urban_preset_e2e.py
"""
import sys
import json
import tempfile
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher

# ===== 固定测试配置（不得随意修改） =====
TEST_FILE = str(Path(__file__).parent.parent / "urban_long_text_test.txt")
ANSWERS_FILE = str(Path(__file__).parent.parent / "urban_preset_answers.json")
CHARACTER_INFO = [
    ("赵总监", "male", {"总监"}),
    ("李经理", "male", {"经理"}),
    ("吴工程师", "male", {"吴工"}),
    ("刘秘书", "female", {"秘书"}),
    ("孙工", "male", set()),
    ("张总", "male", {"老总"}),
    ("陈主管", "female", {"主管"}),
]
EXPECTED_BASELINE = 100.0


def load_answers(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_answers_by_dialogue(answers, text):
    """将行号索引的答案转换为按对话内容索引。
    
    原理：读取原文，按行号找到对应的对话内容，建立 {dialogue_content: speaker_name} 映射。
    """
    import re
    
    with open(text, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    dialogue_to_speaker = {}
    
    for line_idx, (line_num_str, speaker) in enumerate(answers.items()):
        line_num = int(line_num_str)
        if line_num < 1 or line_num > len(lines):
            continue
        
        line = lines[line_num - 1].strip()
        # 提取引号内的对话内容
        match = re.search(r'[\u201c\u201d\u300c\u300d\u300e\u300f""](.*?)[\u201c\u201d\u300c\u300d\u300e\u300f""]', line)
        if match:
            dialogue_content = match.group(1)
            dialogue_to_speaker[dialogue_content] = speaker
    
    return dialogue_to_speaker


def run():
    answers = load_answers(ANSWERS_FILE)
    dialogue_to_speaker = build_answers_by_dialogue(answers, TEST_FILE)
    
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        full_text = f.read()
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        char_manager = CharacterManager(db_path)
        for name, gender, aliases in CHARACTER_INFO:
            char_manager.add_character(name, project_id='test_urban_preset_e2e', gender=gender, aliases=aliases)
        
        matcher = SpeakerMatcher(char_manager)
        matcher._current_project_id = 'test_urban_preset_e2e'
        
        # 调用公共 API：完整文本 → 自动分割 → 说话人识别
        results = matcher.analyze_dialogue(full_text, chapter_id=1)
        
        correct = 0
        total = 0
        unknown = 0
        errors = []
        
        for dialogue_content, speaker in results:
            if dialogue_content not in dialogue_to_speaker:
                # 系统提取的对话不在答案中（可能是答案文件遗漏）
                continue
            
            expected = dialogue_to_speaker[dialogue_content]
            total += 1
            
            predicted = speaker.name if speaker else None
            
            if predicted is None:
                unknown += 1
                errors.append(("UNKNOWN", dialogue_content[:40], expected, predicted))
            elif predicted == expected:
                correct += 1
            else:
                errors.append(("FAIL", dialogue_content[:40], expected, predicted))
        
        # 计算可判断的准确率（排除 UNKNOWN）
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
    print(f"都市-有预注册 (E2E): {accuracy:.1f}% ({correct}/{judgable}) [{status}] (预期≥{EXPECTED_BASELINE}%)")
    print(f"  总对话: {total}, 正确: {correct}, UNKNOWN: {unknown}")
    
    if errors:
        print("\n【错误详情】")
        for err_type, dialogue, expected, predicted in errors:
            print(f"  {err_type}: 预期={expected}, 预测={predicted}  对话: {dialogue}...")
