"""用评估脚本同样的方式测试P7"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tempfile, uuid
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

# P7原文
P7 = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起："这枚丹药，你先服下。"萧炎点头照做。"感觉如何？"老者问道。'
expected_dialogues = [
    {'text': '这枚丹药，你先服下。', 'speaker': '药老'},
    {'text': '感觉如何？', 'speaker': '药老'},
]

def test():
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    # 预创建角色（同评估脚本模式B）
    for name in ['药老', '萧炎']:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    sm.reset_activity()
    
    results = sm.analyze_dialogue(P7, chapter_id=7)
    
    print(f'P7分析结果:')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        expected = expected_dialogues[i]['speaker'] if i < len(expected_dialogues) else '?'
        status = 'OK' if actual == expected else 'FAIL'
        print(f'  dialogue{i+1}: [{dialogue}] expected={expected} actual={actual} {status}')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    test()
