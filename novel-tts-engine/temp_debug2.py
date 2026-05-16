# -*- coding: utf-8 -*-
"""Debug: trace where "修士" enters the system"""
import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING)

from pipeline.entity_cleaner import EntityCleaner, reset_entity_cleaner
from pipeline.character_manager import reset_character_manager

# Reset singletons
reset_entity_cleaner()
reset_character_manager()

import os
if os.path.exists('data/characters.db'):
    os.remove('data/characters.db')

from pipeline.entity_cleaner import get_entity_cleaner
ec = get_entity_cleaner()

# Test with full chapter text
chapter1 = open(r'C:\Users\月笙如歌\Desktop\修仙传(1).txt', encoding='utf-8').read()
parts = chapter1.split('第2章')
ch1 = parts[0]

# Find "修士" in text
import re
matches = [m.start() for m in re.finditer('修士', ch1)]
print(f'"修士" 在第一章出现 {len(matches)} 次')
for m in matches:
    context = ch1[max(0,m-10):m+20]
    print(f'  ...{context}...')

# Check if "修士们" exists
print(f'\n"修士们" 在第一章: {"修士们" in ch1}')

# Test entity filtering
result = ec.clean([('修士', 'PER')], ch1)
print(f'\nentity_cleaner.clean([("修士","PER")], chapter_text) = {result}')
if not result:
    print('✅ "修士" 被过滤')
else:
    print('❌ "修士" 未被过滤')

# Also test with just "修士" without "们"
no_men = ch1.replace('修士们', '修道者')
result2 = ec.clean([('修士', 'PER')], no_men)
print(f'\nentity_cleaner.clean([("修士","PER")], text_without_们) = {result2}')
if not result2:
    print('✅ 也通过 CULTIVATION_CATEGORY_TERMS 过滤')
else:
    print('❌ 未过滤')
