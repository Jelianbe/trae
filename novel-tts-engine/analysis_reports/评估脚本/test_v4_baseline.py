"""使用v4备份版本的speaker_matcher.py进行对比测试"""
import sys, os
import importlib.util

# Load v4 version
spec_v4 = importlib.util.spec_from_file_location("speaker_matcher_v4", os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline', 'speaker_matcher_v4_backup.py'))
speaker_matcher_v4 = importlib.util.module_from_spec(spec_v4)
spec_v4.loader.exec_module(speaker_matcher_v4)

from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

# Test data
P1_TEXT = '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"'
P12_TEXT = '一个白发老者缓缓走来。他捋了捋胡须说道："年轻人，你与我有缘。"苏夜愣住了。'

def test_with_v4():
    """测试v4版本"""
    print('=== V4版本测试 ===')
    
    for test_name, text, expected in [
        ('P1', P1_TEXT, ['林轩', '掌柜']),
        ('P12', P12_TEXT, ['白发老者'])
    ]:
        print(f'\n--- {test_name} ---')
        print(f'全文: {text}')
        print(f'期望: {expected}')
        
        # Create temp DB
        db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        db_path = db_file.name
        db_file.close()
        cm = CharacterManager(db_path=db_path)
        project_id = f'test_{uuid.uuid4().hex[:8]}'
        
        # Pre-create characters
        for name in set(expected):
            cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')
        
        # Create v4 matcher
        sm = speaker_matcher_v4.SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
        sm._current_project_id = project_id
        
        results = sm.analyze_dialogue(text, chapter_id=1)
        print(f'结果: {[speaker.name if speaker else "未知" for dialogue, speaker in results]}')
        
        for i, (dialogue, speaker) in enumerate(results):
            actual = speaker.name if speaker else '未知'
            exp = expected[i] if i < len(expected) else '?'
            status = '✅' if actual == exp else '❌'
            print(f'  对话{i+1}: [{dialogue[:20]}] 期望={exp} 实际={actual} {status}')
        
        try:
            os.unlink(db_path)
        except:
            pass

if __name__ == '__main__':
    test_with_v4()
