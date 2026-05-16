"""构建统一测试用例集 - 合并历史数据与新数据"""
import sys, os, re, json

sys.path.insert(0, os.path.dirname(__file__))
from test_data_v6 import TEST_PARAGRAPHS as HISTORICAL_DATA
from new_cases_parsed import NEW_TEST_CASES

def normalize_historical():
    """将历史测试数据标准化为统一格式"""
    unified = []
    for item in HISTORICAL_DATA:
        unified.append({
            'id': f'H-{item["id"]:03d}',
            'source': 'historical',
            'category': 'dialogue',
            'paragraph': item['paragraph'],
            'dialogues': [
                {'text': d['text'], 'speaker': d['speaker']}
                for d in item['dialogues']
            ],
            'note': '',
        })
    return unified

def normalize_new():
    """将新测试用例标准化，修正非对话类处理"""
    unified = []
    for item in NEW_TEST_CASES:
        dialogues = item.get('dialogues', [])
        category = item.get('category', 'unknown')

        # For non-dialogue tests: the system should detect NO dialogues
        # So set dialogues to empty - these are negative tests
        if category == 'non_dialogue':
            # Check if all dialogues have "旁白（非对话）" or similar non-speaker
            all_non = all(
                d.get('speaker', '') in ('旁白（非对话）', '旁白', '非对话')
                for d in dialogues
            ) if dialogues else True

            if all_non:
                dialogues = []  # Empty = expect no dialogue detected
            # else: keep original for mixed cases

        # Normalize speaker names
        normalized_dialogues = []
        for d in dialogues:
            speaker = d.get('speaker', '未知')
            if speaker in ('旁白（非对话）', '旁白', '非对话'):
                # These are non-dialogue - should yield no dialogue result
                # Keep empty dialogues for this category
                continue
            normalized_dialogues.append({
                'text': d['text'],
                'speaker': speaker,
            })

        # If original category is non_dialogue and we normalized away all dialogues,
        # leave dialogues empty
        if category == 'non_dialogue' and not normalized_dialogues:
            pass  # keep empty
        elif normalized_dialogues:
            dialogues = normalized_dialogues
        elif category == 'non_dialogue':
            dialogues = []
        else:
            dialogues = normalized_dialogues

        unified.append({
            'id': item['id'],
            'source': 'new',
            'category': category,
            'paragraph': item['paragraph'],
            'dialogues': dialogues,
            'note': item.get('note', ''),
        })
    return unified

def post_process(new_cases):
    """修复解析器的已知边缘情况"""
    # E1/E2 用例：段落中的第一个引号是上下文对话，需补全到期望列表中
    e1_fixes = {
        'E1-1': [{'text': '老夫自有分寸。', 'speaker': '药尘'}],
        'E1-2': [{'text': '萧炎，你太冒进了。', 'speaker': '药老'}],
        'E1-3': [{'text': '林雪，这是你的丹药。', 'speaker': '孙项明'}],
        'E2-1': [{'text': '不想死就滚开。', 'speaker': '黑衣老者'}],
        'E2-2': [{'text': '小娃娃，此地危险。', 'speaker': '拄拐老妪'}],
        'E2-3': [{'text': '哼，不自量力。', 'speaker': '金袍少年'}],
    }
    for case in new_cases:
        cid = case['id']
        if cid in e1_fixes:
            # Prepend the context dialogue
            case['dialogues'] = e1_fixes[cid] + case['dialogues']

        # Clean D1 paragraphs: remove "(无)" noise prefix
        if cid in ('D1-1', 'D1-2', 'D1-3'):
            para = case['paragraph']
            para = para.replace('（无）', '')
            para = para.replace('（无上下文，单独一句）', '')
            case['paragraph'] = para.strip()

        # F1-3: 传音符内容，说话人未知 → 应归类为 unknown_speaker
        if cid == 'F1-3':
            case['category'] = 'unknown_speaker'
            case['dialogues'] = [{'text': '黑风谷出现异动，所有弟子速回！', 'speaker': '未知'}]

        # D3-1, D3-2: 书籍/石碑引用 → 应归类为 non_dialogue
        if cid in ('D3-1', 'D3-2'):
            case['category'] = 'non_dialogue'
            case['dialogues'] = []

    return new_cases

def check_overlaps(historical, new):
    """检查历史数据与新数据之间是否有重叠"""
    hist_texts = set()
    for h in historical:
        for d in h['dialogues']:
            hist_texts.add(d['text'])

    overlaps = []
    for n in new:
        for d in n['dialogues']:
            if d['text'] in hist_texts:
                overlaps.append((n['id'], d['text']))
    return overlaps

