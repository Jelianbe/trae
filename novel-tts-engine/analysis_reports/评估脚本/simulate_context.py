import re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

with open(str(project_root / 'tests' / 'urban_long_text_test.txt'), 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f.readlines() if l.strip()]

non_empty = [(i+1, l) for i, l in enumerate(lines)]

def get_context_before_new(idx, non_empty):
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
    return '。'.join(before_lines)

errors = [9, 10, 12, 17, 22, 28, 35, 39, 49, 53, 55, 67, 73, 76, 85, 90]

answers = {
    9: '赵总监', 10: '吴工程师', 12: '吴工程师', 17: '李经理',
    22: '吴工程师', 28: '刘秘书', 35: '赵总监', 39: '刘秘书',
    49: '张总', 53: '张总', 55: '张总', 67: '李经理',
    73: '李经理', 76: '赵总监', 85: '张总', 90: '张总'
}

print('=== 新方案下 context_before 模拟 ===')
count_would_fix = 0
for err_idx in errors:
    dialogue_idx = err_idx - 1
    ctx = get_context_before_new(dialogue_idx, non_empty)
    answer = answers.get(err_idx, '?')
    in_ctx = answer in ctx
    
    if in_ctx:
        count_would_fix += 1
    
    print(f'#{err_idx}: 预期={answer} -> {"在" if in_ctx else "不在"}context_before中')
    print(f'  {ctx[:100]}')
    print()

print(f'=== 汇总 ===')
print(f'16条错误中，预期角色会出现在新context_before中的: {count_would_fix}条')
print(f'仍无法修复的: {16 - count_would_fix}条')
