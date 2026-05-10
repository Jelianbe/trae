# -*- coding: utf-8 -*-
"""T-007 代词消解调试脚本"""
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
import tempfile
import os

db = tempfile.mktemp(suffix='.db')
cm = CharacterManager(db)
cm.add_character('林轩', gender='male')
cm.add_character('小翠', gender='female')

matcher = SpeakerMatcher(cm)

# 测试用例 1：简单代词
text1 = '林轩说道："你好。"他转身离开了。'
results1 = matcher.analyze_dialogue(text1)
print(f'测试1: {text1}')
for d, c in results1:
    print(f'  对话: {d} -> 说话人: {c.name if c else None}')

print()

# 测试用例 2：双角色交替
matcher.reset_activity()
text2 = '林轩说道："你去哪里？"小翠回应道："我去买东西。"她拿起包裹。'
results2 = matcher.analyze_dialogue(text2)
print(f'测试2: {text2}')
for d, c in results2:
    print(f'  对话: {d} -> 说话人: {c.name if c else None}')

print()

# 测试用例 3：三角色混合
matcher.reset_activity()
cm.add_character('药老', gender='male')
text3 = '萧炎说道："这件事交给我吧。"药老点头道："你可以试试。"他捋了捋胡须。'
results3 = matcher.analyze_dialogue(text3)
print(f'测试3: {text3}')
for d, c in results3:
    print(f'  对话: {d} -> 说话人: {c.name if c else None}')

# 清理
os.remove(db)