def analyze_format_consistency(all_data):
    """检查格式一致性"""
    issues = []

    # Check 1: All entries have required fields
    required_fields = ['id', 'source', 'category', 'paragraph', 'dialogues', 'note']
    for item in all_data:
        for field in required_fields:
            if field not in item:
                issues.append(f"缺失字段: {item.get('id', '?')} 缺少 '{field}'")

    # Check 2: dialogues structure
    for item in all_data:
        dialogues = item.get('dialogues', [])
        if not isinstance(dialogues, list):
            issues.append(f"dialogues非列表: {item['id']}")
            continue
        for i, d in enumerate(dialogues):
            if 'text' not in d:
                issues.append(f"缺失text: {item['id']}[{i}]")
            if 'speaker' not in d:
                issues.append(f"缺失speaker: {item['id']}[{i}]")

    # Check 3: Speaker naming conventions
    suspicious_speakers = []
    for item in all_data:
        for d in item.get('dialogues', []):
            spk = d.get('speaker', '')
            if spk.startswith('GROUP:'):
                continue  # 合法群组标记
            if spk in ('未知', '旁白（非对话）', ''):
                continue  # 合法特殊值
            # Check for obviously wrong speakers
            if spk in ('旁白', '非对话', '无'):
                suspicious_speakers.append(f"{item['id']}: speaker='{spk}'")

    if suspicious_speakers:
        issues.append(f"可疑的说话人标记: {suspicious_speakers}")

    # Check 4: ID format consistency
    id_formats = set()
    for item in all_data:
        id_val = item['id']
        if re.match(r'^H-\d{3}$', id_val):
            id_formats.add('H-NNN')
        elif re.match(r'^[A-F]\d+-\d+$', id_val):
            id_formats.add('LETTER-N-N')
        elif re.match(r'^[A-F]\d+-混$', id_val):
            id_formats.add('LETTER-N-混')
        elif re.match(r'^[A-F]\d+-\d+-补$', id_val):
            id_formats.add('LETTER-N-N-补')
        else:
            id_formats.add(f'OTHER: {id_val}')

    return issues, id_formats

def main():
    historical = normalize_historical()
    new_cases = normalize_new()

    # Post-processing: fix specific known issues
    post_process(new_cases)

    print(f"历史用例: {len(historical)} 段落, {sum(len(h['dialogues']) for h in historical)} 对话")
    print(f"新用例:   {len(new_cases)} 条目, {sum(len(n['dialogues']) for n in new_cases)} 对话")

    # Merge
    all_data = historical + new_cases
    print(f"合并后总计: {len(all_data)} 条目, {sum(len(d['dialogues']) for d in all_data)} 对话")

    # Category stats
    from collections import Counter
    cats = Counter(d['category'] for d in all_data)
    print(f"\n分类分布:")
    for cat, count in cats.most_common():
        d_count = sum(len(d['dialogues']) for d in all_data if d['category'] == cat)
        print(f"  {cat}: {count}条目, {d_count}对话")

    # Non-dialogue entries with empty dialogues
    non_dialogue_empty = sum(1 for d in all_data if d['category'] == 'non_dialogue' and len(d['dialogues']) == 0)
    non_dialogue_total = sum(1 for d in all_data if d['category'] == 'non_dialogue')
    print(f"\n非对话类: {non_dialogue_empty}/{non_dialogue_total} 正确设空")

    # Check overlaps
    overlaps = check_overlaps(historical, new_cases)
    if overlaps:
        print(f"\n发现可能重叠的对话: {len(overlaps)}条")
        for oid, text in overlaps[:10]:
            print(f"  {oid}: \"{text[:40]}...\"")

    # Format consistency check
    issues, id_formats = analyze_format_consistency(all_data)
    if issues:
        print(f"\n格式问题 ({len(issues)}):")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print(f"\n格式检查: 全部通过")

    print(f"\nID格式类型: {id_formats}")

    # Write unified file
    output_path = os.path.join(os.path.dirname(__file__), 'test_data_unified.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('"""统一测试用例集 v1.0\n')
        f.write('\n')
        f.write('合并来源:\n')
        f.write('  - test_data_v6.py (历史35段落，73对话)\n')
        f.write('  - 新建 文本文档.txt (新增75用例)\n')
        f.write('\n')
        f.write('字段说明:\n')
        f.write('  id: 用例唯一标识 (H-NNN=历史, A/B/C/D/E/F=分类)\n')
        f.write('  source: "historical" | "new"\n')
        f.write('  category: "dialogue" | "non_dialogue" | "unknown_speaker"\n')
        f.write('  paragraph: 完整段落文本\n')
        f.write('  dialogues: 对话列表 [{"text": "...", "speaker": "..."}]\n')
        f.write('    - speaker="未知" 表示说话人无法确定\n')
        f.write('    - dialogues=[] 表示段落中不应检测到对话\n')
        f.write('  note: 易错点/备注\n')
        f.write('"""\n\n')
        f.write('UNIFIED_TEST_CASES = [\n')

        for i, item in enumerate(all_data):
            f.write('  {\n')
            f.write(f'    "id": {json.dumps(item["id"], ensure_ascii=False)},\n')
            f.write(f'    "source": {json.dumps(item["source"], ensure_ascii=False)},\n')
            f.write(f'    "category": {json.dumps(item["category"], ensure_ascii=False)},\n')
            f.write(f'    "paragraph": {json.dumps(item["paragraph"], ensure_ascii=False)},\n')
            if item['dialogues']:
                f.write(f'    "dialogues": [\n')
                for d in item['dialogues']:
                    f.write(f'      {json.dumps(d, ensure_ascii=False)},\n')
                f.write(f'    ],\n')
            else:
                f.write(f'    "dialogues": [],\n')
            f.write(f'    "note": {json.dumps(item.get("note", ""), ensure_ascii=False)},\n')
            f.write('  },\n')

        f.write(']\n')

    print(f"\n统一测试文件已写入: {output_path}")
    return all_data

if __name__ == '__main__':
    all_data = main()
