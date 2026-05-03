# -*- coding: utf-8 -*-
"""
检查萧媚是否有对话
"""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

# 查找包含"萧媚"和对话引导词的句子
print("=" * 80)
print("检查萧媚的对话")
print("=" * 80)

# 查找所有"萧媚"后面的动词
xiaomei_pattern = re.compile(r'萧媚([^\s，。！？]{0,10})')
matches = list(xiaomei_pattern.finditer(text))

print(f"\n【'萧媚'后面的动词/动作】")
for m in matches[:20]:
    after = m.group(1)
    if after:
        # 打印上下文
        start = max(0, m.start() - 20)
        end = min(len(text), m.end() + 20)
        context = text[start:end].replace('\n', ' ')
        print(f"  ...{context}...")

# 检查对话标注
print(f"\n\n【GT中的对话标注】")
print("萧媚不在dialogue_speakers中，说明没有明确标注她的对话")
print("但她出现11次，应该有说话场景")

# 查找"萧媚"后面跟"道"、"说"、"问"等的情况
dialogue_pattern = re.compile(r'萧媚.{0,5}(?:道|说|问|喊|叫)')
dialogue_matches = list(dialogue_pattern.finditer(text))
print(f"\n【'萧媚'后跟对话引导词的情况】: {len(dialogue_matches)}次")
for m in dialogue_matches:
    start = max(0, m.start() - 10)
    end = min(len(text), m.end() + 30)
    context = text[start:end].replace('\n', ' ')
    print(f"  ...{context}...")

print("\n" + "=" * 80)
print("结论：")
print("=" * 80)
print("如果萧媚没有明确的'萧媚道'类对话，SpeakerRoleFilter会认为她不是说话角色")
print("但这与GT标注矛盾（GT标注她是speaking_persons）")
print("问题可能是：GT标注她说话，但实际文本中她的对话没有明确的说话人标识")
