"""诊断P18 dialog1为什么药老摇头道不匹配"""
import re

# P18原文
P18 = '"萧炎，你太弱了！"药老摇头道。萧炎低下头："师傅，我会努力的。"药老叹了口气。'

# 对话1的位置
dialogue1 = '"萧炎，你太弱了！"'
idx = P18.find(dialogue1)
ctx_before = P18[:idx].strip()  # 应该是空
ctx_after = P18[idx+len(dialogue1):].strip()  # "药老摇头道。萧炎低下头..."

print(f'P18: {P18}')
print(f'ctx_before: "{ctx_before}"')
print(f'ctx_after: "{ctx_after}"')
print()

# 测试药老摇头道匹配
char_name = '药老'
patterns = [
    rf'{char_name}(?:.+?)?(?:捋了捋胡须|摇头|点头|叹息|叹气)(?:.+?)?(?:道|说|：|:)',
]

for pattern in patterns:
    match_before = re.search(pattern, ctx_before)
    match_after = re.search(pattern, ctx_after)
    print(f'pattern: {pattern}')
    print(f'  context_before match: {match_before.group() if match_before else None}')
    print(f'  context_after match: {match_after.group() if match_after else None}')

# 检查NER
print()
print("=== NER检查 ===")
print(f"ctx_before中是否有萧炎: {'萧炎' in ctx_before}")
print(f"ctx_after中是否有萧炎: {'萧炎' in ctx_after}")
