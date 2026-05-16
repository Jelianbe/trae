import re
from pathlib import Path

text_path = Path('tests/urban_long_text_test.txt')
with open(text_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

non_empty = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]

# Look at lines around "赵总监皱起眉头"
for idx in range(5, 15):
    line_num, text = non_empty[idx]
    print(f'Line {line_num}: {text}')
    print()
