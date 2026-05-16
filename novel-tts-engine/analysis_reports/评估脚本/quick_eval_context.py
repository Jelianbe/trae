"""快速评估：仅测试GT用例（带上下文）的准确率，验证P0-NEW-A效果"""
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

# Load context mapping
with open(os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json'), 'r', encoding='utf-8') as f:
    CONTEXT_MAP = json.load(f)

# Build test cases from context mapping
def build_test_cases():
    cases = []
    for item in CONTEXT_MAP:
        cases.append({
            'id': item['gt_id'],
            'text': item['full_paragraph'],  # 使用完整段落
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

def main():
    print("=" * 60)
    print(" P0-NEW-A 快速验证：GT用例上下文修复效果")
    print("=" * 60)
    
    cases = build_test_cases()
    print(f"\n测试用例: {len(cases)} 条")
    
    # 统计风格分布
    from collections import Counter
    style_counts = Counter(c['style'] for c in cases)
    for style, cnt in style_counts.most_common():
        print(f"  {style}: {cnt}")
    
    # 创建角色库
    import tempfile, uuid
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    
    cm = CharacterManager(db_path=db_path)
    project_id = f'quick_test_{uuid.uuid4().hex[:8]}'
    
    # 预创建角色
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
    errors = []
    
    start = time.time()
    
    for case in cases:
        sm.reset_activity()
        results = sm.analyze_dialogue(case['text'], chapter_id=case['id'])
        
        if not results:
            # 没有检测到对话
            wrong_count += 1
            total += 1
            errors.append({
                'id': case['id'],
                'expected': case['expected_speaker'],
                'actual': '(未检测到)',
                'text': case['text'][:50],
            })
            continue
        
        # 取第一个对话结果
        dialogue_text, speaker_char = results[0]
        actual_name = speaker_char.name if speaker_char else '未知'
        
        total += 1
        if names_equivalent(actual_name, case['expected_speaker']):
            correct += 1
        elif actual_name == '未知':
            unknown_count += 1
        else:
            wrong_count += 1
            errors.append({
                'id': case['id'],
                'expected': case['expected_speaker'],
                'actual': actual_name,
                'text': case['text'][:50],
            })
    
    elapsed = time.time() - start
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass
    
    # 输出结果
    print(f"\n{'='*60}")
    print(f" 测试结果 (耗时 {elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f" 总测试: {total}")
    print(f" 正确:   {correct} ({correct/total:.1%})")
    print(f" 未知:   {unknown_count}")
    print(f" 错误:   {wrong_count}")
    
    if errors:
        print(f"\n 错误明细 (前{min(20, len(errors))}条):")
        for e in errors[:20]:
            print(f"  x {e['id']:<25s} 期望={e['expected']:<10s} 实际={e['actual']:<10s} [{e['text']}]")

if __name__ == '__main__':
    main()
