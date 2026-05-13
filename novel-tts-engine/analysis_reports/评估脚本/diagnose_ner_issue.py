"""诊断NER误匹配：为什么药老的对话被归给萧炎"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

# P7：药老说话，但NER可能提取到"萧炎"
P7 = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起：\"这枚丹药，你先服下。\"萧炎点头照做。'

# P18：药老说话，NER提取"萧炎"
P18 = '萧炎站在练功场中央，汗水浸透了衣衫。\"萧炎，你太弱了！\"药老的声音响起。'

def diagnose(text, precreate_chars=None):
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
    
    print(f'原文: {text}')
    print()
    
    # 1. NER结果
    result = sm.nlp.analyze(text)
    pers = [e for e in result.entities if e.type == 'PER']
    print(f'NER PER实体: {[e.text for e in pers]}')
    print()
    
    # 2. 分词结果
    import hanlp
    from pipeline.nlp_basics import _create_hanlp_tokenizer
    try:
        tokenizer = _create_hanlp_tokenizer()
        tokens = tokenizer(text)
        print(f'分词结果: {tokens}')
        print()
    except Exception as e:
        print(f'分词加载失败: {e}')
        print()
    
    # 3. _extract_from_ner 结果
    narration = text
    ner_candidates = sm._extract_from_ner(narration)
    print(f'NER候选: {ner_candidates}')
    print()
    
    # 4. _extract_context_speakers 结果
    # 模拟对话2的上下文
    print('=== _extract_context_speakers ===')
    ctx_before = text.split('\"')[0] if '\"' in text else text
    ctx_after = text.split('\"')[-1] if '\"' in text else ''
    print(f'context_before: {ctx_before[:60]}')
    print(f'context_after: {ctx_after[:60]}')
    
    context_candidates = sm._extract_context_speakers(text, ctx_before, ctx_after)
    print(f'上下文候选: {context_candidates[:3]}')
    print()
    
    # 5. 完整分析
    results = sm.analyze_dialogue(text, chapter_id=1)
    print(f'=== 分析结果 ===')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        print(f'对话{i+1}: [{dialogue}] -> {actual}')
    
    try:
        os.unlink(db_path)
    except:
        pass

def main():
    chars = [('药老', 'male'), ('萧炎', 'male')]
    print('=== P7 诊断 ===')
    diagnose(P7, chars)
    
    print('\n=== P18 诊断 ===')
    diagnose(P18, chars)

if __name__ == '__main__':
    main()
