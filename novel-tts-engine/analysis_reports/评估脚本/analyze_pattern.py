import re, json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

with open(str(project_root / 'tests' / 'urban_long_text_test.txt'), 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f.readlines() if l.strip()]

with open(str(project_root / 'tests' / 'urban_long_text_answer_key.json'), 'r', encoding='utf-8') as f:
    answer_key = json.load(f)

# 找出所有对话行（含引号）
dialogue_lines = []
for i, line in enumerate(lines):
    m = re.search(r'["""](.+?)["""]', line)
    if m:
        colon = line.find('\uff1a')
        q = line.find('"')
        if q == -1: q = line.find("'")
        has_prefix = (colon >= 0 and q >= 0 and colon < q)
        prefix = line[:colon].strip() if has_prefix else ''
        dialogue_lines.append({
            'idx': len(dialogue_lines),
            'line': line,
            'has_prefix': has_prefix,
            'prefix': prefix,
            'expected': answer_key['dialogues'][len(dialogue_lines)] if len(dialogue_lines) < len(answer_key['dialogues']) else '?'
        })

print('=== 对话模式分析 ===')
print()

# 检查连续纯对话段
i = 0
while i < len(dialogue_lines):
    if not dialogue_lines[i]['has_prefix']:
        # 找到连续纯对话段的起始
        start = i
        while i < len(dialogue_lines) and not dialogue_lines[i]['has_prefix']:
            i += 1
        # 连续纯对话段
        block = dialogue_lines[start:i]
        # 看上一个有旁白的行
        prev_with_prefix = dialogue_lines[start-1] if start > 0 else None
        # 看下一个有旁白的行
        next_with_prefix = dialogue_lines[i] if i < len(dialogue_lines) else None
        
        print(f'--- 纯对话段 [{start+1}~{i}] (共{i-start}条) ---')
        if prev_with_prefix:
            print(f'  上一个有旁白的行: #{start} {prev_with_prefix["expected"]} - {prev_with_prefix["prefix"][:30]}')
        for d in block:
            print(f'  #{d["idx"]+1}: {d["expected"]} - {d["line"][:60]}')
        if next_with_prefix:
            print(f'  下一个有旁白的行: #{i+1} {next_with_prefix["expected"]} - {next_with_prefix["prefix"][:30]}')
        print()
    else:
        i += 1
