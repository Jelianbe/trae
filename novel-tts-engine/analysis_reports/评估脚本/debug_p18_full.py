"""诊断P18完整流程"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tempfile, uuid
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

P18 = '"萧炎，你太弱了！"药老摇头道。萧炎低下头："师傅，我会努力的。"药老叹了口气。'

def test():
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    for name, gender in [('药老', 'male'), ('萧炎', 'male')]:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    # Analyze
    results = sm.analyze_dialogue(P18, chapter_id=18)
    
    print(f'P18: {P18}')
    print(f'共{len(results)}段对话')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        expected = '药老' if i == 0 else '萧炎'
        status = 'OK' if actual == expected else 'FAIL'
        print(f'  dialogue{i+1}: [{dialogue}] expected={expected} actual={actual} {status}')
    
    # 手动追踪对话1的context
    print()
    print('=== 手动追踪对话1 ===')
    dialogue1 = '"萧炎，你太弱了！"'
    idx = P18.find(dialogue1)
    ctx_before = P18[:idx].strip()
    ctx_after = P18[idx+len(dialogue1):].strip()
    print(f'ctx_before: "{ctx_before}"')
    print(f'ctx_after: "{ctx_after}"')
    print()
    
    # _extract_context_speakers
    candidates = sm._extract_context_speakers(dialogue1, ctx_before, ctx_after)
    print(f'_extract_context_speakers候选: {candidates[:5]}')
    print()
    
    # 角色库检查
    char = sm.char_manager.get_character_by_name('药老', project_id)
    print(f'get_character_by_name("药老"): {char.name if char else "None"}')
    char = sm.char_manager.get_character_by_name('萧炎', project_id)
    print(f'get_character_by_name("萧炎"): {char.name if char else "None"}')
    print()
    
    # 创建上下文并调用match_speaker
    context = DialogueContext(
        text=dialogue1,
        speaker_hint=None,
        prev_speaker=None,
        mentioned_characters=[],
        chapter_id=18,
        context_before=ctx_before,
        context_after=ctx_after,
    )
    match_result = sm.match_speaker(context)
    if match_result:
        print(f'match_speaker结果: {match_result.character.name} (type={match_result.match_type})')
    else:
        print('match_speaker结果: None')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    test()
