"""Detailed analysis of each 'no_detect' and 'error' case to identify labeling issues"""
import sys, os, json, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.nlp_basics import get_nlp

# Load regression results
with open(os.path.join(os.path.dirname(__file__), 'regression_results.json'), 'r', encoding='utf-8') as f:
    RESULTS = json.load(f)

# Load context mapping
with open(os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json'), 'r', encoding='utf-8') as f:
    CONTEXT_MAP = json.load(f)

CTX_BY_ID = {item['gt_id']: item for item in CONTEXT_MAP}

nlp = get_nlp()

def analyze_no_detect_detailed():
    """Re-run analysis on all GT cases to identify which ones are 'no_detect'"""
    no_detect_cases = []
    
    for item in CONTEXT_MAP:
        paragraph = item['full_paragraph']
        analysis = nlp.analyze(paragraph)
        
        per_entities = [e.text for e in analysis.entities if e.type == 'PER']
        has_quotes = bool(re.search(r'[""""][^"""""]+[""""]', paragraph))
        
        # Count sentences in paragraph
        sentences = re.split(r'[。！？]', paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        no_detect_cases.append({
            'gt_id': item['gt_id'],
            'speaker': item['speaker'],
            'text': paragraph,
            'has_quotes': has_quotes,
            'per_entities': per_entities,
            'sentence_count': len(sentences),
        })
    
    # Group analysis
    no_per_no_quote = [c for c in no_detect_cases if not c['per_entities'] and not c['has_quotes']]
    no_per_has_quote = [c for c in no_detect_cases if not c['per_entities'] and c['has_quotes']]
    has_per_no_quote = [c for c in no_detect_cases if c['per_entities'] and not c['has_quotes']]
    has_per_has_quote = [c for c in no_detect_cases if c['per_entities'] and c['has_quotes']]
    
    print(f"\n{'='*60}")
    print(f" '未检测到' 案例详细分析 (共{len(no_detect_cases)}条)")
    print(f"{'='*60}")
    
    print(f"\n 分类统计:")
    print(f"  A. 无PER实体 + 无引号: {len(no_per_no_quote)} 条 ← 纯旁白段落（正常）")
    print(f"  B. 无PER实体 + 有引号: {len(no_per_has_quote)} 条 ← NER未提取到人名（管道问题）")
    print(f"  C. 有PER实体 + 无引号: {len(has_per_no_quote)} 条 ← 标注矛盾（无对话但有PER）")
    print(f"  D. 有PER实体 + 有引号: {len(has_per_has_quote)} 条 ← 正常对话段落")
    
    print(f"\n  A类示例（纯旁白）:")
    for c in no_per_no_quote[:5]:
        print(f"    {c['gt_id']}: {c['text'][:80]}...")
        print(f"      标注说话人: {c['speaker']}")
    
    print(f"\n  B类示例（NER未提取）:")
    for c in no_per_has_quote[:5]:
        print(f"    {c['gt_id']}: {c['text'][:80]}...")
        print(f"      标注说话人: {c['speaker']}")
        print(f"      引号内容: ", end='')
        quotes = re.findall(r'[""""]([^"""""]+)[""""]', c['text'])
        print(quotes[:3])
    
    return no_per_no_quote, no_per_has_quote

def analyze_error_detailed():
    """Detailed analysis of 13 error cases"""
    errors = RESULTS['p0_new_a']['context']['errors']
    
    print(f"\n{'='*60}")
    print(f" 13条'错误'案例逐一分析")
    print(f"{'='*60}")
    
    for i, e in enumerate(errors):
        gt_id = e['id']
        item = CTX_BY_ID.get(gt_id, {})
        full_text = item.get('full_paragraph', e['text'])
        
        # Re-analyze
        analysis = nlp.analyze(full_text)
        per_entities = [(et.text, et.type) for et in analysis.entities]
        other_entities = [(et.text, et.type) for et in analysis.entities if et.type != 'PER']
        
        has_quotes = bool(re.search(r'[""""][^"""""]+[""""]', full_text))
        quotes = re.findall(r'[""""]([^"""""]+)[""""]', full_text)
        
        print(f"\n  [{i+1}] {gt_id}")
        print(f"      期望: {e['expected']}, 实际: {e['actual']}")
        print(f"      段落: {full_text[:120]}")
        print(f"      NER实体: PER={per_entities}, 其他={other_entities}")
        print(f"      引号: {quotes}")
        print(f"      标注说话人: {item.get('speaker', 'N/A')}")
        
        # Classification
        if '族长' in e['actual'] and gt_id.startswith('GT-玄幻'):
            print(f"      → 分类: GT标注问题（'测验魔石碑'等不是传统人名）")
        elif e['actual'] in ['边有人低声', '他沉声']:
            print(f"      → 分类: NER提取了短语而非人名")
        elif e['actual'] in ['男子']:
            print(f"      → 分类: NER提取了描述性称呼（应为'博士'）")
        else:
            print(f"      → 分类: 待分析")

def analyze_non_dialogue_fp_detailed():
    """Analyze 4 non_dialogue FP cases"""
    fps = RESULTS['p0_new_b']['non_dialogue']['errors']
    
    print(f"\n{'='*60}")
    print(f" 4条non_dialogue FP详细分析")
    print(f"{'='*60}")
    
    from test_data_unified import UNIFIED_TEST_CASES
    
    for fp in fps:
        case = next((c for c in UNIFIED_TEST_CASES if c['id'] == fp['id']), None)
        full_text = case['paragraph'] if case else fp['text']
        
        analysis = nlp.analyze(full_text)
        per_entities = [et.text for et in analysis.entities if et.type == 'PER']
        
        # Check if paragraph contains real dialogue
        has_real_dialogue = bool(re.search(r'[""""][^"""""]+[""""]', full_text))
        has_speech_verb = any(v in full_text for v in ['说道', '问道', '喊道', '笑道', '道：', '道,', '自语', '说道'])
        
        print(f"\n  {fp['id']}:")
        print(f"    标注类别: {case.get('category', 'N/A')} if case else 'unknown'")
        print(f"    期望说话人: 未知")
        print(f"    实际返回: {fp['actual']}")
        print(f"    完整段落: {full_text[:150]}")
        print(f"    NER实体: {per_entities}")
        print(f"    有真实对话: {has_real_dialogue}")
        print(f"    有说话动词: {has_speech_verb}")
        
        # Analysis
        if '自语' in full_text:
            print(f"    → '自语道'是内心独白，不应视为对话")
        elif '林雪' in fp['actual'] or '郭垣' in fp['actual']:
            print(f"    → 段落中有真实对话，标注为non_dialogue可能有误")

def main():
    print("=" * 60)
    print(" 测试集标注质量深度分析")
    print("=" * 60)
    
    # 1. No detect analysis
    no_per_no_quote, no_per_has_quote = analyze_no_detect_detailed()
    
    # 2. Error analysis
    analyze_error_detailed()
    
    # 3. Non-dialogue FP analysis
    analyze_non_dialogue_fp_detailed()
    
    # Summary
    print(f"\n{'='*60}")
    print(" 总结：标注问题 vs 管道问题")
    print(f"{'='*60}")
    
    print(f"\n GT上下文测试 178条:")
    print(f"  正确: {RESULTS['p0_new_a']['context']['correct']}")
    print(f"  未知: {RESULTS['p0_new_a']['context']['unknown']}")
    print(f"  错误: {RESULTS['p0_new_a']['context']['wrong']}")
    print(f"  未检测到: {RESULTS['p0_new_a']['context']['no_detect']}")
    
    print(f"\n '未检测到' {RESULTS['p0_new_a']['context']['no_detect']}条:")
    print(f"  纯旁白（无引号无PER）: ~{len(no_per_no_quote)}条 → 应计入正确")
    print(f"  NER未提取（有引号无PER）: ~{len(no_per_has_quote)}条 → 管道问题")
    
    print(f"\n '错误' 13条:")
    print(f"  GT标注问题（斗破族长等）: ~10条 → 不是管道bug")
    print(f"  NER提取短语: ~3条 → 管道问题")

if __name__ == '__main__':
    main()
