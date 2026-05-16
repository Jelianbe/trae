import json

# 加载旧数据集
with open(r'd:\trae\novel-tts-engine\tests\role_emotion_gt_100.json', encoding='utf-8') as f:
    old_data = json.load(f)

# 加载新数据集
with open(r'd:\trae\novel-tts-engine\tests\role_emotion_gt_expanded.json', encoding='utf-8') as f:
    new_data = json.load(f)

print(f'旧数据集: {len(old_data)} 条')
print(f'  ID范围: {old_data[0]["id"]} ~ {old_data[-1]["id"]}')
print(f'新数据集: {len(new_data)} 条')
print(f'  ID范围: {new_data[0]["id"]} ~ {new_data[-1]["id"]}')

# 检查是否有重复ID
old_ids = set(item['id'] for item in old_data)
new_ids = set(item['id'] for item in new_data)
overlap = old_ids & new_ids
if overlap:
    print(f'\n警告: 发现 {len(overlap)} 个重复ID: {sorted(overlap)}')
else:
    print('\n无重复ID，可以合并')

# 合并
merged = old_data + new_data
print(f'\n合并后总计: {len(merged)} 条')
print(f'ID范围: {merged[0]["id"]} ~ {merged[-1]["id"]}')

# 保存
output_path = r'd:\trae\novel-tts-engine\tests\role_emotion_gt_300.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f'已保存到 {output_path}')

# 统计文体分布
styles = {}
for item in merged:
    s = item.get('style', 'unknown')
    styles[s] = styles.get(s, 0) + 1
print(f'\n文体分布:')
for s, c in sorted(styles.items(), key=lambda x: -x[1]):
    print(f'  {s}: {c} 条')
