import re, json
from pathlib import Path
from collections import Counter

project_root = Path(__file__).resolve().parent.parent.parent

with open(str(project_root / 'tests' / 'urban_long_text_test.txt'), 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f.readlines() if l.strip()]

with open(str(project_root / 'tests' / 'urban_long_text_answer_key.json'), 'r', encoding='utf-8') as f:
    answer_key = json.load(f)

# 找出所有对话行
dialogue_lines = []
for i, line in enumerate(lines):
    m = re.search(r'["""](.+?)["""]', line)
    if m:
        colon = line.find('\uff1a')
        q = line.find('"')
        if q == -1: q = line.find("'")
        has_prefix = (colon >= 0 and q >= 0 and colon < q)
        dialogue_lines.append({
            'idx': len(dialogue_lines),
            'line': line,
            'has_prefix': has_prefix,
            'expected': answer_key['dialogues'][len(dialogue_lines)]['speaker'] if len(dialogue_lines) < len(answer_key['dialogues']) else '?'
        })

print('=== 纯对话段内部模式统计 ===')
print()

# 分析每个纯对话段
pure_dialogue_blocks = []
i = 0
while i < len(dialogue_lines):
    if not dialogue_lines[i]['has_prefix']:
        start = i
        while i < len(dialogue_lines) and not dialogue_lines[i]['has_prefix']:
            i += 1
        block = dialogue_lines[start:i]
        speakers = [d['expected'] for d in block]
        unique_speakers = len(set(speakers))
        
        # 检查对话内容特征
        for d in block:
            # 称呼语检测
            vocative = re.match(r'["""]*([\u4e00-\u9fa5\u2027·]{2,4})[，,]', d['line'])
            # 自称检测
            first_person = bool(re.search(r'我[们]?[的]|我自己|咱[们]?', d['line']))
            # 第二人称
            second_person = bool(re.search(r'你[们]?|您[们]?|你的|您的', d['line']))
            # 语气词
            modal = bool(re.search(r'[啊呢吧嘛呀哦了嘛]', d['line']))
            
            d['has_vocative'] = bool(vocative)
            d['vocative_name'] = vocative.group(1) if vocative else None
            d['has_first_person'] = first_person
            d['has_second_person'] = second_person
            d['has_modal'] = modal
        
        pure_dialogue_blocks.append({
            'start': start + 1,
            'end': i,
            'count': len(block),
            'unique_speakers': unique_speakers,
            'speakers': speakers,
            'details': block
        })
    else:
        i += 1

# 统计分布
print(f'纯对话段总数: {len(pure_dialogue_blocks)}')
print(f'纯对话段总行数: {sum(b["count"] for b in pure_dialogue_blocks)}')
print()

print('=== 按说话人数量分类 ===')
by_speaker_count = Counter(b['unique_speakers'] for b in pure_dialogue_blocks)
for count, freq in sorted(by_speaker_count.items()):
    print(f'  {count}个不同说话人: {freq}段 ({sum(b["count"] for b in pure_dialogue_blocks if b["unique_speakers"]==count)}行)')
print()

# 分析各段特征
for block in pure_dialogue_blocks:
    print(f'--- 第{block["start"]}~{block["end"]}条 ({block["count"]}行, {block["unique_speakers"]}人) ---')
    print(f'  说话人: {" → ".join(block["speakers"])}')
    for d in block['details']:
        features = []
        if d['has_vocative']: features.append(f'称呼语:{d["vocative_name"]}')
        if d['has_first_person']: features.append('第一人称')
        if d['has_second_person']: features.append('第二人称')
        if d['has_modal']: features.append('语气词')
        print(f'  #{d["idx"]+1}: {d["expected"]} | {" | ".join(features) if features else "无特征"} | {d["line"][:50]}')
    print()
