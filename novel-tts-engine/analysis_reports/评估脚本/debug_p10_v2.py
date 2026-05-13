"""调试P10对话2为什么没匹配到药老"""
import re

# P10对话2的context_before
ctx_before = '萧炎看向药老："这枚丹药值多少？"药老捋了捋胡须：'
name = '药老'

pos = ctx_before.rfind(name)
print(f'ctx_before: {ctx_before}')
print(f'药老位置: {pos}')
after_name = ctx_before[pos + len(name):pos + len(name) + 10]
print(f'药老后面: "{after_name}"')

# 规则2检查
if re.match(r'(?:道|说道|问|答道|喊|叫|笑道|沉声道|冷冷道|淡淡道|低声道|高声道)', after_name):
    print('规则2匹配: 说话动词')
else:
    print('规则2不匹配')

# 规则3检查
if re.match(r'[：:]', after_name):
    print('规则3匹配: 冒号')
    before_name = ctx_before[max(0, pos-4):pos]
    print(f'药老前面: "{before_name}"')
    if not re.search(r'(?:看向|看着|望着|对准|对着)$', before_name):
        print('规则3通过: 不是被对话方')
    else:
        print('规则3不通过: 是被对话方')
else:
    print('规则3不匹配')

# 规则4检查
if pos <= 2 and len(ctx_before) < 30:
    print('规则4可能匹配')
    if re.search(r'(?:从.+?(?:飘出|走出|走来)|拍了一下|站起身|转过头|摇了摇头|点了点头|叹了口气)', ctx_before):
        print('规则4匹配: 动作暗示')
else:
    print(f'规则4不匹配: pos={pos}, len={len(ctx_before)}')
