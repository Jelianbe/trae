"""快速评估：使用GT原文（单句）验证基线准确率，确认当前管线能力"""
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

with open(os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json'), 'r', encoding='utf-8') as f:
    CONTEXT_MAP = json.load(f)

def build_test_cases(use_context=False):
    cases = []
    for item in CONTEXT_MAP:
        cases.append({
            'id': item['gt_id'],
            # use_context=True: 使用完整段落; False: 使用单句对话
            'text': item['full_paragraph'] if use_context else item['dialogue_text'],
            'expected_speaker': item['speaker'],
            'style': item['style'],
        })
    return cases

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
        return True
    return False

def run_eval(cases, label):
    import tempfile, uuid
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    
    cm = CharacterManager(db_path=db_path)
    project_id = f'quick_test_{uuid.uuid4().hex[:8]}'
    
    all_chars = [
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
    
    for name, gender in all_chars:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    total = 0
    correct = 0
    unknown_count = 0
    wrong_count = 0
    no_detect = 0
    
    start = time.time()
    
    for case in cases:
        sm.reset_activity()
        results = sm.analyze_dialogue(case['text'], chapter_id=case['id'])
        
        if not results:
            no_detect += 1
            total += 1
            continue
        
        dialogue_text, speaker_char = results[0]
        actual_name = speaker_char.name if speaker_char else '未知'
        
        total += 1
        if names_equivalent(actual_name, case['expected_speaker']):
            correct += 1
        elif actual_name == '未知':
            unknown_count += 1
        else:
            wrong_count += 1
    
    elapsed = time.time() - start
    try:
        os.unlink(db_path)
    except:
        pass
    
    acc = correct / total if total > 0 else 0
    print(f"\n  [{label}]")
    print(f"    总数: {total} (未检测到: {no_detect})")
    print(f"    正确: {correct} ({acc:.1%})")
    print(f"    未知: {unknown_count}")
    print(f"    错误: {wrong_count}")
    print(f"    耗时: {elapsed:.1f}s ({total/elapsed:.1f} 条/s)")
    
    return {'total': total, 'correct': correct, 'unknown': unknown_count, 'wrong': wrong_count, 'no_detect': no_detect, 'elapsed': elapsed}

def main():
    print("=" * 60)
    print(" P0-NEW-A 验证：单句 vs 上下文 效果对比")
    print("=" * 60)
    
    cases_single = build_test_cases(use_context=False)
    cases_context = build_test_cases(use_context=True)
    
    print(f"\n测试用例: {len(cases_single)} 条")
    from collections import Counter
    style_counts = Counter(c['style'] for c in cases_single)
    for style, cnt in style_counts.most_common():
        print(f"  {style}: {cnt}")
    
    # Run single sentence eval first (faster)
    r1 = run_eval(cases_single, "单句输入（原文）")
    
    # Run context eval on a sample of 30 cases (to save time)
    import random
    random.seed(42)
    sample_indices = random.sample(range(len(cases_context)), min(30, len(cases_context)))
    cases_context_sample = [cases_context[i] for i in sorted(sample_indices)]
    r2 = run_eval(cases_context_sample, f"上下文输入（30条采样）")
    
    print(f"\n{'='*60}")
    print(" 对比分析")
    print(f"{'='*60}")
    print(f"  单句准确率: {r1['correct']/r1['total']:.1%}")
    print(f"  上下文准确率 (30条采样): {r2['correct']/r2['total']:.1%}")

if __name__ == '__main__':
    main()
