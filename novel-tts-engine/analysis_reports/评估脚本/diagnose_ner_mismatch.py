"""诊断NER误匹配问题：P7/P10/P15/P18中"药老"被"萧炎"覆盖"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

# P7：药老场景
P7_TEXT = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起：\"这枚丹药，你先服下。\"萧炎点头照做。\"感觉如何？\"老者问道。'

# P10：药老场景
P10_TEXT = '\"这枚丹药至少值三万金币。\"药老说道，\"你现在还无法判断它的真正价值。\"萧炎沉思片刻。\"至少三万金币。\"他喃喃道。'

# P15：药老场景
P15_TEXT = '苏夜看着手中的丹药。\"这丹药如何？\"林雪问道。萧炎仔细观察着，药老在脑海中轻声道：\"至少三品。\"'

# P18：药老场景
P18_TEXT = '萧炎站在练功场中央，汗水浸透了衣衫。\"萧炎，你太弱了！\"药老的声音响起。\"我知道。\"少年咬牙道，\"再来一次。\"'

def diagnose_ner(text, precreate_chars=None):
    """诊断NER处理流程"""
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
    
    print(f'全文: {text}')
    print()
    
    # 测试NER提取
    from pipeline.text_utils import extract_entities
    entities = extract_entities(text)
    print(f'NER实体: {entities}')
    print()
    
    # 测试分词
    import hanlp
    tokenizer = hanlp.load('PKU_NAME_MERGED_SIX_MONTHS_PRUNE')
    tokens = tokenizer(text)
    print(f'分词结果: {tokens}')
    print()
    
    # 运行完整匹配
    results = sm.analyze_dialogue(text, chapter_id=1)
    print(f'分析结果: {len(results)}段对话')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        print(f'  对话{i+1}: [{dialogue}] -> {actual}')
        # 测试NER
        ner_results = sm._extract_from_ner(text)
        if ner_results:
            print(f'    NER: {ner_results}')
    
    try:
        os.unlink(db_path)
    except:
        pass

def main():
    precreate_chars = [
        ('药老', 'male'), ('萧炎', 'male'), ('苏夜', 'male'), ('林雪', 'female'),
    ]
    
    print('=== P7 诊断 ===')
    diagnose_ner(P7_TEXT, precreate_chars)
    
    print('\n=== P10 诊断 ===')
    diagnose_ner(P10_TEXT, precreate_chars)
    
    print('\n=== P18 诊断 ===')
    diagnose_ner(P18_TEXT, precreate_chars)

if __name__ == '__main__':
    main()
