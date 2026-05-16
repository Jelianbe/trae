import json

data = json.load(open('gt_context_mapping.json', encoding='utf-8'))
no_ctx = [d for d in data if not d['has_context']]

print(f'Unmatched: {len(no_ctx)}')
for d in no_ctx:
    print(f'  {d["gt_id"]}: {d["dialogue_text"][:50]}')
