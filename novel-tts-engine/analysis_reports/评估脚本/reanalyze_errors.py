"""按用户标准重新评估测试结果"""
import json
from collections import Counter

with open('test_report_full.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

errs = d['short_tests_mode_b']['errors']
total = d['short_tests_mode_b']['total']
correct_orig = d['short_tests_mode_b']['correct']

print('=== 用户标准：返回"未知"=符合需求，修饰词宽泛=正确 ===')
print()
print(f'原始：正确 {correct_orig}/{total} ({correct_orig/total:.1%})')
print()

# 1. FP 但 actual='未知' → 正确（原则2：不确定返回未知）
fp_unknown = [e for e in errs if e['type'] == 'false_positive' and e['actual'] == '未知']

# 2. FP 但 actual 是具体人 → 仍错误
modifier_fps = [e for e in errs if e['type'] == 'false_positive' and e['actual'] not in ('未知',)]

# 3. mismatch actual='未知', expected 有具体人 → 仍错误
mismatch_unknown = [e for e in errs if e['type'] == 'mismatch' and e['actual'] == '未知']

# 4. mismatch wrong name → 仍错误
mismatch_wrong = [e for e in errs if e['type'] == 'mismatch' and e['actual'] != '未知']

# 5. FN → 仍错误
fns = [e for e in errs if e.get('type') == 'false_negative' or e['actual'] == '(未检测到)']

print(f'FP + actual="未知": {len(fp_unknown)} → 重新分类为正确')
print(f'FP + actual=具体人: {len(modifier_fps)} → 仍错误')
print(f'mismatch actual="未知": {len(mismatch_unknown)} → 仍错误')
print(f'mismatch wrong name: {len(mismatch_wrong)} → 仍错误')
print(f'FN: {len(fns)} → 仍错误')
print()

reclassified = len(fp_unknown)
new_correct = correct_orig + reclassified
new_accuracy = new_correct / total
remaining_errors = len(errs) - len(fp_unknown)

print(f'=== 重新分类后 ===')
print(f'重新分类为正确: {reclassified} 条')
print(f'新正确数: {new_correct}/{total}')
print(f'新准确率: {new_accuracy:.1%}')
print(f'剩余真实错误: {remaining_errors} 条')
print()

remaining_types = Counter()
for e in errs:
    if e not in fp_unknown:
        if e['type'] == 'false_positive':
            remaining_types[f'FP(实际={e["actual"]})'] += 1
        elif e['type'] == 'mismatch':
            if e['actual'] == '未知':
                remaining_types['mismatch(返回未知)'] += 1
            else:
                remaining_types['mismatch(选错人)'] += 1
        else:
            remaining_types[e['type']] += 1

print(f'=== 剩余 {remaining_errors} 个真实错误分布 ===')
for t, c in remaining_types.most_common():
    print(f'  {t}: {c}')

print()
print(f'=== FP 中 actual=具体人的示例 (前10) ===')
for e in modifier_fps[:10]:
    print(f'  {e["para_id"]}: actual="{e["actual"]}" | {e["dialogue"]}')

print()
print(f'=== mismatch 选错人典型示例 (前15) ===')
for e in mismatch_wrong[:15]:
    print(f'  {e["para_id"]}: 期望={e["expected"]} 实际="{e["actual"]}" | {e["dialogue"]}')
