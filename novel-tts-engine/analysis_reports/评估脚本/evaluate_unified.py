"""评估统一测试用例集 - 支持非对话/未知说话人/多分类"""
import sys, os, json, time, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.dialogue_boundary_detector import get_detector
from test_data_unified import UNIFIED_TEST_CASES

# Load GT context mapping if available
GT_CONTEXT_MAP = {}
_context_path = os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json')
if os.path.exists(_context_path):
    import json as _json
    with open(_context_path, 'r', encoding='utf-8') as _f:
        _ctx_data = _json.load(_f)
    for item in _ctx_data:
        GT_CONTEXT_MAP[item['gt_id']] = item['full_paragraph']

def resolve_input_text(paragraph_data):
    """For GT cases with context, use full_paragraph; otherwise use paragraph"""
    case_id = paragraph_data['id']
    if case_id in GT_CONTEXT_MAP:
        return GT_CONTEXT_MAP[case_id]
    return paragraph_data['paragraph']

def filter_dialogue_results(results, text, boundary_detector):
    """Filter out non-dialogue quotes using boundary detector"""
    if not boundary_detector or not results:
        return results
    
    boundary_results = boundary_detector.detect_all(text)
    if not boundary_results:
        return results
    
    # Build set of non-dialogue quote texts
    non_dialogue_quotes = set()
    for br in boundary_results:
        if not br.is_dialogue:
            non_dialogue_quotes.add(br.quote_info.text)
    
    filtered = []
    for dialogue_text, speaker_char in results:
        # Check if this quote is identified as non-dialogue
        is_non_dialogue = False
        for nq in non_dialogue_quotes:
            if dialogue_text in nq or nq in dialogue_text:
                is_non_dialogue = True
                break
        
        # Keep if: (1) it's dialogue, OR (2) speaker is unknown (principle 2)
        # Filter out if: non-dialogue AND specific speaker assigned
        if not is_non_dialogue or (speaker_char is None):
            filtered.append((dialogue_text, speaker_char))
    
    return filtered


def names_equivalent(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
def names_equivalent(actual: str, expected: str) -> bool:
    if actual == expected:
        return True

    shorter, longer = (actual, expected) if len(actual) < len(expected) else (expected, actual)

    if shorter in longer:
        diff = longer.replace(shorter, '')
        modifier_prefixs = ['白发', '黑衣', '白衣', '青衣', '红衣', '蓝衣', '紫衣',
                          '邋遢', '年轻', '年老', '高大', '矮小', '神秘',
                          '英俊', '丑陋', '胖', '瘦', '金袍', '黑袍', '守阵', '拄拐']
        for prefix in modifier_prefixs:
            if diff == prefix or longer.startswith(prefix + shorter):
                return True
        if all(c in '怒冷冷淡淡低高轻沉苦涩颤抖微笑' for c in diff):
            return False
        return True

    return False


def run_unified_evaluation(data, precreate_chars=None):
    import tempfile, uuid
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_unified_{uuid.uuid4().hex[:8]}'

    if precreate_chars:
        for name, gender in precreate_chars:
            char = cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)

    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    # Initialize boundary detector
    boundary_detector = get_detector()

    total_expected = 0
    correct = 0
    unknown_correct = 0  # 期望未知且返回未知
    wrong = 0
    false_positive = 0   # 期望无对话但检测到对话
    false_negative = 0   # 期望有对话但未检测到
    detail_results = []

    for paragraph_data in data:
        para_id = paragraph_data['id']
        text = resolve_input_text(paragraph_data)  # Use full paragraph if available
        expected_dialogues = paragraph_data.get('dialogues', [])
        category = paragraph_data.get('category', 'dialogue')

        sm.reset_activity()
        results = sm.analyze_dialogue(text, chapter_id=para_id)
        
        # Apply boundary detection filter
        results = filter_dialogue_results(results, text, boundary_detector)

        # Non-dialogue case: expect NO dialogues
        if category == 'non_dialogue' and len(expected_dialogues) == 0:
            if len(results) == 0:
                correct += 1
                total_expected += 1
                detail_results.append({
                    'para_id': para_id,
                    'category': category,
                    'expected': '(无对话)',
                    'actual': '(无对话)',
                    'is_correct': True,
                    'is_false_positive': False,
                })
            else:
                false_positive += 1
                total_expected += 1
                for dialogue_text, speaker_char in results:
                    actual_name = speaker_char.name if speaker_char else '未知'
                    detail_results.append({
                        'para_id': para_id,
                        'category': category,
                        'expected': '(无对话)',
                        'actual': actual_name,
                        'is_correct': False,
                        'is_false_positive': True,
                        'dialogue': dialogue_text[:30],
                    })
            continue

        # Dialogue / unknown_speaker cases
        for i, expected in enumerate(expected_dialogues):
            total_expected += 1
            expected_name = expected['speaker']
            expected_text = expected.get('text', '')

            if i >= len(results):
                false_negative += 1
                detail_results.append({
                    'para_id': para_id,
                    'category': category,
                    'expected': expected_name,
                    'actual': '(未检测到)',
                    'is_correct': False,
                    'is_false_negative': True,
                    'dialogue': expected_text[:30],
                })
                continue

            dialogue_text, speaker_char = results[i]
            actual_name = speaker_char.name if speaker_char else '未知'

            if expected_name == '未知':
                if actual_name == '未知':
                    unknown_correct += 1
                    correct += 1
                else:
                    wrong += 1
            else:
                if names_equivalent(actual_name, expected_name):
                    correct += 1
                elif actual_name == '未知':
                    unknown_correct += 1
                    wrong += 1  # 期望有具体人但返回未知 = 不算正确
                else:
                    wrong += 1

            detail_results.append({
                'para_id': para_id,
                'category': category,
                'expected': expected_name,
                'actual': actual_name,
                'is_correct': names_equivalent(actual_name, expected_name) or (expected_name == '未知' and actual_name == '未知'),
                'dialogue': dialogue_text[:30],
            })

        # Extra results beyond expected → false positives
        for i in range(len(expected_dialogues), len(results)):
            false_positive += 1
            total_expected += 1
            dialogue_text, speaker_char = results[i]
            actual_name = speaker_char.name if speaker_char else '未知'
            detail_results.append({
                'para_id': para_id,
                'category': category,
                'expected': '(无此对话)',
                'actual': actual_name,
                'is_correct': False,
                'is_false_positive': True,
                'dialogue': dialogue_text[:30],
            })

    try:
        os.unlink(db_path)
    except:
        pass

    return {
        'total_expected': total_expected,
        'correct': correct,
        'unknown_correct': unknown_correct,
        'wrong': wrong,
        'false_positive': false_positive,
        'false_negative': false_negative,
        'accuracy': correct / total_expected if total_expected > 0 else 0,
        'details': detail_results,
    }


