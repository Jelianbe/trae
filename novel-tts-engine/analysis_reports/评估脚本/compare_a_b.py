"""对比模式A和模式B的详细差异"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid, json
from test_data_v6 import TEST_PARAGRAPHS
import sys, os
# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def run_eval(data, precreate_chars=None):
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    if precreate_chars:
        for name, gender in precreate_chars:
            cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    results = []
    for paragraph_data in data:
        para_id = paragraph_data['id']
        text = paragraph_data['paragraph']
        expected_dialogues = paragraph_data['dialogues']
        
        sm.reset_activity()
        dialogue_results = sm.analyze_dialogue(text, chapter_id=para_id)
        
        for i, (dialogue_text, speaker_char) in enumerate(dialogue_results):
            if i >= len(expected_dialogues):
                break
            
            expected = expected_dialogues[i]
            actual_name = speaker_char.name if speaker_char else '未知'
            expected_name = expected['speaker']
            
            results.append({
                'para_id': para_id,
                'expected': expected_name,
                'actual': actual_name,
                'is_correct': actual_name == expected_name,
                'dialogue': dialogue_text[:30],
            })
    
    try:
        os.unlink(db_path)
    except:
        pass
    
    return results

def main():
    precreate_chars = [
        ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
        ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
        ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
        ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
        ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
        ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
    ]
    
    results_a = run_eval(TEST_PARAGRAPHS)
    results_b = run_eval(TEST_PARAGRAPHS, precreate_chars)
    
    # Compare
    print("=" * 80)
    print("模式A→模式B 差异对比")
    print("=" * 80)
    
    improved = 0
    degraded = 0
    
    for r_a, r_b in zip(results_a, results_b):
        if r_a['is_correct'] != r_b['is_correct']:
            status = ""
            if not r_a['is_correct'] and r_b['is_correct']:
                status = "✅ 改进"
                improved += 1
            elif r_a['is_correct'] and not r_b['is_correct']:
                status = "❌ 退化"
                degraded += 1
            
            if status:
                print(f"P{r_a['para_id']:>2d} [{r_a['dialogue']:30s}] 期望={r_a['expected']:<8s} A={r_a['actual']:<8s} B={r_b['actual']:<8s} {status}")
    
    print(f"\n总结: 改进={improved} 退化={degraded} 净变化={improved-degraded}")

if __name__ == '__main__':
    main()
