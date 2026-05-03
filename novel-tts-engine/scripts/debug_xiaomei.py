# -*- coding: utf-8 -*-
"""
调试萧媚为什么没有被识别
"""
import sys
from pathlib import Path
import json
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import get_context_validator

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

nlp = get_nlp()
result = nlp.analyze(text)

# 查找所有包含"媚"的实体
mei_entities = [e for e in result.entities if '媚' in e.text]
print("=" * 80)
print("调试萧媚")
print("=" * 80)

print(f"\n【基础NER中包含'媚'的实体】")
for e in mei_entities:
    print(f"  text={e.text}, type={e.type}, confidence={e.confidence:.2f}, start={e.start}, end={e.end}")

# 统计萧媚在全文中的出现
xiaomei_pattern = re.compile('萧媚')
matches = list(xiaomei_pattern.finditer(text))
print(f"\n【'萧媚'在全文中的出现次数】: {len(matches)}")

# 检查统计验证后
validator = get_context_validator(mode='speaker_role', whitelist=set())
validated = validator.validate(result.entities, text)

xiaomei_after = [e for e in validated if '媚' in e.text]
print(f"\n【统计验证后包含'媚'的实体】")
for e in xiaomei_after:
    print(f"  text={e.text}, confidence={e.confidence:.2f}")

# 打印前3个"萧媚"的上下文
print(f"\n【'萧媚'的上下文】")
for m in matches[:3]:
    start = max(0, m.start() - 30)
    end = min(len(text), m.end() + 30)
    context = text[start:end].replace('\n', ' ')
    print(f"  位置{m.start()}: ...{context}...")

print("\n" + "=" * 80)
