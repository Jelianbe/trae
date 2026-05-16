"""分析都市长文本基线错误模式"""

import json
from pathlib import Path

result_path = Path(__file__).parent / 'urban_long_text_baseline_result.json'
with open(result_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

errors = [r for r in data['results'] if r['status'] == 'WRONG']

# 分析错误类型
patterns = {}
for e in errors:
    mt = e['match_type']
    if '描述性角色' in mt:
        cat = '描述性角色误匹配(非角色库描述被当角色)'
    elif '近因' in mt:
        cat = '近因效应(粘着最近说话人)'
    else:
        cat = f'其他({mt})'
    patterns[cat] = patterns.get(cat, 0) + 1

print(f"{'='*60}")
print(f"错误模式分析")
print(f"{'='*60}")
for cat, count in sorted(patterns.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count} 条 ({count/len(errors)*100:.1f}%)")

print(f"\n总错误: {len(errors)}/{data['judgable']}")
print(f"准确率: {data['correct']}/{data['judgable']} = {data['accuracy']*100:.1f}%")

# 检查连续错误
print(f"\n错误分布:")
consecutive_errors = 0
max_consecutive = 0
current_streak = 0
for r in data['results']:
    if r['status'] == 'WRONG':
        current_streak += 1
        if current_streak > max_consecutive:
            max_consecutive = current_streak
    else:
        current_streak = 0

print(f"  最大连续错误: {max_consecutive} 条")

# 列出前10个错误详情
print(f"\n前10个错误详情:")
for e in errors[:10]:
    print(f"  [{e['index']:3d}] {e['text'][:20]} | 预期={e['expected']} 预测={e['predicted']} | {e['match_type']}")
