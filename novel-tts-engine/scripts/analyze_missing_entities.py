# -*- coding: utf-8 -*-
"""
检查别名映射和漏报实体的出现情况
"""
import sys
from pathlib import Path
import json
import re
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

# 读取GT
gt_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ground_truth.json'
ground_truth = json.loads(gt_file.read_text(encoding='utf-8'))

gt_persons = set(ground_truth['entities']['persons'])
gt_aliases = ground_truth['entities']['aliases']

print("=" * 80)
print("检查漏报实体的出现情况")
print("=" * 80)

# 检查每个漏报实体在文本中的出现次数
missing = ['云山', '云韵', '药尘', '萧媚']
for name in missing:
    count = len(re.findall(re.escape(name), text))
    print(f"\n{name}: 出现{count}次")
    # 打印前3个上下文
    matches = list(re.finditer(re.escape(name), text))
    for m in matches[:3]:
        start = max(0, m.start() - 15)
        end = min(len(text), m.end() + 15)
        context = text[start:end]
        print(f"  ...{context}...")

# 检查别名映射
print(f"\n\n【别名映射检查】")
print(f"GT persons: {sorted(gt_persons)}")
print(f"GT aliases: {gt_aliases}")

# 检查药尘→药老的映射
if '药尘' in gt_aliases.get('药老', []):
    print(f"\n✅ 药尘是药老的别名")
    # 当预测到'药老'时，应该能匹配到GT中的'药尘'
    print(f"   预测'药老'应该匹配GT中的'药老'和'药尘'")

# 检查Belle
print(f"\n【萧媚检查】")
xiao_mei_count = len(re.findall('萧媚', text))
print(f"萧媚出现{xiao_mei_count}次")

# 检查云韵
print(f"\n【云韵检查】")
yun_yun_count = len(re.findall('云韵', text))
print(f"云韵出现{yun_yun_count}次")

# 检查云山
print(f"\n【云山检查】")
yun_shan_count = len(re.findall('云山', text))
print(f"云山出现{yun_shan_count}次")

# 检查这些实体是否在speaking_persons中
speaking_persons = set(ground_truth['entities']['speaking_persons'])
print(f"\n【说话角色检查】")
for name in missing:
    is_speaking = name in speaking_persons
    print(f"  {name}: {'是说话角色' if is_speaking else '非说话角色'}")

print("\n" + "=" * 80)
print("结论：")
print("=" * 80)
print("1. 药尘是药老的别名，预测'药老'应该能匹配GT'药尘'")
print("2. 云韵、云山不在speaking_persons中，可能被合理过滤")
print("3. 萧媚在speaking_persons中但出现次数可能不足")
