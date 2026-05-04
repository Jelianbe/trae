import re
import os

SRC = r"D:\trae\novel-tts-engine\诡秘之主(1-500章).txt"
DST = r"D:\trae\novel-tts-engine\tests\test_novel_guimi_ch1-10.txt"

with open(SRC, "r", encoding="utf-8") as f:
    lines = f.readlines()

chapters = []
for i, line in enumerate(lines):
    m = re.match(r"^第(\d+)章", line.strip())
    if m:
        ch_num = int(m.group(1))
        if ch_num <= 11:
            chapters.append((ch_num, i))

for ch_num, line_idx in chapters:
    print(f"第{ch_num}章 at line {line_idx}: {lines[line_idx].strip()[:40]}")

ch11_line = next(idx for num, idx in chapters if num == 11)
print(f"\nExtracting lines 5 to {ch11_line-1} (chapters 1-10)")

extracted = lines[5:ch11_line]
with open(DST, "w", encoding="utf-8") as f:
    f.writelines(extracted)

print(f"Written {len(extracted)} lines")
print(f"File size: {os.path.getsize(DST)} bytes")
