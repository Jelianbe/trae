"""检查P10对话1的ctx_after切割"""
P10 = '萧炎看向药老："这枚丹药值多少？"药老捋了捋胡须："至少三万金币。"萧炎皱眉："太贵了。'
dialogue1 = '"这枚丹药值多少？"'

idx = P10.find(dialogue1)
ctx_after_raw = P10[idx+len(dialogue1):].strip()

print(f'P10: {P10}')
print(f'对话1: {dialogue1}')
print(f'对话1结束位置: {idx+len(dialogue1)}')
print(f'ctx_after原始: "{ctx_after_raw}"')
print()

# 问题：ctx_after应该只包含对话1之后、对话2之前的叙述文本
# 但当前的ctx_after包含了整个后续文本

# 正确做法：找到下一个对话引号的位置
next_quote_pos = ctx_after_raw.find('"')
if next_quote_pos == -1:
    next_quote_pos = ctx_after_raw.find('"')

if next_quote_pos >= 0:
    ctx_after_correct = ctx_after_raw[:next_quote_pos].strip()
    print(f'下一个引号位置: {next_quote_pos}')
    print(f'正确的ctx_after: "{ctx_after_correct}"')
else:
    print(f'无引号，取前20字符: "{ctx_after_raw[:20]}"')
