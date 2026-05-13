"""用评估脚本同样的P7原文测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tempfile, uuid
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

# 评估脚本中的P7原文
P7 = '药老从戒指中飘出。他看了一眼萧炎，缓缓道："这枚丹药，你先服下。"萧炎接过来，毫不犹豫地吞了下去。'

def test():
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    for name in ['药老', '萧炎']:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    sm.reset_activity()
    
    results = sm.analyze_dialogue(P7, chapter_id=7)
    
    print(f'P7原文: {P7}')
    print(f'分析结果: {len(results)}段对话')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        expected = '药老'
        status = 'OK' if actual == expected else 'FAIL'
        print(f'  dialogue{i+1}: [{dialogue}] expected={expected} actual={actual} {status}')
    
    # 分析上下文
    print()
    idx = P7.find('"这枚丹药，你先服下。"')
    ctx_before = P7[:idx].strip()
    ctx_after = P7[idx+len('"这枚丹药，你先服下。"'):].strip()
    print(f'context_before: "{ctx_before}"')
    print(f'context_after: "{ctx_after}"')
    print()
    
    # NER结果
    result = sm.nlp.analyze(ctx_before)
    pers = [e for e in result.entities if e.type == 'PER']
    print(f'NER PER: {[e.text for e in pers]}')
    
    # _extract_context_speakers
    candidates = sm._extract_context_speakers('"这枚丹药，你先服下。"', ctx_before, ctx_after)
    print(f'context_speakers候选: {candidates[:3]}')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    test()
