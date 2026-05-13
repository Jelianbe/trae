"""测试P10/P15/P18修复"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tempfile, uuid
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

TEST_CASES = [
    (10, '萧炎看向药老："这枚丹药值多少？"药老捋了捋胡须："至少三万金币。"萧炎皱眉："太贵了。',
     [('这枚丹药值多少？', '药老'), ('至少三万金币。', '药老'), ('太贵了。', '萧炎')]),
    (15, '林雪拍了一下桌子。"这丹药如何？"药老看向萧炎。萧炎点头道："很好，我买了。',
     [('这丹药如何？', '林雪'), ('很好，我买了。', '萧炎')]),
    (18, '"萧炎，你太弱了！"药老摇头道。萧炎低下头："师傅，我会努力的。"药老叹了口气。',
     [('萧炎，你太弱了！', '药老'), ('师傅，我会努力的。', '萧炎')]),
]

CHARS = [
    ('药老', 'male'), ('萧炎', 'male'), ('林雪', 'female'),
]

def test():
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    for name, gender in CHARS:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    total_correct = 0
    total_count = 0
    
    for para_id, text, expected in TEST_CASES:
        sm.reset_activity()
        results = sm.analyze_dialogue(text, chapter_id=para_id)
        
        print(f'P{para_id}: {text}')
        for i, (dialogue, speaker) in enumerate(results):
            if i >= len(expected):
                break
            actual = speaker.name if speaker else '未知'
            exp = expected[i][1]
            status = 'OK' if actual == exp else 'FAIL'
            if actual == exp:
                total_correct += 1
            total_count += 1
            print(f'  dialogue{i+1}: [{dialogue}] expected={exp} actual={actual} {status}')
        print()
    
    print(f'总计: {total_correct}/{total_count} OK ({100*total_correct/total_count:.1f}%)')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    test()