def print_report(result, label):
    print(f"\n{'='*60}")
    print(f" {label}")
    print(f"{'='*60}")
    print(f" 总期望:     {result['total_expected']}")
    print(f" 正确:       {result['correct']} ({result['accuracy']:.1%})")
    print(f"   其中未知正确: {result['unknown_correct']}")
    print(f" 错误:       {result['wrong']}")
    print(f" 误报(FP):   {result['false_positive']}")
    print(f" 漏报(FN):   {result['false_negative']}")

    # Per-category stats
    details = result['details']
    cats = {}
    for d in details:
        cat = d.get('category', '?')
        if cat not in cats:
            cats[cat] = {'total': 0, 'correct': 0}
        cats[cat]['total'] += 1
        if d['is_correct']:
            cats[cat]['correct'] += 1

    print(f"\n 按分类:")
    for cat in ['dialogue', 'unknown_speaker', 'non_dialogue']:
        if cat in cats:
            c = cats[cat]
            acc = c['correct'] / c['total'] if c['total'] > 0 else 0
            print(f"   {cat:<20s}: {c['correct']}/{c['total']} ({acc:.1%})")

    # Errors
    errors = [d for d in details if not d['is_correct']]
    if errors:
        print(f"\n 错误明细 ({len(errors)}条):")
        for d in errors[:30]:
            fp = '(FP)' if d.get('is_false_positive') else ''
            fn = '(FN)' if d.get('is_false_negative') else ''
            tag = fp or fn or ''
            print(f"   x {d['para_id']:<12s} 期望={d['expected']:<12s} 实际={d['actual']:<12s} {tag} [{d.get('dialogue', '')}]")

def main():
    print("加载统一测试数据...")
    data = UNIFIED_TEST_CASES
    print(f"  {len(data)} 条用例")

    # 统计
    from collections import Counter
    cats = Counter(d['category'] for d in data)
    for cat, cnt in cats.most_common():
        d_count = sum(len(d['dialogues']) for d in data if d['category'] == cat)
        print(f"  {cat}: {cnt}条, {d_count}期望对话")

    precreate_chars = [
        ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
        ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
        ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
        ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
        ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
        ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
        ('孙项明', 'male'), ('药尘', 'male'), ('郭垣', 'male'),
        ('小师妹', 'female'), ('掌门', 'male'),
    ]

    # Mode A: 无角色库
    start = time.time()
    result_a = run_unified_evaluation(data, precreate_chars=None)
    elapsed_a = time.time() - start
    print_report(result_a, f'模式A: 无角色库 (耗时{elapsed_a:.2f}s)')

    # Mode B: 预创建角色
    start = time.time()
    result_b = run_unified_evaluation(data, precreate_chars=precreate_chars)
    elapsed_b = time.time() - start
    print_report(result_b, f'模式B: 预创建{len(precreate_chars)}角色 (耗时{elapsed_b:.2f}s)')

    print(f"\n{'='*60}")
    print(f" 对比总结")
    print(f"{'='*60}")
    for metric in ['accuracy', 'false_positive', 'false_negative']:
        a_val = result_a[metric]
        b_val = result_b[metric]
        if isinstance(a_val, float):
            print(f" {metric:<15s}: A={a_val:.1%}, B={b_val:.1%}")
        else:
            print(f" {metric:<15s}: A={a_val}, B={b_val}")

if __name__ == '__main__':
    main()
