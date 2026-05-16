import json, re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent

with open(str(project_root / 'tests' / 'urban_long_text_test.txt'), 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(str(project_root / 'tests' / 'urban_long_text_answer_key.json'), 'r', encoding='utf-8') as f:
    answer_key = json.load(f)

non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]

wrong_cases = [
    (6, '谁批准的？', '赵总监', '李经理'),
    (13, '我知道你尽力了', '李经理', '赵总监'),
    (15, '都安排好了', '刘秘书', '赵总监'),
    (21, '数据库连接数满了', '孙工', '赵总监'),
    (24, '已经停了', '孙工', '赵总监'),
    (26, '对不起', '孙工', '李经理'),
    (48, '去我办公室谈', '张总', '赵总监'),
    (51, '说说吧', '张总', '赵总监'),
    (53, '钱不是问题', '张总', '赵总监'),
    (55, '我去跟财务说', '张总', '赵总监'),
    (57, '去吧', '张总', '赵总监'),
    (58, '怎么样？', '李经理', '赵总监'),
    (60, '好的，我这就去通知', '李经理', '赵总监'),
    (70, '放桌上吧', '赵总监', '刘秘书'),
    (73, '都通知到了', '李经理', '刘秘书'),
    (74, '好，下午的会', '赵总监', '刘秘书'),
    (75, '我已经准备好了', '李经理', '刘秘书'),
    (76, '数据很详细', '赵总监', '刘秘书'),
    (77, '谢谢', '李经理', '刘秘书'),
    (78, '辛苦了', '赵总监', '刘秘书'),
    (79, '没问题', '李经理', '刘秘书'),
    (85, '你说，我听着', '张总', '赵总监'),
    (88, '主要是服务器采购', '李经理', '赵总监'),
    (90, '她做事很细致', '张总', '赵总监'),
]

print('=== 错误案例 context_before 分析 ===')
print()

for idx, (line_num, text) in enumerate(non_empty):
    if '"' in text or "'" in text:
        match = re.search(r'["""](.+?)["""]', text)
        if match:
            dialogue_content = match.group(1)
            for case_idx, case_text, expected, predicted in wrong_cases:
                if case_text in dialogue_content:
                    before_lines = []
                    for prev_idx in range(idx-1, -1, -1):
                        prev_line = non_empty[prev_idx][1]
                        if prev_line and '"' not in prev_line and "'" not in prev_line:
                            before_lines.append(prev_line)
                        if len(before_lines) >= 3:
                            break
                    before_lines.reverse()
                    context_before = '。'.join(before_lines) + '。' if before_lines else '(空)'

                    colon_idx = text.find('：')
                    quote_idx = text.find('"')
                    if quote_idx == -1:
                        quote_idx = text.find("'")
                    if colon_idx >= 0 and quote_idx >= 0 and colon_idx < quote_idx:
                        raw_prefix = text[:colon_idx].strip()
                    else:
                        raw_prefix = '(无冒号前内容)'

                    quoted = dialogue_content[:50]

                    print(f'=== 第{case_idx}条 ===')
                    print(f'原文: {text[:80]}')
                    print(f'同行动作主语: {raw_prefix}')
                    print(f'context_before: {context_before[:120]}')
                    print(f'预期={expected}, 预测={predicted}')
                    print()
                    break

# Count: how many wrong cases have narration prefix on same line?
total_with_prefix = 0
total_before_context_has_correct = 0
for idx, (line_num, text) in enumerate(non_empty):
    if '"' in text or "'" in text:
        match = re.search(r'["""](.+?)["""]', text)
        if match:
            dialogue_content = match.group(1)
            for case_idx, case_text, expected, predicted in wrong_cases:
                if case_text in dialogue_content:
                    colon_idx = text.find('：')
                    quote_idx = text.find('"')
                    if quote_idx == -1:
                        quote_idx = text.find("'")
                    if colon_idx >= 0 and quote_idx >= 0 and colon_idx < quote_idx:
                        raw_prefix = text[:colon_idx].strip()
                        # Check if expected speaker is in the prefix
                        if expected in raw_prefix:
                            total_with_prefix += 1
                    break

print(f'=== 汇总 ===')
print(f'预期角色出现在同一行旁白前的错误: {total_with_prefix}条')
print(f'共分析错误案例: {len(wrong_cases)}条')
