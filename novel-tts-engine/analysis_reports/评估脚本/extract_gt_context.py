"""为GT短用例提取完整段落上下文，解决184条'未知'中大部分因缺上下文导致的错误"""
import sys, os, re, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

GT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'tests')

# Novel files corresponding to each GT
NOVEL_FILES = {
    '修仙': 'test_novel.txt',
    '都市异能': 'test_novel_urban.txt',
    '西幻': 'test_novel_western.txt',
    '玄幻(斗破)': 'test_novel_doupo_ch1-10.txt',
}

GT_FILES = {
    '修仙': 'test_novel_ground_truth.json',
    '都市异能': 'test_novel_urban_ground_truth.json',
    '西幻': 'test_novel_western_ground_truth.json',
    '玄幻(斗破)': 'test_novel_doupo_ground_truth.json',
}

def normalize_quotes(text):
    """Normalize quote formats for matching"""
    for old in ['\u201c', '\u201d', '\u2018', '\u2019']:
        text = text.replace(old, '"')
    return text

def extract_full_paragraph(novel_content, dialogue_text):
    """在小说内容中找到包含该对话的完整段落"""
    # 尝试多种匹配方式
    clean_dialogue = normalize_quotes(dialogue_text).strip().strip('"')
    if not clean_dialogue:
        return dialogue_text  # 无法匹配，返回原文

    # 将小说内容按段落分割
    paragraphs = re.split(r'\n\s*\n', novel_content)
    
    # 第一优先：精确匹配（含引号）
    for quote in ['"', '"', '"', '"']:
        target = f'{quote}{clean_dialogue}{quote}'
        for para in paragraphs:
            if target in para:
                return para.strip()
    
    # 第二优先：匹配对话内容（不含引号）
    for para in paragraphs:
        para_clean = normalize_quotes(para)
        if clean_dialogue in para_clean:
            return para.strip()
    
    # 第三优先：模糊匹配（去除部分标点）
    fuzzy_dialogue = re.sub(r'[！？，。……]', '', clean_dialogue)
    if len(fuzzy_dialogue) > 5:  # 只匹配长度足够的内容
        for para in paragraphs:
            para_clean = normalize_quotes(para)
            para_fuzzy = re.sub(r'[！？，。……]', '', para_clean)
            if fuzzy_dialogue in para_fuzzy:
                return para.strip()
    
    # 无法匹配：返回原始对话文本
    return dialogue_text

def extract_dialogue_sentences(novel_content):
    """从小说中提取所有对话句子，用于定位"""
    # 匹配引号内的内容
    pattern = r'[""""][^"""""]+[""""]'
    return re.findall(pattern, novel_content)

def main():
    print("=" * 70)
    print(" 为GT短用例提取完整段落上下文")
    print("=" * 70)
    
    # Load existing unified test cases
    from test_data_unified import UNIFIED_TEST_CASES
    
    # Filter existing cases to find GT- cases
    existing_gt_ids = set(c['id'] for c in UNIFIED_TEST_CASES if c['source'] == 'gt_json')
    
    results = []
    stats = {
        'total': 0,
        'matched_paragraph': 0,
        'no_match': 0,
    }
    
    for style_key, gt_file in GT_FILES.items():
        novel_file = NOVEL_FILES[style_key]
        
        # Load GT
        gt_path = os.path.join(GT_DIR, gt_file)
        if not os.path.exists(gt_path):
            print(f"\n⚠️  跳过 {style_key}: GT文件不存在")
            continue
        
        with open(gt_path, 'r', encoding='utf-8') as f:
            gt = json.load(f)
        
        # Load novel
        novel_path = os.path.join(GT_DIR, novel_file)
        if not os.path.exists(novel_path):
            print(f"\n⚠️  跳过 {style_key}: 小说文件不存在")
            continue
        
        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_content = f.read()
        
        print(f"\n📂 处理 {style_key}...")
        print(f"  小说长度: {len(novel_content)} 字符")
        
        dialogue_items = gt.get('dialogue_speakers', [])
        
        for i, item in enumerate(dialogue_items):
            dialogue_text = item.get('text', '')
            speaker = item.get('speaker', '未知')
            
            # Extract full paragraph
            full_para = extract_full_paragraph(novel_content, dialogue_text)
            
            stats['total'] += 1
            
            if full_para != dialogue_text:
                stats['matched_paragraph'] += 1
                results.append({
                    'gt_id': f"GT-{style_key}-{i+1:03d}",
                    'dialogue_text': dialogue_text,
                    'speaker': speaker,
                    'full_paragraph': full_para,
                    'style': style_key,
                    'has_context': True,
                })
            else:
                stats['no_match'] += 1
                results.append({
                    'gt_id': f"GT-{style_key}-{i+1:03d}",
                    'dialogue_text': dialogue_text,
                    'speaker': speaker,
                    'full_paragraph': dialogue_text,  # fallback
                    'style': style_key,
                    'has_context': False,
                })
            
            if i % 20 == 0:
                print(f"  处理 {i}/{len(dialogue_items)}...")
        
        print(f"  ✅ {style_key} 完成: {len(dialogue_items)} 条对话")
    
    print(f"\n{'='*70}")
    print(f"  统计结果")
    print(f"{'='*70}")
    print(f"  总条目: {stats['total']}")
    print(f"  成功匹配到段落: {stats['matched_paragraph']} ({stats['matched_paragraph']/stats['total']:.1%})")
    print(f"  未匹配到段落: {stats['no_match']} ({stats['no_match']/stats['total']:.1%})")
    
    # Save results for inspection
    output_path = os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 映射结果已保存: {output_path}")
    
    # Show a few examples
    print(f"\n📋 示例（前3条有上下文的）:")
    examples = [r for r in results if r['has_context']][:3]
    for ex in examples:
        print(f"\n  [{ex['gt_id']}] {ex['speaker']}:")
        print(f"  对话: {ex['dialogue_text'][:60]}...")
        print(f"  段落: {ex['full_paragraph'][:100]}...")
    
    return results

if __name__ == '__main__':
    main()
