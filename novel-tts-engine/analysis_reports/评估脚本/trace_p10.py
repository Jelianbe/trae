"""追踪P10对话1实际匹配流程"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tempfile, uuid
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

P10 = '萧炎看向药老："这枚丹药值多少？"药老捋了捋胡须："至少三万金币。"萧炎皱眉："太贵了。'
dialogue1 = '"这枚丹药值多少？"'

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
    
    idx = P10.find(dialogue1)
    ctx_before = P10[:idx].strip()
    ctx_after = P10[idx+len(dialogue1):].strip()
    
    print(f'ctx_before: "{ctx_before}"')
    print(f'ctx_after: "{ctx_after}"')
    print()
    
    # 测试_extract_context_speakers
    candidates = sm._extract_context_speakers(dialogue1, ctx_before, ctx_after)
    print(f'_extract_context_speakers候选:')
    for i, (name, reason, conf) in enumerate(candidates):
        print(f'  {i+1}. {name} ({reason}) confidence={conf}')
    print()
    
    # 测试match_speaker
    context = DialogueContext(
        text=dialogue1,
        speaker_hint=None,
        prev_speaker=None,
        mentioned_characters=[],
        chapter_id=10,
        context_before=ctx_before,
        context_after=ctx_after,
    )
    result = sm.match_speaker(context)
    if result:
        print(f'match_speaker: {result.character.name} (type={result.match_type})')
    else:
        print('match_speaker: None')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    test()
