import json

data = json.load(open(r'd:\trae\novel-tts-engine\tests\role_emotion_gt_expanded.json', encoding='utf-8'))
print(f'总条数: {len(data)}')
print(f'第一条 ID: {data[0]["id"]}')
print(f'最后一条 ID: {data[-1]["id"]}')
print(f'\n样例:')
print(json.dumps(data[0], ensure_ascii=False, indent=2)[:500])

# 检查关键字段完整性
required_fields = ['id', 'text', 'context_before', 'context_after', 'style', 'speaker']
missing = []
for i, item in enumerate(data):
    for field in required_fields:
        if field not in item:
            missing.append((i, item.get('id', 'unknown'), field))

if missing:
    print(f'\n警告: {len(missing)} 条记录缺少必要字段')
    for idx, item_id, field in missing[:5]:
        print(f'  [{idx}] {item_id} 缺少 {field}')
else:
    print(f'\n所有 {len(data)} 条记录均包含必要字段')
