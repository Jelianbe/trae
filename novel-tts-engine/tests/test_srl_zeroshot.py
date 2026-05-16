"""SRL ARG0 零样本测试 --- 无角色库依赖，直接评估 SRL 原始提取能力。

在无角色库的情况下，直接用 HanLP SRL 提取旁白中的施事者（ARG0），
对比预期说话人，评估 SRL 在说话人发现任务中的原始能力。
"""
import sys, json, os, re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.environ['DEBUG_SRL'] = '1'

from pipeline.nlp_basics import get_nlp, reset_nlp


def parse_dialogue_file(file_path: str) -> list:
    """parse test file, return [(dialogue_text, context_before, context_after, line_num), ...]"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]

    dialogues = []
    for idx, (line_num, text) in enumerate(non_empty):
        if '"' in text or "'" in text or '\u201c' in text or '\u2018' in text:
            match = re.search(r'[\u201c""](.+?)[\u201d""]', text)
            if not match:
                continue

            # context_before: previous line
            context_before = non_empty[idx-1][1] if idx > 0 else ''

            # prefix: text before fullwidth colon
            colon_idx = text.find('\uff1a')
            if colon_idx > 0:
                prefix_narration = text[:colon_idx]
            else:
                prefix_narration = ''

            dialogues.append({
                'line_num': line_num,
                'text': text,
                'dialogue': match.group(1),
                'context_before': context_before,
                'prefix_narration': prefix_narration,
            })

    return dialogues


def load_answer_key(answer_path: str) -> dict:
    with open(answer_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_srl_on_dataset(name: str, file_path: str, answer_path: str):
    """Test SRL ARG0 extraction without character library."""
    print(f"\n{'='*70}")
    print(f"  SRL zero-shot test: {name}")
    print(f"{'='*70}")

    reset_nlp()
    nlp = get_nlp()

    dialogues = parse_dialogue_file(file_path)
    answer_key = load_answer_key(answer_path)

    total = min(len(dialogues), len(answer_key['dialogues']))
    srl_found = 0
    srl_matched_expected = 0
    srl_extracted_all = []

    for i in range(total):
        d = dialogues[i]
        raw_expected = answer_key['dialogues'][i]
        expected = raw_expected if isinstance(raw_expected, str) else raw_expected.get('speaker', 'UNKNOWN')

        context_before = d['context_before']
        if not context_before:
            continue

        arg0s = nlp.extract_srl_arg0s(context_before)

        if arg0s:
            srl_found += 1
            for a in arg0s:
                srl_extracted_all.append(a)
                if a == expected:
                    srl_matched_expected += 1

            expected_display = expected if expected != 'UNKNOWN' else '?'
            match_mark = '+' if expected in arg0s else ' '
            first_30 = d['text'][:40]
            print(f"  [{match_mark}] SRL={arg0s}   exp={expected_display:8s} | {first_30}")

    total_judgable = sum(1 for i in range(total) if dialogues[i]['context_before'])
    unique_extracted = list(set(srl_extracted_all))

    print(f"\n{'='*70}")
    print(f"  {name} SRL zero-shot summary")
    print(f"  total dialogues          : {total}")
    print(f"  has context_before       : {total_judgable}")
    print(f"  SRL triggered            : {srl_found}")
    print(f"  unique entities found    : {len(unique_extracted)}")
    print(f"  matched expected speaker : {srl_matched_expected}")
    print(f"  SRL entities             : {unique_extracted}")
    print(f"{'='*70}")

    return {
        'name': name,
        'total': total,
        'judgable': total_judgable,
        'srl_found': srl_found,
        'unique_entities': unique_extracted,
        'matched_expected': srl_matched_expected,
    }


def test_single_sentences():
    """Test SRL on hand-crafted typical sentences."""
    print(f"\n{'='*70}")
    print(f"  Typical sentence SRL ARG0 extraction")
    print(f"{'='*70}")

    reset_nlp()
    nlp = get_nlp()

    test_cases = [
        # urban scenarios
        "赵总监皱起眉头问道：",
        "李经理端起咖啡喝了一口，抬头说：",
        "吴工程师看了看报表，叹了口气：",
        "孙工打开电脑，飞快地敲击键盘：",
        "张总站起身，走到窗前：",
        "刘秘书推了推眼镜，认真地说：",
        "赵总监翻开文件，脸色渐渐沉了下来。",

        # fantasy scenarios
        "亚瑟拔出长剑，高喊道：",
        "艾琳法师挥动法杖，一道蓝光射向城门：",
        "雷恩队长举起盾牌，大吼道：",
        "莉莉迅速施展治疗术，绿色的光芒笼罩了伤员：",
        "加文老战士握紧战斧，目光坚定：",

        # complex (multiple characters)
        "亚瑟看了艾琳一眼，低声说道：",
        "赵总监对李经理点了点头，然后转向吴工程师：",

        # no-character-name narration
        "他站起身，走到窗前：",
        "她轻轻叹了口气，说道：",
        "团长缓缓转过身来，目光如炬：",
        "队长环顾四周，沉声道：",
    ]

    for sent in test_cases:
        arg0s = nlp.extract_srl_arg0s(sent)
        print(f"  text: {sent}")
        print(f"  SRL : {arg0s}\n")


if __name__ == '__main__':
    # 1. single sentence tests
    test_single_sentences()

    # 2. urban dataset zero-shot
    urban_file = project_root / 'tests' / 'urban_long_text_test.txt'
    urban_answer = project_root / 'tests' / 'urban_long_text_answer_key.json'
    if urban_file.exists() and urban_answer.exists():
        test_srl_on_dataset('urban', str(urban_file), str(urban_answer))

    # 3. fantasy dataset zero-shot
    fantasy_file = project_root / 'tests' / 'fantasy_long_text_test.txt'
    fantasy_answer = project_root / 'tests' / 'fantasy_long_text_answer_key.json'
    if fantasy_file.exists() and fantasy_answer.exists():
        test_srl_on_dataset('fantasy', str(fantasy_file), str(fantasy_answer))
