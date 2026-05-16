# -*- coding: utf-8 -*-
"""Debug: trace entity_cleaner filtering for "修士" """
import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

from pipeline.entity_cleaner import EntityCleaner, get_entity_cleaner

ec = get_entity_cleaner()

# Simulate what happens with "修士" + a text containing "修士们"
test_text = "修士们鱼贯而入。孙项明站在人群中。"
test_entities = [("修士", "PER"), ("孙项明", "PER")]
cleaned = ec.clean(test_entities, test_text)
print(f"\n输入: {test_entities}")
print(f"输出: {cleaned}")
print(f"期望: [('孙项明', 'PER')]")
assert cleaned == [("孙项明", "PER")], f"FAIL: {cleaned}"
print("✅ entity_cleaner 过滤正确")
