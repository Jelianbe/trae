import json
import re
import sys
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

text_path = project_root / 'tests' / 'urban_long_text_test.txt'
answer_path = project_root / 'tests' / 'urban_long_text_answer_key.json'
result_path = project_root / 'tests' / 'urban_long_text_baseline_result.json'

with open(text_path, 'r', encoding='utf-8') as f:
    full_text = f.read()

with open(answer_path, 'r', encoding='utf-8') as f:
    answer_data = json.load(f)
    answers = {a['line']: a for a in answer_data['dialogues']}

with open(result_path, 'r', encoding='utf-8') as f:
    result_data = json.load(f)

errors = [d for d in result_data['results'] if d['status'] == 'WRONG']

# Error classification
error_categories = {
    'action_subject': [],      # 动作主语误导：旁白角色动作被误认为说话
    'address_confusion': [],   # 称呼误解："XX，xxx"被误判为XX说话
    'recency_decay': [],       # 近因衰减不足：最近说话人持续被匹配
    'candidate_pool': [],      # 候选池问题：正确角色不在候选池
    'other': []                # 其他
}

print("=" * 100)
print("45 条错误逐条深度分析")
print("=" * 100)

for err in errors:
    idx = err['index']
    expected = err['expected']
    predicted = err['predicted']
    match_type = err['match_type']
    dialogue = err['text']
    
    # Find context in full text
    search_text = dialogue[:30]
    pos = full_text.find(search_text)
    if pos == -1:
        continue
    
    # Get 200 chars before dialogue
    context_start = max(0, pos - 200)
    context_before = full_text[context_start:pos]
    
    # Classification logic
    category = 'other'
    reason = ''
    
    # Rule 1: Check if dialogue starts with a name + comma (address pattern)
    address_match = re.match(r'^["""]?(\S+)[，,]', dialogue)
    if address_match:
        addressed_name = address_match.group(1)
        if addressed_name == predicted and addressed_name != expected:
            category = 'address_confusion'
            reason = f'对话以"{addressed_name}"开头，系统误判为说话人'
    
    # Rule 2: Check if context_before has "predicted + action verb" pattern
    if category == 'other':
        action_verbs = ['翻开', '端起', '打开', '站起身', '皱起', '端起', '走到', '看向', '扫了', '看了看']
        for verb in action_verbs:
            if predicted + verb[:2] in context_before or f'{predicted[:2]}{verb[:2]}' in context_before:
                # Check if the action is NOT followed by speech verb
                pattern = re.compile(rf'{re.escape(predicted)}.{{0,15}}(?:翻开|端起|打开|站起身|皱起|走到|看向|扫了|看了看|点头|摇头)')
                if pattern.search(context_before):
                    # Check if there's NO speech verb after the action
                    speech_pattern = re.compile(rf'{re.escape(predicted)}.{{0,30}}(?:道|说|问|答|笑道)')
                    if not speech_pattern.search(context_before):
                        category = 'action_subject'
                        reason = f'旁白"{predicted}+动作"但无说话动词，系统误认为在说话'
                    break
    
    # Rule 3: Check if it's a recency decay issue (same character repeated)
    if category == 'other' and '近因衰减' in match_type:
        # Check if previous dialogue was also this character
        prev_idx = idx - 1
        for prev_err in errors:
            if prev_err['index'] == prev_idx:
                if prev_err['predicted'] == predicted:
                    category = 'recency_decay'
                    reason = f'连续匹配同一角色，近因衰减未生效'
                break
    
    # Rule 4: Check if expected character is missing from context
    if category == 'other':
        if expected not in context_before and expected not in dialogue:
            category = 'candidate_pool'
            reason = f'期望角色"{expected}"在上下文中未出现'
    
    # Add to category
    error_categories[category].append({
        'idx': idx,
        'expected': expected,
        'predicted': predicted,
        'match_type': match_type[:50],
        'dialogue': dialogue[:40],
        'context': context_before[-80:] if context_before else '',
        'reason': reason
    })

# Print results by category
for cat_name, cat_errors in error_categories.items():
    if not cat_errors:
        continue
    
    cat_labels = {
        'action_subject': '【A】动作主语误导',
        'address_confusion': '【B】称呼误解',
        'recency_decay': '【C】近因衰减不足',
        'candidate_pool': '【D】候选池问题',
        'other': '【E】其他'
    }
    
    print(f"\n{'=' * 80}")
    print(f"{cat_labels[cat_name]}: {len(cat_errors)} 条 ({len(cat_errors)/45*100:.0f}%)")
    print(f"{'=' * 80}")
    
    for e in cat_errors:
        print(f"\n  索引 {e['idx']:02d}: 期望={e['expected']:8s} 预测={e['predicted']:8s}")
        print(f"    对话: {e['dialogue']}")
        print(f"    上下文: ...{e['context']}")
        print(f"    原因: {e['reason']}")
        print(f"    match_type: {e['match_type']}")

# Summary
print(f"\n{'=' * 80}")
print("汇总统计")
print(f"{'=' * 80}")
print(f"{'类别':<20s} {'数量':>4s} {'占比':>6s}")
print("-" * 35)
for cat_name, cat_errors in error_categories.items():
    if not cat_errors:
        continue
    cat_labels = {
        'action_subject': '动作主语误导',
        'address_confusion': '称呼误解',
        'recency_decay': '近因衰减不足',
        'candidate_pool': '候选池问题',
        'other': '其他'
    }
    print(f"{cat_labels[cat_name]:<18s} {len(cat_errors):4d} {len(cat_errors)/45*100:5.0f}%")
print(f"{'总计':<18s} {45:4d} {100:5.0f}%")
