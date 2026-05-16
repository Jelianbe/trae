import re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
with open(str(project_root / 'tests' / 'urban_long_text_test.txt'), 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f.readlines() if l.strip()]

print('=== 引号内容分析 ===')
non_dialogue_quotes = []
dialogue_quotes = []

for i, line in enumerate(lines):
    quotes = re.findall(r'["""](.+?)["""]', line)
    for q in quotes:
        # 判断是否是拟声词或强调词
        is_sfx = bool(re.match(r'^[!！？\*～~\.\.\…—\-]+$', q.strip()))
        is_action = bool(re.search(r'[点头摇头笑哭叹气转身跑走站坐躺]', q))
        is_emphasis = bool(re.match(r'^(太好了|糟糕|完了|糟糕|不行|不行|天哪|我的天|好家伙)', q))
        
        if is_sfx or is_action or is_emphasis:
            non_dialogue_quotes.append((i+1, line, q))
        else:
            dialogue_quotes.append((i+1, q[:50]))

print(f'引号总数: {len(dialogue_quotes) + len(non_dialogue_quotes)}')
print(f'对话内容: {len(dialogue_quotes)} 条')
print(f'拟声/动作/强调词: {len(non_dialogue_quotes)} 条')
print()

if non_dialogue_quotes:
    print('=== 非对话类引号 ===')
    for line_num, line, q in non_dialogue_quotes:
        print(f'  行{line_num}: [{q}]')
        print(f'    原文: {line[:80]}')
        print()
