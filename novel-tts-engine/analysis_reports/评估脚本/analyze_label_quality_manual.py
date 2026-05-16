"""逐条检查回归测试中的每个'未检测到'和'错误'案例，人工标注修正"""
import sys, os, json, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load context mapping
with open(os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json'), 'r', encoding='utf-8') as f:
    CONTEXT_MAP = json.load(f)

# Load regression results
with open(os.path.join(os.path.dirname(__file__), 'regression_results.json'), 'r', encoding='utf-8') as f:
    RESULTS = json.load(f)

from pipeline.nlp_basics import get_nlp
nlp = get_nlp()

def get_actual_result(gt_id):
    """从回归测试结果中找到该gt_id的实际结果"""
    # We need to re-run evaluation to get exact results
    # For now, let's just analyze based on the error list
    errors = RESULTS['p0_new_a']['context']['errors']
    for e in errors:
        if e['id'] == gt_id:
            return 'error', e
    return 'unknown', None

def classify_paragraph(item):
    """人工分类每个段落"""
    text = item['full_paragraph']
    speaker = item['speaker']
    gt_id = item['gt_id']
    
    has_quotes = bool(re.search(r'[""""][^"""""]+[""""]', text))
    has_speech_verb = any(v in text for v in ['说道', '问道', '喊道', '笑道', '道：', '道,', '自语', '说道', '叫道', '答道', '回应道'])
    
    # Check if it's monologue/self-talk
    is_monologue = any(m in text for m in ['喃喃自语', '自语道', '心中想', '暗自想', '自言自语'])
    
    # Check if paragraph has narration-only (no dialogue at all)
    # A paragraph might be pure narration if it has no quotes and no speech verbs
    is_pure_narration = not has_quotes and not has_speech_verb
    
    # Check if speaker is a person name vs descriptor
    # Common descriptors that shouldn't be speaker names
    descriptors = ['声音', '清脆', '苍老', '熟悉', '低声', '高声']
    is_descriptor_speaker = any(d in speaker for d in descriptors)
    
    return {
        'gt_id': gt_id,
        'text': text,
        'speaker': speaker,
        'has_quotes': has_quotes,
        'has_speech_verb': has_speech_verb,
        'is_monologue': is_monologue,
        'is_pure_narration': is_pure_narration,
        'is_descriptor_speaker': is_descriptor_speaker,
    }

def main():
    print("=" * 60)
    print(" 测试集标注质量逐条分析")
    print("=" * 60)
    
    classifications = []
    
    for item in CONTEXT_MAP:
        cls = classify_paragraph(item)
        classifications.append(cls)
    
    # Group by classification
    pure_narration = [c for c in classifications if c['is_pure_narration']]
    monologue = [c for c in classifications if c['is_monologue']]
    has_quotes_and_verb = [c for c in classifications if c['has_quotes'] and c['has_speech_verb']]
    has_quotes_no_verb = [c for c in classifications if c['has_quotes'] and not c['has_speech_verb']]
    no_quotes_has_verb = [c for c in classifications if not c['has_quotes'] and c['has_speech_verb']]
    
    print(f"\n 分类统计:")
    print(f"  纯旁白（无引号无说话动词）: {len(pure_narration)} 条")
    print(f"  内心独白: {len(monologue)} 条")
    print(f"  有引号+有说话动词: {len(has_quotes_and_verb)} 条")
    print(f"  有引号无说话动词: {len(has_quotes_no_verb)} 条")
    print(f"  无引号有说话动词: {len(no_quotes_has_verb)} 条")
    
    print(f"\n 纯旁白段落:")
    for c in pure_narration:
        print(f"  {c['gt_id']}: {c['text'][:80]}")
        print(f"    标注说话人: {c['speaker']}")
        print(f"    → 建议: 应移除或标为'无对话'")
    
    print(f"\n 内心独白段落:")
    for c in monologue:
        print(f"  {c['gt_id']}: {c['text'][:80]}")
        print(f"    标注说话人: {c['speaker']}")
        print(f"    → 建议: 应标为'内心独白'而非'对话'")
    
    # Check error cases
    print(f"\n{'='*60}")
    print(f" 13条'错误'案例人工复核")
    print(f"{'='*60}")
    
    errors = RESULTS['p0_new_a']['context']['errors']
    for e in errors:
        gt_id = e['id']
        item = next((i for i in CONTEXT_MAP if i['gt_id'] == gt_id), None)
        if not item:
            continue
        
        text = item['full_paragraph']
        expected = e['expected']
        actual = e['actual']
        
        # Manual classification
        if gt_id.startswith('GT-玄幻'):
            classification = "GT标注问题（斗破段落使用同一长文本，'测验魔石碑'等不是人名）"
        elif actual in ['边有人低声', '他沉声']:
            classification = "NER提取了短语而非人名（管道问题）"
        elif actual == '男子' and expected == '博士':
            classification = "标注'博士'但文中无此词，NER提取'男子'是合理的"
        else:
            classification = "待人工确认"
        
        print(f"\n  {gt_id}:")
        print(f"    期望: {expected}, 实际: {actual}")
        print(f"    段落: {text[:100]}")
        print(f"    → 分类: {classification}")
    
    # Check non_dialogue FP
    print(f"\n{'='*60}")
    print(f" 4条non_dialogue FP人工复核")
    print(f"{'='*60}")
    
    from test_data_unified import UNIFIED_TEST_CASES
    
    fps = RESULTS['p0_new_b']['non_dialogue']['errors']
    for fp in fps:
        case = next((c for c in UNIFIED_TEST_CASES if c['id'] == fp['id']), None)
        if not case:
            continue
        
        text = case['paragraph']
        
        # Manual analysis
        if '自语道' in text:
            classification = "内心独白（'自语道'），管道应区分"
        elif any(x in text for x in ['林雪', '郭垣']):
            classification = "段落中有真实对话，标注为non_dialogue有误"
        else:
            classification = "待人工确认"
        
        print(f"\n  {fp['id']}:")
        print(f"    期望: 未知, 实际: {fp['actual']}")
        print(f"    段落: {text[:150]}")
        print(f"    → 分类: {classification}")
    
    # Summary
    print(f"\n{'='*60}")
    print(" 修正建议汇总")
    print(f"{'='*60}")
    
    print(f"\n 1. GT标注问题:")
    print(f"    - 斗破10条: 移除或修正（'测验魔石碑'等不是人名）")
    print(f"    - 纯旁白2条: 移除或标为'无对话'")
    print(f"    - 内心独白: 单独分类")
    
    print(f"\n 2. 管道问题:")
    print(f"    - NER提取短语: 需要实体过滤")
    print(f"    - NER未提取: 需要改进NER或添加规则")
    print(f"    - '自语道'区分: 需要内心独白检测")
    
    print(f"\n 3. 标注争议:")
    print(f"    - '男子' vs '博士': 需统一标注标准")

if __name__ == '__main__':
    main()
