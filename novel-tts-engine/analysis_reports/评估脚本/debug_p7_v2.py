"""诊断P7为什么声音指示模式没有生效"""
import sys, os
import re, tempfile, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

P7 = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起："这枚丹药，你先服下。"萧炎点头照做。"感觉如何？"老者问道。'

db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = db_file.name
db_file.close()

cm = CharacterManager(db_path=db_path)
project_id = f'test_{uuid.uuid4().hex[:8]}'

cm.add_character(name='药老', project_id=project_id, aliases=set(), gender='male')
cm.add_character(name='萧炎', project_id=project_id, aliases=set(), gender='male')

sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
sm._current_project_id = project_id

# 手动分析对话
results = sm.analyze_dialogue(P7, chapter_id=1)
print(f'共{len(results)}段对话:')
for i, (dialogue, speaker) in enumerate(results):
    actual = speaker.name if speaker else '未知'
    print(f'  对话{i+1}: [{dialogue}] -> {actual}')

# 诊断对话1
print()
print('=== 手动诊断对话1 ===')
# 对话1: "这枚丹药，你先服下。"
# context_before应该是: "萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起："
ctx_before = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起：'
text = '"这枚丹药，你先服下。"'

# 直接测试_extract_context_speakers
candidates = sm._extract_context_speakers(text, ctx_before, '')
print(f'_extract_context_speakers返回: {candidates}')
print()

# 检查是否匹配到声音指示
project_chars = cm.get_all_characters(project_id=project_id)
print(f'项目角色: {[c.name for c in project_chars]}')
for char in project_chars:
    patterns = [
        rf'{char.name}的声音',
        rf'{char.name}在脑海',
        rf'{char.name}心中',
        rf'{char.name}传音',
    ]
    for pattern in patterns:
        if re.search(pattern, ctx_before):
            print(f'  匹配: {char.name} pattern={pattern}')

try:
    os.unlink(db_path)
except:
    pass
