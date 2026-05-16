"""分析测试报告中的错误分类"""
import json
from collections import Counter

with open('test_report_full.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

errs = d['short_tests_mode_b']['errors']
print(f'总错误: {len(errs)}')

types = Counter(e['type'] for e in errs)
print('\n=== 按错误类型 ===')
for t, c in types.most_common(): print(f'  {t}: {c}')

actuals = Counter(e['actual'] for e in errs)
print('\n=== 实际返回值 Top20 ===')
for a, c in actuals.most_common(20): print(f'  "{a}" = {c}')

# Mismatch细分类
mismatches = [e for e in errs if e['type'] == 'mismatch']
noise_chars = set('着说道问喊骂叫怒叹咬牙呐喝嚷急沉冷冷淡淡')

unknown = [e for e in mismatches if e['actual'] == '未知']
noise = [e for e in mismatches if e['actual'] != '未知' and any(ch in e['actual'] for ch in noise_chars)]
wrong = [e for e in mismatches if e['actual'] != '未知' and not any(ch in e['actual'] for ch in noise_chars)]

print(f'\n=== Mismatch 细分类 (共{len(mismatches)}) ===')
print(f'  返回"未知": {len(unknown)} 条 — HanLP NER未能提取人物名')
print(f'  噪声文本: {len(noise)} 条 — NER取了说话动词/情绪修饰词')
print(f'  角色匹配错: {len(wrong)} 条 — 有候选人但选错了')

# FP分析
fps = [e for e in errs if e['type'] == 'false_positive']
# 分来源
fp_cats = Counter()
for e in fps:
    pid = e['para_id']
    if pid.startswith('GT-'):
        fp_cats['GT:长文本提取'] += 1
    elif pid.startswith('A'):
        fp_cats['A:非对话(地名/物品/拟声/强调/独白)'] += 1
    elif pid.startswith('B'):
        fp_cats['B:实体误判(物品/地名/组织/概念/形容词)'] += 1
    elif pid.startswith('D'):
        fp_cats['D:未知/文献'] += 1
    elif pid.startswith('F'):
        fp_cats['F:旁白引用/内心独白'] += 1
    elif pid.startswith('H-'):
        fp_cats['H:历史用例'] += 1
    else:
        fp_cats[f'Other:{pid[:5]}'] += 1

print(f'\n=== False Positive 来源 (共{len(fps)}) ===')
for c, n in fp_cats.most_common(): print(f'  {c}: {n}')

# 错误集中ID分析
error_ids = Counter(e['para_id'] for e in errs)
print(f'\n=== 错误最多的用例 Top15 ===')
for pid, cnt in error_ids.most_common(15):
    exps = set(e['expected'] for e in errs if e['para_id'] == pid)
    acts = set(e['actual'] for e in errs if e['para_id'] == pid)
    print(f'  {pid}: {cnt}错误 | 期望={list(exps)[:3]} | 实际={list(acts)[:3]}')

print('\n=== 噪声文本具体值(唯一值) ===')
noise_vals = Counter(e['actual'] for e in noise)
for v, c in noise_vals.most_common(20):
    examples = [e['dialogue'] for e in noise if e['actual'] == v]
    print(f'  "{v}" ({c}次) 例: {examples[:2]}')

print('\n=== 返回"未知"典型场景 ===')
uk_examples = {}
for e in unknown:
    key = e['para_id'][:5]
    if key not in uk_examples:
        uk_examples[key] = []
    if len(uk_examples[key]) < 2:
        uk_examples[key].append((e['expected'], e['dialogue']))
for k, v in sorted(uk_examples.items()):
    for exp, dia in v:
        print(f'  [{k}] 期望={exp} | {dia}')

print('\n=== 角色匹配错误(选错人)典型 ===')
for e in wrong[:20]:
    print(f'  {e["para_id"]}: 期望={e["expected"]} 实际={e["actual"]} | {e["dialogue"]}')
