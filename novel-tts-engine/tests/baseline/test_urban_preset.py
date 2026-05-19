"""有预注册角色场景准确率测试 — 都市

标准化基线测试 #1：都市-有预注册
测试文件: tests/urban_long_text_test.txt
答案文件: tests/urban_preset_answers.json
预期基线: ≥100.0%

用法: python tests/baseline/test_urban_preset.py
"""
import sys
import re
import json
import tempfile
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext

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


def parse_text_file(text_path):
    with open(text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]
    dialogues = []
    for idx, (line_num, text) in enumerate(non_empty):
        if '"' in text or '\u201c' in text or '\u300c' in text or '\u300e' in text:
            match = re.search(r'[\u201c\u201d\u300c\u300d\u300e\u300f""](.*?)[\u201c\u201d\u300c\u300d\u300e\u300f""]', text)
            if match:
                prefix_narration = text[:match.start()].strip()
                context_before = non_empty[idx-1][1] if idx > 0 else ''
                context_after = non_empty[idx+1][1] if idx < len(non_empty) - 1 else ''
                dialogues.append({
                    'text': text,
                    'dialogue_content': match.group(1),
                    'line_num': line_num,
                    'context_before': context_before,
                    'context_after': context_after,
                    'prefix_narration': prefix_narration,
                })
    return dialogues


def get_matched_name(result):
    if result is None:
        return None
    if result.character:
        return result.character.name
    if result.speaker_id:
        return result.speaker_id.normalized
    return None


def run():
    answers = load_answers(ANSWERS_FILE)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        char_manager = CharacterManager(db_path)
        for name, gender, aliases in CHARACTER_INFO:
            char_manager.add_character(name, gender=gender, aliases=aliases)
        matcher = SpeakerMatcher(char_manager)
        matcher._current_project_id = 'test_urban_preset'
        dialogues = parse_text_file(TEST_FILE)
        correct, total, skipped, results = 0, 0, 0, []
        prev_speaker = None
        for d in dialogues:
            line_num = str(d['line_num'])
            if line_num not in answers:
                skipped += 1
                continue
            expected = answers[line_num]
            total += 1
            ctx = DialogueContext(
                text=d['text'], prefix_narration=d['prefix_narration'],
                context_before=d['context_before'], context_after=d['context_after'],
                prev_speaker=prev_speaker,
            )
            result = matcher.match_speaker(ctx)
            matched = get_matched_name(result)
            if matched == expected:
                correct += 1
                results.append(("OK", d, matched))
                prev_speaker = matched
            else:
                results.append(("FAIL", d, expected, matched))
                if matched: prev_speaker = matched
        accuracy = correct / total * 100 if total > 0 else 0
        return accuracy, total, correct, skipped, results
    finally:
        try: os.unlink(db_path)
        except: pass


if __name__ == "__main__":
    accuracy, total, correct, skipped, results = run()
    status = "PASS" if accuracy >= EXPECTED_BASELINE else "FAIL"
    print(f"都市-有预注册: {accuracy:.1f}% ({correct}/{total}) [{status}] (预期≥{EXPECTED_BASELINE}%)")
    for r in results:
        if r[0] == "FAIL":
            d = r[1]
            print(f"  FAIL L{d['line_num']}: expected={r[2]}, got={r[3]}  原文: {d['dialogue_content'][:30]}...")
