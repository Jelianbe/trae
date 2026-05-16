import re

line = '"赵总监，给你介绍一下。"张总侧过身，"这是我们技术部的陈主管。"'

all_quotes = list(re.finditer(r'["""](.+?)["""]', line))
print(f'总引号段数: {len(all_quotes)}')
for i, q in enumerate(all_quotes):
    print(f'  第{i+1}段: "{q.group(1)}" (位置 {q.start()}-{q.end()})')

if len(all_quotes) >= 2:
    between = line[all_quotes[0].end():all_quotes[1].start()]
    print(f'两段之间的内容: "{between}"')
