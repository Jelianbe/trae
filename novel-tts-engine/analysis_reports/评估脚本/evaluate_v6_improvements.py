"""评估 v6 跨句推理改进效果"""
import sys, os, json, time, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
from test_data_v6 import TEST_PARAGRAPHS as DEFAULT_DATA

def load_test_data():
    return DEFAULT_DATA

def create_character_for_test(cm, project_id, name, gender='male'):
    from pipeline.character_manager import Character
    char = cm.add_character(
        name=name,
        project_id=project_id,
        aliases=set(),
        gender=gender
    )
    return char

def run_evaluation(data, precreate_chars=None):
    import tempfile, os
    from pipeline.character_manager import CharacterManager
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    
    import uuid
    project_id = f'test_v6_{uuid.uuid4().hex[:8]}'
    
    if precreate_chars:
        for name, gender in precreate_chars:
            create_character_for_test(cm, project_id, name, gender)
    
    from pipeline.semantic_ranker import get_semantic_ranker
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    total_dialogues = 0
    correct = 0
    unknown = 0
    detail_results = []
    
    for paragraph_data in data:
        para_id = paragraph_data['id']
        text = paragraph_data['paragraph']
        expected_dialogues = paragraph_data['dialogues']
        
        # Reset for each paragraph
        sm.reset_activity()
        
        # Use analyze_dialogue to get speakers
        results = sm.analyze_dialogue(text, chapter_id=para_id)
        
        # Compare with expected
        for i, (dialogue_text, speaker_char) in enumerate(results):
            if i >= len(expected_dialogues):
                break
            
            expected = expected_dialogues[i]
            actual_name = speaker_char.name if speaker_char else '未知'
            expected_name = expected['speaker']
            expected_text = expected['text']
            
            is_correct = (actual_name == expected_name)
            is_unknown = (actual_name == '未知')
            
            if is_correct:
                correct += 1
            if is_unknown:
                unknown += 1
            total_dialogues += 1
            
            detail_results.append({
                'para_id': para_id,
                'expected': expected_name,
                'actual': actual_name,
                'is_correct': is_correct,
                'is_unknown': is_unknown,
                'dialogue': dialogue_text[:30],
            })
    
    try:
        os.unlink(db_path)
    except:
        pass
    
    # 加权准确率：正确=1.0分，未知=0.25分，错误=0.0分
    # 设计理念："诚实优于猜测"，未知比错误的用户成本低
    UNKNOWN_WEIGHT = 0.25
    wrong = total_dialogues - correct - unknown
    weighted_score = correct * 1.0 + unknown * UNKNOWN_WEIGHT
    weighted_accuracy = weighted_score / total_dialogues if total_dialogues > 0 else 0
    
    return {
        'total': total_dialogues,
        'correct': correct,
        'unknown': unknown,
        'wrong': wrong,
        'accuracy': correct / total_dialogues if total_dialogues > 0 else 0,
        'unknown_rate': unknown / total_dialogues if total_dialogues > 0 else 0,
        'wrong_rate': wrong / total_dialogues if total_dialogues > 0 else 0,
        'weighted_accuracy': weighted_accuracy,
        'weighted_score': weighted_score,
        'details': detail_results,
    }

def print_report(result, label):
    print(f"\n{'='*60}")
    print(f" {label}")
    print(f"{'='*60}")
    print(f" 总对话:   {result['total']}")
    print(f" 正确:     {result['correct']} ({result['accuracy']:.1%})")
    print(f" 未知:     {result['unknown']} ({result['unknown_rate']:.1%})")
    print(f" 错误:     {result['wrong']} ({result['wrong_rate']:.1%})")
    print(f" 加权准确率: {result['weighted_accuracy']:.1%} (正确x1.0 + 未知x0.25)")
    
    # Print details for wrong cases
    wrong = [d for d in result['details'] if not d['is_correct']]
    print(f"\n 错误明细 ({len(wrong)}条):")
    for d in wrong[:20]:
        status = '未知' if d['is_unknown'] else '错误'
        print(f"   x P{d['para_id']}: 期望={d['expected']:<8s} 实际={d['actual']:<8s} ({status}) [{d['dialogue']}]")

def main():
    print("加载测试数据...")
    data = load_test_data()
    print(f"  {len(data)} 个段落")
    total_dialogue_count = sum(len(p['dialogues']) for p in data)
    
    # Verify DIALOGUE_PATTERNS can find all dialogues
    from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS as DP
    found_count = 0
    for item in data:
        found_count += sum(1 for pat in DP for _ in pat.finditer(item['paragraph']))
    print(f"  {total_dialogue_count} 个对话 (DIALOGUE_PATTERNS匹配: {found_count})")
    
    # Mode A: No pre-created characters
    start = time.time()
    result_a = run_evaluation(data, precreate_chars=None)
    elapsed_a = time.time() - start
    print_report(result_a, f'模式A: 无角色库 (耗时{elapsed_a:.2f}s)')
    
    # Mode B: With pre-created characters (11 main characters from test data)
    precreate_chars = [
        ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
        ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
        ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
        ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
        ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
        ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
    ]
    start = time.time()
    result_b = run_evaluation(data, precreate_chars=precreate_chars)
    elapsed_b = time.time() - start
    print_report(result_b, f'模式B: 预创建18角色 (耗时{elapsed_b:.2f}s)')
    
    # Comparison
    print(f"\n{'='*60}")
    print(f" 对比总结")
    print(f"{'='*60}")
    print(f" {'指标':<20s} {'模式A(无库)':<20s} {'模式B(有库)':<20s} {'差值':>10s}")
    print(f" {'-'*70}")
    print(f" {'准确率':<20s} {result_a['accuracy']:>10.1%}{'':>10s} {result_b['accuracy']:>10.1%}{'':>10s} {result_b['accuracy']-result_a['accuracy']:>+9.1%}")
    print(f" {'未知率':<20s} {result_a['unknown_rate']:>10.1%}{'':>10s} {result_b['unknown_rate']:>10.1%}{'':>10s} {result_b['unknown_rate']-result_a['unknown_rate']:>+9.1%}")
    print(f" {'加权准确率':<18s} {result_a['weighted_accuracy']:>10.1%}{'':>10s} {result_b['weighted_accuracy']:>10.1%}{'':>10s} {result_b['weighted_accuracy']-result_a['weighted_accuracy']:>+9.1%}")
    print(f" {'正确数':<20s} {result_a['correct']:>3d}/{result_a['total']:<3d}{'':>14s} {result_b['correct']:>3d}/{result_b['total']:<3d}")

if __name__ == '__main__':
    main()
