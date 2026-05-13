"""调试P10对话1冒号匹配"""
import re

ctx_before = '萧炎看向药老：'
name = '药老'

pos = ctx_before.rfind(name)
print(f'ctx_before: {ctx_before}')
print(f'药老位置: {pos}')
after_name = ctx_before[pos + len(name):pos + len(name) + 10]
print(f'药老后面: "{after_name}"')

# 规则3检查
if re.search(r'[：:]', after_name[:8]):
    print('冒号匹配')
    before_name = ctx_before[max(0, pos-4):pos]
    print(f'药老前面4字符: "{before_name}"')
    if re.search(r'(?:看向|看着|望着|对准|对着)$', before_name):
        print('被排除: 药老是被对话方')
    else:
        print('未被排除: 药老被误判为说话人')
else:
    print('冒号不匹配')

# 检查萧炎是否匹配
name2 = '萧炎'
pos2 = ctx_before.rfind(name2)
print()
print(f'萧炎位置: {pos2}')
after_name2 = ctx_before[pos2 + len(name2):pos2 + len(name2) + 10]
print(f'萧炎后面: "{after_name2}"')
if re.search(r'[：:]', after_name2[:8]):
    print('萧炎冒号匹配')
    before_name2 = ctx_before[max(0, pos2-4):pos2]
    print(f'萧炎前面4字符: "{before_name2}"')
    if re.search(r'(?:看向|看着|望着|对准|对着)$', before_name2):
        print('被排除')
    else:
        print('未被排除: 萧炎是说话人')
