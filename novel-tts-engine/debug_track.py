"""精确跟踪 _match_candidate_to_character 的行为"""
import sys, os, uuid
sys.path.insert(0, '.')
os.environ['DEBUG_NER'] = '0'

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker, reset_semantic_ranker
import tempfile

db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = db_file.name
db_file.close()

cm = CharacterManager(db_path=db_path)
project_id = f'test_{uuid.uuid4().hex[:8]}'

# 预创建角色
cm.add_character(name='掌柜', project_id=project_id, aliases=set(), gender='male')
cm.add_character(name='林轩', project_id=project_id, aliases=set(), gender='male')

print(f"角色库中角色: {[c.name for c in cm.get_all_characters(project_id)]}")
print(f"get_by_name('掌柜'): {cm.get_character_by_name('掌柜', project_id)}")

reset_semantic_ranker()
ranker = get_semantic_ranker(enable_l2=True)
ranker.load_model()

sm = SpeakerMatcher(character_manager=cm, semantic_ranker=ranker)
sm._current_project_id = project_id

# 直接测试 _match_candidate_to_character
print("\n=== _match_candidate_to_character 测试 ===")
for candidate in ['掌柜', '林轩', '陌生人']:
    result = sm._match_candidate_to_character(candidate, '')
    if result:
        print(f"  '{candidate}' -> name='{result.name}', id={result.id}")
    else:
        print(f"  '{candidate}' -> None")

# 测试完整流程
print("\n=== analyze_dialogue 端到端 ===")
text = '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧。"'
sm.reset_activity()
results = sm.analyze_dialogue(text, chapter_id=1)

for dialogue_text, speaker in results:
    print(f"  对话: {dialogue_text[:30]} -> 说话人: {speaker.name if speaker else '未知'}, id={speaker.id if speaker else '?'}")
