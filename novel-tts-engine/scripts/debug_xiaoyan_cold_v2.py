# -*- coding: utf-8 -*-
"""
调试"萧炎冷"在统计验证阶段的处理
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp, Entity
from pipeline.context_diversity_validator import get_context_validator

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

print("=" * 80)
print("调试'萧炎冷'统计验证")
print("=" * 80)

# 获取NER结果
nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']

# 查找"萧炎冷"
xiaoyan_cold_entities = [e for e in per_entities if '炎冷' in e.text or '萧炎冷' == e.text]
print(f"\n【基础NER中'萧炎冷'相关实体】")
for e in xiaoyan_cold_entities:
    print(f"  实体: '{e.text}', confidence={e.confidence:.2f}")

# 统计"萧炎冷"在全文中的出现情况
import re
pattern = re.compile('萧炎冷')
matches = list(pattern.finditer(text))
print(f"\n【'萧炎冷'在全文中的出现次数】: {len(matches)}")

if matches:
    for m in matches[:5]:
        start = max(0, m.start() - 20)
        end = min(len(text), m.end() + 20)
        context = text[start:end]
        print(f"  位置 {m.start()}: ...{context}...")

# 统计"萧炎"的出现情况
xiaoyan_pattern = re.compile('萧炎')
xiaoyan_matches = list(xiaoyan_pattern.finditer(text))
print(f"\n【'萧炎'在全文中的出现次数】: {len(xiaoyan_matches)}")

# 运行统计验证
validator = get_context_validator(mode='speaker_role', whitelist=set())

# 检查validate方法内部
# 先调用discover_compound_entities
discovered = validator.discover_compound_entities(text, per_entities)
print(f"\n【discover_compound_entities发现的实体】")
for e in discovered:
    print(f"  {e.text}: confidence={e.confidence:.2f}")

# 检查"萧炎冷"是否在discovered中
discovered_texts = set(e.text for e in discovered)
if '萧炎冷' in discovered_texts:
    print("  ⚠️ '萧炎冷'在discover_compound_entities中产生了！")

# 现在运行完整的validate
validated = validator.validate(per_entities, text)

print(f"\n【validate后'萧炎冷'相关实体】")
for e in validated:
    if '炎冷' in e.text or '萧炎冷' == e.text:
        print(f"  实体: '{e.text}', confidence={e.confidence:.2f}")

# 检查统计结果
from pipeline.context_diversity_validator import ContextDiversityValidator
temp_validator = ContextDiversityValidator(mode='speaker_role', whitelist=set())

# 手动收集统计信息
all_entities = per_entities + discovered
entity_positions = {}
for e in all_entities:
    if e.text not in entity_positions:
        entity_positions[e.text] = []
    entity_positions[e.text].append((e.start, e.end))

stats = temp_validator._collect_context_stats(all_entities, text)

if '萧炎冷' in stats:
    xiaoyan_cold_stats = stats['萧炎冷']
    print(f"\n【'萧炎冷'的统计信息】")
    print(f"  occurrences: {xiaoyan_cold_stats['occurrences']}")
    print(f"  right_neighbors: {xiaoyan_cold_stats['right_neighbors']}")
    print(f"  boundary_hit_templates: {xiaoyan_cold_stats['boundary_hit_templates']}")
    print(f"  boundary_hit_total: {xiaoyan_cold_stats['boundary_hit_total']}")
    
    # 模拟_calculate_confidence
    from dataclasses import dataclass
    test_entity = Entity(text='萧炎冷', type='PER', start=0, end=3, confidence=0.9)
    new_conf = temp_validator._calculate_confidence(test_entity, xiaoyan_cold_stats)
    print(f"\n【_calculate_confidence结果】")
    print(f"  原始confidence: 0.9")
    print(f"  计算后confidence: {new_conf:.2f}")

print("\n" + "=" * 80)
