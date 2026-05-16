"""高效回归验证：抽样关键用例，快速验证P0/P1改进效果"""
import sys, os, json, time, tempfile, uuid, random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.dialogue_boundary_detector import get_detector

with open(os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json'), 'r', encoding='utf-8') as f:
    CONTEXT_MAP = json.load(f)

ALL_CHARS = [
    ('林轩', 'male'), ('小翠', 'female'), ('林天豪', 'male'),
    ('王管家', 'male'), ('赵虎', 'male'), ('李铁', 'male'),
    ('陈风', 'male'), ('路人', 'male'), ('考官', 'male'),
    ('苏夜', 'male'), ('林雪', 'female'), ('老陈', 'male'),
    ('黑衣人', 'male'), ('赵天行', 'male'), ('博士', 'male'),
    ('联盟成员', 'male'), ('三人', 'male'),
    ('艾德温', 'male'), ('伊莉雅', 'female'), ('加尔文', 'male'),
    ('骑士', 'male'), ('年轻骑士', 'male'), ('莫洛克', 'male'),
    ('托马斯', 'male'), ('雷纳德', 'male'), ('国王', 'male'),
    ('众人', 'male'),
    ('萧炎', 'male'), ('萧薰儿', 'female'), ('萧媚', 'female'),
    ('测验魔石碑', 'male'), ('中年男子', 'male'), ('测验人', 'male'),
    ('测试员', 'male'),
]

def names_equivalent(actual, expected):
    if actual == expected:
        return True
    shorter, longer = (actual, expected) if len(actual) < len(expected) else (expected, actual)
    if shorter in longer:
        return True
    return False

def build_pipeline():
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'reg_{uuid.uuid4().hex[:8]}'
    for name, gender in ALL_CHARS:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    boundary_detector = get_detector()
    return sm, boundary_detector, db_path, project_id

def eval_cases(cases, sm, boundary_detector, project_id):
    total = 0
    correct = 0
    unknown = 0
    wrong = 0
    errors = []
    start = time.time()
    for case in cases:
        sm.reset_activity()
        results = sm.analyze_dialogue(case['text'], chapter_id=project_id)
        if not results:
            total += 1
            continue
        dialogue_text, speaker_char = results[0]
        actual = speaker_char.name if speaker_char else '未知'
        expected = case['expected']
        total += 1
        if names_equivalent(actual, expected):
            correct += 1
        elif actual == '未知':
            unknown += 1
        else:
            wrong += 1
            errors.append({'id': case.get('id',''), 'expected': expected, 'actual': actual, 'text': case['text'][:60]})
    elapsed = time.time() - start
    return {'total': total, 'correct': correct, 'unknown': unknown, 'wrong': wrong, 'elapsed': elapsed, 'errors': errors}

def main():
    print("=" * 60)
    print(" 高效回归验证：P0/P1 改进抽样验证")
    print("=" * 60)
    
    sm, boundary_detector, db_path, project_id = build_pipeline()
    
    # 每风格抽样10条（含上下文）
    from collections import defaultdict
    by_style = defaultdict(list)
    for item in CONTEXT_MAP:
        by_style[item['style']].append(item)
    
    random.seed(42)
    sampled_context = []
    for style, items in by_style.items():
        sample = random.sample(items, min(10, len(items)))
        sampled_context.extend([{'id': s['gt_id'], 'text': s['full_paragraph'], 'expected': s['speaker']} for s in sample])
    
    sampled_single = []
    for style, items in by_style.items():
        sample = random.sample(items, min(10, len(items)))
        sampled_single.extend([{'id': s['gt_id'], 'text': s['dialogue_text'], 'expected': s['speaker']} for s in sample])
    
    print(f"\n抽样用例: 上下文 {len(sampled_context)} 条, 单句 {len(sampled_single)} 条")
    print(f"  西幻: 10, 修仙: 10, 都市异能: 10, 玄幻(斗破): 10")
    
    # Run context eval
    print("\n 运行上下文测试...")
    r_ctx = eval_cases(sampled_context, sm, boundary_detector, project_id)
    
    # Run single eval
    print(" 运行单句测试...")
    r_sgl = eval_cases(sampled_single, sm, boundary_detector, project_id)
    
    # Test non-dialogue filtering
    from test_data_unified import UNIFIED_TEST_CASES
    nd_cases = []
    for c in UNIFIED_TEST_CASES:
        if c.get('category') == 'non_dialogue':
            nd_cases.append({'id': c['id'], 'text': c['paragraph'], 'expected': '未知'})
    
    print(" 运行非对话过滤测试...")
    r_nd = eval_cases(nd_cases[:15], sm, boundary_detector, project_id)
    
    try:
        os.unlink(db_path)
    except:
        pass
    
    # Results
    print(f"\n{'='*60}")
    print(" 结果汇总")
    print(f"{'='*60}")
    print(f"\n  P0-NEW-A (上下文修复):")
    print(f"    单句基线:   {r_sgl['correct']}/{r_sgl['total']} ({r_sgl['correct']/r_sgl['total']:.1%})")
    print(f"    上下文修复: {r_ctx['correct']}/{r_ctx['total']} ({r_ctx['correct']/r_ctx['total']:.1%})")
    print(f"    提升:       +{(r_ctx['correct']/r_ctx['total'] - r_sgl['correct']/r_sgl['total']):.1%}")
    
    print(f"\n  P0-NEW-B (非对话过滤):")
    print(f"    正确返回未知: {r_nd['correct']}/{r_nd['total']}")
    print(f"    错误返回具体人: {r_nd['wrong']}")
    
    print(f"\n  详细错误:")
    for label, r in [("上下文", r_ctx), ("单句", r_sgl)]:
        if r['errors']:
            print(f"    [{label}] 错误示例 (前5):")
            for e in r['errors'][:5]:
                print(f"      {e['id']}: 期望={e['expected']}, 实际={e['actual']}")
    
    # Save results
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'p0_new_a_context': r_ctx,
        'p0_new_a_single': r_sgl,
        'p0_new_b_non_dialogue': r_nd,
    }
    out_path = os.path.join(os.path.dirname(__file__), 'regression_quick.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ 结果已保存: {out_path}")

if __name__ == '__main__':
    main()
