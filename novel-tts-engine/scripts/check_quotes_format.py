#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查小说文件中的引号格式"""
import re

with open('《斗破苍穹》【爱上阅读_www.isyd.net】.txt', 'r', encoding='utf-8') as f:
    content = f.read(5000)

# 检查中文引号
quotes_cn = re.findall(r'\u201c(.*?)\u201d', content)
print(f"中文引号 \\u201c\\u201d: {len(quotes_cn)} 个")
if quotes_cn:
    for q in quotes_cn[:3]:
        print(f"  - {q[:50]}")

# 检查英文引号
quotes_en = re.findall(r'"(.*?)"', content)
print(f"英文引号: {len(quotes_en)} 个")

# 打印前100个字符看看
print(f"\n前100字符: {repr(content[:100])}")

# 查找包含对话的段落
paragraphs = content.split('\n')
for i, para in enumerate(paragraphs[:20]):
    if '\u201c' in para or '"' in para:
        print(f"\n段落{i}: {para[:100]}")
