"""无预注册角色场景准确率测试 — 西幻

标准化基线测试 #4：西幻-无预注册
测试文件: tests/fantasy_long_text_test.txt
预期基线: ≥71.9%

用法: python tests/baseline/test_fantasy_no_preset.py
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
TEST_FILE = str(Path(__file__).parent.parent / "fantasy_long_text_test.txt")
ANSWER_FILE = str(Path(__file__).parent.parent / "fantasy_long_text_answer_key.json")
EXPECTED_BASELINE = 71.9


def parse_text_file(file_path):
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
                'has_prefix': bool(prefix_narration),
            })
    return dialogues


def run():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        char_manager = CharacterManager(db_path)
        matcher = SpeakerMatcher()
        matcher.char_manager = char_manager
        matcher._current_project_id = 'fantasy_no_preset'

        with open(ANSWER_FILE, 'r', encoding='utf-8') as f:
            answer_key = json.load(f)

        dialogues = parse_text_file(TEST_FILE)
        correct, wrong, unknown = 0, 0, 0
        results = []
        for i, d in enumerate(dialogues):
            if i >= len(answer_key['dialogues']):
                break
            expected = answer_key['dialogues'][i]
            ctx = DialogueContext(
                text=d['text'], context_before=d['context_before'],
                context_after=d['context_after'], prefix_narration=d.get('prefix_narration', '')
            )
            result = matcher.match_speaker(ctx)
            if result and result.character:
                predicted = result.character.name
                match_type = result.match_type
            else:
                predicted, match_type = 'UNKNOWN', 'none'
            if expected == 'UNKNOWN':
                status = 'skip'; unknown += 1
            elif predicted == expected:
                status = 'ok'; correct += 1
            elif predicted == 'UNKNOWN':
                status = 'unknown'; unknown += 1
            else:
                status = 'wrong'; wrong += 1
            results.append({'index': i+1, 'text': d['text'][:50], 'expected': expected, 'predicted': predicted, 'status': status})
        total = len(dialogues)
        judgable = total - unknown
        accuracy = correct / judgable * 100 if judgable > 0 else 0
        return accuracy, total, correct, results
    finally:
        try: os.unlink(db_path)
        except: pass


if __name__ == "__main__":
    accuracy, total, correct, results = run()
    status = "PASS" if accuracy >= EXPECTED_BASELINE else "FAIL"
    print(f"西幻-无预注册: {accuracy:.1f}% ({correct}/{total}) [{status}] (预期≥{EXPECTED_BASELINE}%)")
    for r in results:
        if r['status'] == 'wrong':
            print(f"  FAIL: expected={r['expected']}, got={r['predicted']} - {r['text']}")
