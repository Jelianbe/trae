import re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
with open(str(project_root / 'tests' / 'urban_long_text_test.txt'), 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f.readlines() if l.strip()]

has_prefix = 0
no_prefix = 0
for l in lines:
    if '"' in l or "'" in l:
        m = re.search(r'["""](.+?)["""]', l)
        if m:
            colon = l.find('\uff1a')
            q = l.find('"')
            if q == -1: q = l.find("'")
            if colon >= 0 and q >= 0 and colon < q:
                has_prefix += 1
            else:
                no_prefix += 1

print(f'有旁白前缀的对话行: {has_prefix}')
print(f'无旁白前缀的纯对话行: {no_prefix}')
print(f'合计: {has_prefix + no_prefix}')
