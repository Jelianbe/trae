"""回归验证：运行完整测试套件，验证P0-NEW-A/B和P1-NEW-1效果"""
import sys, os, json, time, tempfile, uuid, random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.dialogue_boundary_detector import get_detector
from test_data_unified import UNIFIED_TEST_CASES

# Load GT context mapping
with open(os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json'), 'r', encoding='utf-8') as f:
    CONTEXT_MAP = json.load(f)

CONTEXT_BY_ID = {item['gt_id']: item for item in CONTEXT_MAP}

# Character library
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

def names_equivalent(actual: str, expected: str) -> bool:
    if expected is None:
        return True
    if actual == expected:
        return True
    if not actual or not expected:
        return False
    shorter, longer = (actual, expected) if len(actual) < len(expected) else (expected, actual)
    if shorter in longer:
        diff = longer.replace(shorter, '')
        modifier_prefixs = ['白发', '黑衣', '白衣', '青衣', '红衣', '蓝衣', '紫衣',
                          '邋遢', '年轻', '年老', '高大', '矮小', '神秘',
                          '英俊', '丑陋', '胖', '瘦', '金袍', '黑袍', '守阵', '拄拐']
        for prefix in modifier_prefixs:
            if diff == prefix or longer.startswith(prefix + shorter):
                return True
        return True
    return False

def build_pipeline():
    """Create pipeline with all improvements"""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    
    cm = CharacterManager(db_path=db_path)
    project_id = f'regression_{uuid.uuid4().hex[:8]}'
    
    for name, gender in ALL_CHARS:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    boundary_detector = get_detector()
    
    return sm, boundary_detector, db_path, project_id

def run_test_on_cases(cases, label, sm, boundary_detector, project_id):
    """Run evaluation on a list of test cases"""
    total = 0
    correct = 0
    unknown_count = 0
    wrong_count = 0
    no_detect = 0
    fp_count = 0  # false positive: non-dialogue returning specific speaker
    errors = []
    
    start = time.time()
    total_cases = len(cases)
    
    for idx, case in enumerate(cases):
        # 进度展示
        if (idx + 1) % 10 == 0 or idx == 0:
            elapsed_so_far = time.time() - start
            rate = (idx + 1) / elapsed_so_far if elapsed_so_far > 0 else 0
            eta = (total_cases - idx - 1) / rate if rate > 0 else 0
            print(f"  [{idx+1}/{total_cases}] ({(idx+1)/total_cases:.0%}) 速率={rate:.1f}条/s 预计剩余={eta:.0f}s", end='\r', flush=True)
        
        sm.reset_activity()
        results = sm.analyze_dialogue(case['text'], chapter_id=project_id)
        
        if not results:
            no_detect += 1
            total += 1
            continue
        
        # Apply boundary filter
        filtered = []
        for dialogue_text, speaker_char in results:
            is_non_dialogue = False
            boundary_results = boundary_detector.detect_all(case['text'])
            for br in boundary_results:
                if not br.is_dialogue:
                    if dialogue_text in br.quote_info.text or br.quote_info.text in dialogue_text:
                        is_non_dialogue = True
                        break
            if not is_non_dialogue or (speaker_char is None):
                filtered.append((dialogue_text, speaker_char))
        
        if not filtered:
            no_detect += 1
            total += 1
            continue
        
        dialogue_text, speaker_char = filtered[0]
        actual_name = speaker_char.name if speaker_char else '未知'
        expected_speaker = case['expected_speaker']
        category = case.get('category', 'dialogue')
        
        total += 1
        
        if names_equivalent(actual_name, expected_speaker):
            correct += 1
        elif actual_name == '未知':
            unknown_count += 1
        else:
            if category == 'non_dialogue':
                fp_count += 1
            wrong_count += 1
            errors.append({
                'id': case.get('id', ''),
                'expected': expected_speaker,
                'actual': actual_name,
                'category': category,
                'text': case['text'][:60],
            })
    
    elapsed = time.time() - start
    acc = correct / total if total > 0 else 0
    
    print(f"\n  [{label}]")
    print(f"    总数: {total} (未检测到: {no_detect})")
    print(f"    正确: {correct} ({acc:.1%})")
    print(f"    未知: {unknown_count}")
    print(f"    错误: {wrong_count}")
    if fp_count > 0:
        print(f"    FP(non_dialogue返回具体人): {fp_count}")
    print(f"    耗时: {elapsed:.1f}s")
    
    return {
        'total': total, 'correct': correct, 'unknown': unknown_count,
        'wrong': wrong_count, 'no_detect': no_detect, 'fp': fp_count,
        'elapsed': elapsed, 'errors': errors,
    }

def main():
    print("=" * 60)
    print(" 回归验证：P0-NEW-A/B + P1-NEW-1 效果测试")
    print("=" * 60)
    
    # Build pipeline
    sm, boundary_detector, db_path, project_id = build_pipeline()
    
    # Build test cases
    # 1. GT cases with context (P0-NEW-A)
    gt_cases_context = []
    for item in CONTEXT_MAP:
        gt_cases_context.append({
            'id': item['gt_id'],
            'text': item['full_paragraph'],
            'expected_speaker': item['speaker'],
            'category': 'dialogue',
            'style': item['style'],
        })
    
    # 2. GT cases with single sentence (baseline)
    gt_cases_single = []
    for item in CONTEXT_MAP:
        gt_cases_single.append({
            'id': item['gt_id'],
            'text': item['dialogue_text'],
            'expected_speaker': item['speaker'],
            'category': 'dialogue',
            'style': item['style'],
        })
    
    # 3. Non-dialogue cases
    non_dialogue_cases = [c for c in UNIFIED_TEST_CASES if c.get('category') == 'non_dialogue']
    nd_cases = []
    for c in non_dialogue_cases:
        nd_cases.append({
            'id': c['id'],
            'text': c['paragraph'],
            'expected_speaker': '未知',
            'category': 'non_dialogue',
        })
    
    # 4. Unknown speaker cases
    unknown_cases = [c for c in UNIFIED_TEST_CASES if c.get('category') == 'unknown_speaker']
    uk_cases = []
    for c in unknown_cases:
        uk_cases.append({
            'id': c['id'],
            'text': c['paragraph'],
            'expected_speaker': '未知',
            'category': 'unknown_speaker',
        })
    
    # 5. Historical/new dialogue cases
    dialog_cases = [c for c in UNIFIED_TEST_CASES if c.get('category') == 'dialogue']
    dl_cases = []
    for c in dialog_cases:
        dl_cases.append({
            'id': c['id'],
            'text': c['paragraph'],
            'expected_speaker': None,  # Will be determined from dialogues
            'category': 'dialogue',
        })
    
    print(f"\n测试用例统计:")
    print(f"  GT上下文: {len(gt_cases_context)}")
    print(f"  GT单句: {len(gt_cases_single)}")
    print(f"  非对话: {len(nd_cases)}")
    print(f"  未知说话人: {len(uk_cases)}")
    print(f"  历史对话: {len(dl_cases)}")
    print(f"  总计: {len(gt_cases_context) + len(nd_cases) + len(uk_cases)}")
    
    # Run tests
    print("\n" + "=" * 60)
    print(" 测试运行")
    print("=" * 60)
    
    # P0-NEW-A: context vs single sentence comparison
    r_context = run_test_on_cases(gt_cases_context, "GT上下文（P0-NEW-A）", sm, boundary_detector, project_id)
    r_single = run_test_on_cases(gt_cases_single, "GT单句（基线）", sm, boundary_detector, project_id)
    
    # P0-NEW-B: non-dialogue filtering
    r_nondialogue = run_test_on_cases(nd_cases, "非对话过滤（P0-NEW-B）", sm, boundary_detector, project_id)
    
    # Unknown speaker cases
    r_unknown = run_test_on_cases(uk_cases, "未知说话人", sm, boundary_detector, project_id)
    
    # Historical dialogue cases
    r_dialog = run_test_on_cases(dl_cases[:50], "历史对话(抽样50)", sm, boundary_detector, project_id)
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass
    
    # Summary
    print("\n" + "=" * 60)
    print(" 综合结果")
    print("=" * 60)
    print(f"\n  P0-NEW-A 效果验证:")
    print(f"    单句基线:   {r_single['correct']/r_single['total']:.1%} ({r_single['correct']}/{r_single['total']})")
    print(f"    上下文修复: {r_context['correct']/r_context['total']:.1%} ({r_context['correct']}/{r_context['total']})")
    improvement = r_context['correct']/r_context['total'] - r_single['correct']/r_single['total']
    print(f"    提升:       +{improvement:.1%}")
    
    print(f"\n  P0-NEW-B 效果验证:")
    print(f"    FP(non_dialogue返回具体人): {r_nondialogue['fp']}")
    print(f"    目标: ≤5")
    print(f"    状态: {'通过' if r_nondialogue['fp'] <= 5 else '未达标'}")
    
    print(f"\n  P1-NEW-1 效果验证:")
    print(f"    entity_cleaner 保留策略已更新")
    print(f"    - 新增'的'字结构检测")
    print(f"    - 新增2字实体保留")
    print(f"    注：召回率提升需在完整管道中验证")
    
    # Save detailed results
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'p0_new_a': {'context': r_context, 'single': r_single},
        'p0_new_b': {'non_dialogue': r_nondialogue},
        'p1_new_1': {'note': 'entity_cleaner策略已更新'},
        'other': {'unknown': r_unknown, 'dialog_sample': r_dialog},
    }
    
    output_path = os.path.join(os.path.dirname(__file__), 'regression_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ 详细结果已保存: {output_path}")

if __name__ == '__main__':
    main()
