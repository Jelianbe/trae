"""合并4个GT JSON文件的对话数据到测试集，并分离长文本测试集"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))

from test_data_unified import UNIFIED_TEST_CASES

GT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'tests')

# 4 sets with GT JSON (short cases extracted)
GT_FILES = {
    'novel_xiuxian': {
        'gt': 'test_novel_ground_truth.json',
        'novel': 'test_novel.txt',
        'style': '修仙',
    },
    'novel_urban': {
        'gt': 'test_novel_urban_ground_truth.json',
        'novel': 'test_novel_urban.txt',
        'style': '都市异能',
    },
    'novel_western': {
        'gt': 'test_novel_western_ground_truth.json',
        'novel': 'test_novel_western.txt',
        'style': '西幻',
    },
    'novel_doupo': {
        'gt': 'test_novel_doupo_ground_truth.json',
        'novel': 'test_novel_doupo_ch1-10.txt',
        'style': '玄幻(斗破)',
    },
}

# All novels for long test set (incl. those without dialogue-level GT)
ALL_NOVELS = {
    **GT_FILES,
    'novel_guimi': {
        'gt': None,
        'novel': 'test_novel_guimi_ch1-10.txt',
        'style': '诡秘(闺秘)',
    },
}

def normalize_dialogue_text(text):
    """统一对话文本格式：去除引号、清理空白"""
    t = text.strip()
    for q in ['"', '"', '"', '\u201c', '\u201d', "'", '\u2018', '\u2019', '"', '"']:
        t = t.replace(q, '')
    return t.strip()

def extract_from_gt(gt_key, gt_file):
    """从GT JSON提取对话列表"""
    gt_path = os.path.join(GT_DIR, gt_file)
    if not os.path.exists(gt_path):
        print(f"  ⚠️  跳过 {gt_key}: 文件不存在")
        return []

    with open(gt_path, 'r', encoding='utf-8') as f:
        gt = json.load(f)

    info = GT_FILES[gt_key]
    style = info['style']
    novel_name = os.path.basename(info['novel']) if info['novel'] else gt.get('novel', 'unknown')

    dialogue_items = gt.get('dialogue_speakers', [])
    aliases_map = gt.get('entities', {}).get('aliases', {})

    extracted = []
    for item in dialogue_items:
        raw_text = item.get('text', '')
        speaker = item.get('speaker', '未知')
        clean_text = normalize_dialogue_text(raw_text)
        if not clean_text:
            continue

        extracted.append({
            'raw_text': raw_text,
            'clean_text': clean_text,
            'speaker': speaker,
            'style': style,
            'source_novel': novel_name,
            'aliases': aliases_map,
        })

    return extracted

def check_overlap(new_dialogues, existing_cases):
    """检查与现有用例的重叠"""
    existing_texts = set()
    for case in existing_cases:
        for d in case.get('dialogues', []):
            existing_texts.add(normalize_dialogue_text(d.get('text', '')))

    overlaps = []
    unique = []
    for d in new_dialogues:
        if d['clean_text'] in existing_texts:
            overlaps.append(d)
        else:
            existing_texts.add(d['clean_text'])
            unique.append(d)

    return overlaps, unique

def build_short_test_cases(unique_dialogues):
    """构建短文本测试用例（单对话条目）"""
    cases = []
    counter = {}

    for d in unique_dialogues:
        style = d['style']
        speaker = d['speaker']
        key = f"GT-{style}"

        if key not in counter:
            counter[key] = 0
        counter[key] += 1

        case_id = f"{key}-{counter[key]:03d}"
        paragraph = d['raw_text']

        cases.append({
            'id': case_id,
            'source': 'gt_json',
            'category': 'dialogue',
            'paragraph': paragraph,
            'dialogues': [
                {'text': d['clean_text'], 'speaker': speaker}
            ],
            'note': f"来源: {d['source_novel']} | 风格: {d['style']}",
        })

    return cases

def build_long_test_set():
    """构建长文本测试集（保留完整段落上下文和实体信息）"""
    long_sets = []

    for key, info in ALL_NOVELS.items():
        gt_path = os.path.join(GT_DIR, info['gt']) if info.get('gt') else None
        gt = None
        if gt_path and os.path.exists(gt_path):
            with open(gt_path, 'r', encoding='utf-8') as f:
                gt = json.load(f)

        novel_path = os.path.join(GT_DIR, info['novel']) if info.get('novel') else None
        novel_content = None
        if novel_path and os.path.exists(novel_path):
            with open(novel_path, 'r', encoding='utf-8') as nf:
                novel_content = nf.read()

        dialogue_speakers = gt.get('dialogue_speakers', []) if gt else []
        dialogue_sentences = gt.get('dialogue_sentences', []) if gt else []
        entities = gt.get('entities', {}) if gt else {}
        alias_map = gt.get('entities', {}).get('aliases', {}) if gt else {}

        # For novels without GT, try to extract basic info from annotation files
        annotation_path = None
        annotation_content = None
        if 'urban' in key:
            annotation_path = os.path.join(GT_DIR, 'test_novel_urban_annotation.txt')
            if os.path.exists(annotation_path):
                with open(annotation_path, 'r', encoding='utf-8') as af:
                    annotation_content = af.read()

        long_sets.append({
            'id': f"LONG-{key}",
            'style': info['style'],
            'novel_name': info.get('novel', 'N/A'),
            'novel_content': novel_content,
            'has_gt': gt is not None,
            'ground_truth': gt,
            'annotation_content': annotation_content,
            'dialogue_count': len(dialogue_speakers),
            'total_sentences': len(dialogue_sentences),
            'entities': entities,
            'aliases': alias_map,
        })

    return long_sets

def main():
    print("=" * 70)
    print(" 从 GT JSON 文件提取并合并测试用例")
    print("=" * 70)

    # 1. Extract from all GT files
    all_extracted = []
    for gt_key, gt_info in GT_FILES.items():
        print(f"\n📂 提取 {gt_key} ({gt_info['style']})...")
        extracted = extract_from_gt(gt_key, gt_info['gt'])
        print(f"  ✅ 提取 {len(extracted)} 条对话")
        all_extracted.extend(extracted)

    print(f"\n📊 总计提取: {len(all_extracted)} 条对话")

    from collections import Counter
    style_counts = Counter(d['style'] for d in all_extracted)
    for style, cnt in style_counts.items():
        print(f"  {style}: {cnt}")

    # 2. Check overlap with existing unified cases
    print(f"\n🔍 检查与现有 {len(UNIFIED_TEST_CASES)} 条用例的重叠...")
    overlaps, unique = check_overlap(all_extracted, UNIFIED_TEST_CASES)
    print(f"  重叠: {len(overlaps)} 条 (跳过)")
    print(f"  新增: {len(unique)} 条")

    if overlaps:
        print(f"\n  重叠示例:")
        for o in overlaps[:5]:
            print(f"    - \"{o['clean_text'][:50]}\" → {o['speaker']} ({o['style']})")

    # 3. Build short test cases
    short_cases = build_short_test_cases(unique)
    print(f"\n📝 生成短文本测试用例: {len(short_cases)} 条")

    # 4. Merge with existing
    merged = UNIFIED_TEST_CASES + short_cases
    print(f"📦 合并后总用例数: {len(merged)}")

    cats = Counter(c['category'] for c in merged)
    for cat, cnt in cats.items():
        d_count = sum(len(c['dialogues']) for c in merged if c['category'] == cat)
        print(f"  {cat}: {cnt}条, {d_count}对话")

    # 5. Write updated unified file
    unified_path = os.path.join(os.path.dirname(__file__), 'test_data_unified.py')
    with open(unified_path, 'w', encoding='utf-8') as f:
        f.write('"""统一测试用例集 v2.0\n')
        f.write('\n')
        f.write('合并来源:\n')
        f.write('  - test_data_v6.py (历史35段落，73对话)\n')
        f.write('  - 新建 文本文档.txt (新增75用例)\n')
        f.write('  - 4个 GT JSON 文件 (修仙/都市/西幻/斗破)\n')
        f.write('\n')
        f.write(f'总条目: {len(merged)}\n')
        f.write(f'总对话: {sum(len(c["dialogues"]) for c in merged)}\n')
        f.write('\n')
        f.write('字段说明:\n')
        f.write('  id: 用例唯一标识 (H-NNN=历史, A-F=分类, GT-风格=长文本提取)\n')
        f.write('  source: "historical" | "new" | "gt_json"\n')
        f.write('  category: "dialogue" | "non_dialogue" | "unknown_speaker"\n')
        f.write('  paragraph: 完整段落文本\n')
        f.write('  dialogues: 对话列表 [{"text": "...", "speaker": "..."}]\n')
        f.write('  note: 易错点/备注\n')
        f.write('"""\n\n')
        f.write('UNIFIED_TEST_CASES = [\n')

        for item in merged:
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

    print(f"\n✅ 统一测试文件已更新: {unified_path}")

    # 6. Build long test set
    long_sets = build_long_test_set()
    print(f"\n📚 长文本测试集: {len(long_sets)} 套")
    for ls in long_sets:
        has_gt = '✅' if ls['has_gt'] else '❌'
        print(f"  {has_gt} {ls['id']}: {ls['style']} | {ls['novel_name']} | {ls['dialogue_count']}对话 | {ls['total_sentences']}句子")

    # Write long test set
    long_path = os.path.join(os.path.dirname(__file__), 'test_data_long_text.py')
    with open(long_path, 'w', encoding='utf-8') as f:
        f.write('"""长文本测试集 (全文 Ground Truth)\n')
        f.write('\n')
        f.write('用途: 完整小说级别的端到端测试\n')
        f.write('注意: 运行耗时较长，建议单独执行\n')
        f.write('\n')
        f.write('字段说明:\n')
        f.write('  id: 测试集标识\n')
        f.write('  style: 文体风格\n')
        f.write('  novel_name: 小说文件名\n')
        f.write('  has_gt: 是否有对话级GT标注\n')
        f.write('  ground_truth: 完整 GT JSON 内容（如有）\n')
        f.write('  annotation_content: 人工标注文档内容（如有）\n')
        f.write('"""\n\n')
        f.write('LONG_TEXT_TEST_SETS = [\n')

        for ls in long_sets:
            f.write('  {\n')
            f.write(f'    "id": {json.dumps(ls["id"], ensure_ascii=False)},\n')
            f.write(f'    "style": {json.dumps(ls["style"], ensure_ascii=False)},\n')
            f.write(f'    "novel_name": {json.dumps(ls["novel_name"], ensure_ascii=False)},\n')
            f.write(f'    "has_gt": {ls["has_gt"]},\n')
            f.write(f'    "dialogue_count": {ls["dialogue_count"]},\n')
            f.write(f'    "total_sentences": {ls["total_sentences"]},\n')
            
            if ls['ground_truth']:
                gt = ls['ground_truth']
                f.write('    "ground_truth": {\n')
                f.write(f'      "novel": {json.dumps(gt.get("novel", ""), ensure_ascii=False)},\n')
                f.write(f'      "style": {json.dumps(gt.get("style", ""), ensure_ascii=False)},\n')
                f.write(f'      "dialogue_speakers": {json.dumps(gt.get("dialogue_speakers", []), ensure_ascii=False)},\n')
                f.write(f'      "entities": {json.dumps(gt.get("entities", {}), ensure_ascii=False)},\n')
                if 'dialogue_sentences' in gt:
                    # Store as a Python repr() string to preserve Python literals
                    sample = gt.get('dialogue_sentences', [])[:10]
                    f.write(f'      "dialogue_sentences_sample": {repr(sample)},\n')
                    f.write(f'      "dialogue_sentences_count": {len(gt.get("dialogue_sentences", []))},\n')
                f.write('    },\n')
            else:
                f.write('    "ground_truth": null,\n')

            # Include annotation content if available
            if ls.get('annotation_content'):
                f.write(f'    "annotation_content": {json.dumps(ls["annotation_content"], ensure_ascii=False)},\n')
            else:
                f.write('    "annotation_content": None,\n')

            f.write('  },\n')

        f.write(']\n')

    print(f"\n✅ 长文本测试集已生成: {long_path}")

    # Post-process: fix JSON null/false/true to Python equivalents
    with open(long_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(': false,', ': False,').replace(': false\n', ': False\n')
    content = content.replace(': null,', ': None,').replace(': null\n', ': None\n')
    content = content.replace(': true,', ': True,').replace(': true\n', ': True\n')
    content = content.replace('"ground_truth": null', '"ground_truth": None')
    content = content.replace('"annotation_content": null', '"annotation_content": None')
    with open(long_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✅ JSON→Python 字面量修复完成")

    return merged, long_sets

if __name__ == '__main__':
    main()
