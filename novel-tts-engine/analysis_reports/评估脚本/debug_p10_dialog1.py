"""诊断P10对话1"""
# P10原文
P10 = '萧炎看向药老："这枚丹药值多少？"药老捋了捋胡须："至少三万金币。"萧炎皱眉："太贵了。'
dialogue1 = '"这枚丹药值多少？"'

idx = P10.find(dialogue1)
ctx_before = P10[:idx].strip()

print(f'P10: {P10}')
print(f'对话1: {dialogue1}')
print(f'ctx_before: "{ctx_before}"')
print()

# 分析：萧炎看向药老：
# - "萧炎"是主语（说话人）
# - "药老"是"看向"的宾语（被对话方）
# 预期说话人 = 萧炎

# 检查冒号规则
import re

# 找冒号位置
colon_pos = ctx_before.rfind('：')
print(f'冒号位置: {colon_pos}')
print(f'冒号前4字符: "{ctx_before[max(0, colon_pos-4):colon_pos]}"')

# 检查是否匹配到药老
if '药老' in ctx_before:
    pos = ctx_before.rfind('药老')
    before_name = ctx_before[max(0, pos-4):pos]
    print(f'药老前4字符: "{before_name}"')
    if re.search(r'(?:看向|看着|望着|对准|对着)$', before_name):
        print('✅ 药老被"看向"排除')
    else:
        print('❌ 药老未被排除')

# 检查是否匹配到萧炎
if '萧炎' in ctx_before:
    pos = ctx_before.rfind('萧炎')
    before_name = ctx_before[max(0, pos-4):pos]
    print(f'萧炎前4字符: "{before_name}"')
    if re.search(r'(?:看向|看着|望着|对准|对着)$', before_name):
        print('萧炎被"看向"排除')
    else:
        print('✅ 萧炎未被排除，应为说话人')
