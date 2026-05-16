"""统一测试用例完整性验证脚本"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))

from test_data_unified import UNIFIED_TEST_CASES

def verify_all():
    issues = []
    stats = {'total': len(UNIFIED_TEST_CASES), 'ok': 0, 'warn': 0, 'error': 0}
    
    required = ['id', 'source', 'category', 'paragraph', 'dialogues', 'note']
    valid_categories = {'dialogue', 'non_dialogue', 'unknown_speaker'}
    valid_sources = {'historical', 'new', 'gt_json'}
    
    # Per-case checks
    for case in UNIFIED_TEST_CASES:
        cid = case.get('id', '?')
        errors_this = []
        warns_this = []
        
        # 1. Required fields
        for f in required:
            if f not in case:
                errors_this.append(f"缺失字段: {f}")
        
        # 2. Valid source
        if case.get('source') not in valid_sources:
            errors_this.append(f"无效source: {case.get('source')}")
        
        # 3. Valid category
        if case.get('category') not in valid_categories:
            errors_this.append(f"无效category: {case.get('category')}")
        
        # 4. Dialogues structure
        dialogues = case.get('dialogues', [])
        if not isinstance(dialogues, list):
            errors_this.append("dialogues不是列表")
        else:
            for i, d in enumerate(dialogues):
                if not isinstance(d, dict):
                    errors_this.append(f"dialogues[{i}]不是dict")
                    continue
                if 'text' not in d:
                    errors_this.append(f"dialogues[{i}]缺失text")
                if 'speaker' not in d:
                    errors_this.append(f"dialogues[{i}]缺失speaker")
        
        # 5. Category-specific checks
        cat = case.get('category')
        if cat == 'non_dialogue' and len(dialogues) > 0:
            # Some non_dialogue cases (mixed) can have dialogues - check speaker
            for d in dialogues:
                spk = d.get('speaker', '')
                if spk in ('旁白（非对话）', '旁白', '非对话'):
                    errors_this.append(f"非对话类不应有旁白speaker: {spk}")
        
        if cat == 'unknown_speaker':
            if len(dialogues) == 0:
                warns_this.append("未知说话人类但无对话")
            for d in dialogues:
                spk = d.get('speaker', '')
                if spk not in ('未知',):
                    warns_this.append(f"未知说话人类但speaker={spk}（应为'未知'）")
        
        # 6. Paragraph content check
        para = case.get('paragraph', '')
        for d in dialogues:
            text = d.get('text', '')
            if text and text not in para:
                warns_this.append(f"对话'{text[:30]}...'未在段落中找到")
        
        # 8. ID format check
        id_patterns = [
            (r'^H-\d{3}$', '历史格式'),
            (r'^[A-F]\d+-\d+$', '分类-编号格式'),
            (r'^[A-F]\d+-混$', '分类-混合格式'),
            (r'^[A-F]\d+-\d+-补$', '分类-补充格式'),
            (r'^GT-[\u4e00-\u9fa5\(\)\w]+-\d{3}$', 'GT-文体-编号格式'),
        ]
        if not any(re.match(p, cid) for p, _ in id_patterns):
            warns_this.append(f"非常规ID格式: {cid}")
        
        # 8. Speaker name check (no stray commentary)
        for d in dialogues:
            spk = d.get('speaker', '')
            if spk.startswith('GROUP:'):
                continue  # 合法群组
            if spk in ('未知', ''):
                continue
            # Check for Chinese comma in speaker (indicates unparsed commentary)
            if '，' in spk:
                errors_this.append(f"speaker含中文逗号(未清理注释): '{spk}'")
            if '其中' in spk:
                errors_this.append(f"speaker含注释文本: '{spk}'")
            if '为同一角色' in spk:
                errors_this.append(f"speaker含注释文本: '{spk}'")
        
        if errors_this:
            stats['error'] += 1
            for e in errors_this:
                issues.append(f"❌ {cid}: {e}")
        elif warns_this:
            stats['warn'] += 1
            for w in warns_this:
                issues.append(f"⚠️ {cid}: {w}")
        else:
            stats['ok'] += 1
    
    return stats, issues

def print_summary():
    print("=" * 70)
    print(" 统一测试用例集 - 完整性验证报告")
    print("=" * 70)
    
    # Overall stats
    total = len(UNIFIED_TEST_CASES)
    by_cat = {}
    by_src = {}
    total_dialogues = 0
    for case in UNIFIED_TEST_CASES:
        cat = case['category']
        src = case['source']
        by_cat[cat] = by_cat.get(cat, 0) + 1
        by_src[src] = by_src.get(src, 0) + 1
        total_dialogues += len(case['dialogues'])
    
    print(f"\n📊 总体统计:")
    print(f"   总条目: {total}")
    print(f"   总对话: {total_dialogues}")
    print(f"   来源: {dict(by_src)}")
    print(f"   分类: {dict(by_cat)}")
    
    # Per-category dialogue count
    print(f"\n   每类对话数:")
    for cat in ['dialogue', 'unknown_speaker', 'non_dialogue']:
        d_count = sum(len(c['dialogues']) for c in UNIFIED_TEST_CASES if c['category'] == cat)
        n_count = by_cat.get(cat, 0)
        print(f"     {cat}: {n_count}条目, {d_count}对话")
    
    # Non-dialogue analysis
    nd_cases = [c for c in UNIFIED_TEST_CASES if c['category'] == 'non_dialogue']
    nd_with_d = [c for c in nd_cases if len(c['dialogues']) > 0]
    nd_empty = [c for c in nd_cases if len(c['dialogues']) == 0]
    print(f"\n   非对话类: {len(nd_empty)}条空对话, {len(nd_with_d)}条含对话(混合型)")
    if nd_with_d:
        for c in nd_with_d:
            print(f"     - {c['id']}: {c['note'][:60]}")
    
    # Unknown speaker analysis
    uk_cases = [c for c in UNIFIED_TEST_CASES if c['category'] == 'unknown_speaker']
    print(f"\n   未知说话人类: {len(uk_cases)}条")
    for c in uk_cases:
        spks = [d['speaker'] for d in c['dialogues']]
        print(f"     - {c['id']}: speakers={spks} | {c['note'][:50]}")
    
    # Speaker name analysis
    all_speakers = []
    for case in UNIFIED_TEST_CASES:
        for d in case.get('dialogues', []):
            all_speakers.append(d.get('speaker', ''))
    
    from collections import Counter
    spk_counts = Counter(all_speakers)
    print(f"\n📋 说话人分布 (前20):")
    for spk, count in spk_counts.most_common(20):
        print(f"   {spk:<20s}: {count}")
    
    # Run verification
    stats, issues = verify_all()
    print(f"\n🔍 字段级验证:")
    print(f"   ✅ 通过: {stats['ok']}")
    print(f"   ⚠️ 警告: {stats['warn']}")
    print(f"   ❌ 错误: {stats['error']}")
    
    if issues:
        print(f"\n   问题详情:")
        for iss in issues:
            print(f"   {iss}")
    
    # Overlap analysis
    print(f"\n🔄 重叠分析:")
    from collections import defaultdict
    text_to_ids = defaultdict(list)
    for case in UNIFIED_TEST_CASES:
        for d in case.get('dialogues', []):
            text_to_ids[d['text']].append(case['id'])
    
    overlaps = {k: v for k, v in text_to_ids.items() if len(v) > 1}
    if overlaps:
        print(f"   发现 {len(overlaps)} 组重叠对话文本:")
        for text, ids in sorted(overlaps.items(), key=lambda x: -len(x[1])):
            print(f"   \"{text[:50]}...\" → {ids}")
    else:
        print(f"   无重叠对话文本")
    
    # ID uniqueness
    ids = [c['id'] for c in UNIFIED_TEST_CASES]
    dup_ids = [id for id, cnt in Counter(ids).items() if cnt > 1]
    if dup_ids:
        print(f"\n⚠️ 重复ID: {dup_ids}")
    else:
        print(f"\n✅ 所有ID唯一")
    
    print(f"\n{'=' * 70}")
    print(f" 验证完成")
    print(f"{'=' * 70}")

if __name__ == '__main__':
    print_summary()
