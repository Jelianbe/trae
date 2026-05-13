"""快速诊断P1/P12/P4等关键失败案例"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

# Test cases
P1_TEXT = '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"'
P12_TEXT = '一个白发老者缓缓走来。他捋了捋胡须说道："年轻人，你与我有缘。"苏夜愣住了。'

def test_p1():
    """P1: 掌柜测试"""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    # Pre-create characters
    for name in ['林轩', '掌柜']:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    print('=== P1 测试 ===')
    print(f'全文: {P1_TEXT}')
    print()
    
    # Test identity word extraction
    prefix = '林轩推开客栈的门，对着掌柜说道：'
    print(f'prefix: {prefix}')
    identity_words = sm._extract_identity_words(prefix)
    print(f'提取的身份词: {identity_words}')
    print()
    
    # Test character library matching
    narration = sm._extract_narration(prefix)
    print(f'旁白内容: {narration}')
    char_match = sm._match_from_character_library(narration)
    print(f'角色库匹配: {char_match.name if char_match else "None"}')
    print()
    
    # Run full analysis
    results = sm.analyze_dialogue(P1_TEXT, chapter_id=1)
    print(f'=== 分析结果 ===')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        print(f'对话{i+1}: [{dialogue}] -> {actual}')
    
    try:
        os.unlink(db_path)
    except:
        pass

def test_p12():
    """P12: 白发老者测试"""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    # Pre-create characters
    for name in ['白发老者', '苏夜']:
        cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    print('\n\n=== P12 测试 ===')
    print(f'全文: {P12_TEXT}')
    print()
    
    # Run full analysis
    results = sm.analyze_dialogue(P12_TEXT, chapter_id=1)
    print(f'=== 分析结果 ===')
    for i, (dialogue, speaker) in enumerate(results):
        actual = speaker.name if speaker else '未知'
        print(f'对话{i+1}: [{dialogue}] -> {actual}')
    
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    test_p1()
    test_p12()
