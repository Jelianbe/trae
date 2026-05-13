"""诊断P7实际context_before内容"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.pipeline_runner import PipelineRunner
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

P7 = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起：\"这枚丹药，你先服下。\"萧炎点头照做。\"感觉如何？\"老者问道。'

def diagnose():
    # 创建临时DB
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    for name in ['药老', '萧炎']:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')
    
    from pipeline.speaker_matcher import SpeakerMatcher
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    print(f'原文: {P7}')
    print()
    
    # 使用analyze_dialogue，打印每个对话的context_before
    # 先看看分出来的对话和对应的上下文
    results = sm.analyze_dialogue(P7, chapter_id=1)
    print(f'共{len(results)}段对话:')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        print(f'  对话{i+1}: [{dialogue}] -> {actual}')
        print(f'    speaker match_type: {speaker.speaker_hint if speaker else "N/A"}')
    
    # 手动测试_extract_context_speakers
    print()
    print('=== 手动测试 _extract_context_speakers ===')
    
    # 对话1: "这枚丹药，你先服下。"
    # context_before应该是: "萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起："
    ctx_before = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起：'
    ctx_after = ''
    text = '这枚丹药，你先服下。'
    
    print(f'对话: {text}')
    print(f'context_before: {ctx_before}')
    print(f'context_after: {ctx_after}')
    print()
    
    # 检查角色库中是否有药老
    all_chars = cm.get_all_characters()
    print(f'角色库: {[c.name for c in all_chars]}')
    print()
    
    # 检查声音指示模式
    import re
    for char in all_chars:
        patterns = [
            rf'{char.name}的声音',
            rf'{char.name}在脑海',
            rf'{char.name}心中',
        ]
        for pattern in patterns:
            if re.search(pattern, ctx_before):
                print(f'  ✅ 匹配到声音指示: {char.name} (pattern={pattern})')
    
    # 测试_extract_context_speakers
    candidates = sm._extract_context_speakers(text, ctx_before, ctx_after)
    print()
    print(f'_extract_context_speakers候选: {candidates}')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    diagnose()
