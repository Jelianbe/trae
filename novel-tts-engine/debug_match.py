import sys, os, uuid
sys.path.insert(0, '.')
os.environ['DEBUG_NER'] = '0'

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker, reset_semantic_ranker
import tempfile

print("=== 诊断角色库匹配问题 ===\n")

db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = db_file.name
db_file.close()

cm = CharacterManager(db_path=db_path)
project_id = f'test_diag_{uuid.uuid4().hex[:8]}'

# 预创建18个角色
precreate_chars = [
    ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
    ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
    ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
    ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
    ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
    ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
]
for name, gender in precreate_chars:
    cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)

all_chars = cm.get_all_characters(project_id)
print(f"项目 {project_id} 中的角色数: {len(all_chars)}")
print(f"角色名列表: {[c.name for c in all_chars]}\n")

# 测试 get_character_by_name
for test_name in ['掌柜', '小翠', '林轩', '白发老者']:
    char = cm.get_character_by_name(test_name, project_id)
    print(f"  get_by_name('{test_name}') -> {char.name if char else 'None'}")

# 测试 _match_candidate_to_character
reset_semantic_ranker()
ranker = get_semantic_ranker(enable_l2=True)
ranker.load_model()

sm = SpeakerMatcher(character_manager=cm, semantic_ranker=ranker)
sm._current_project_id = project_id

print(f"\n=== _match_candidate_to_character 测试 ===")
for candidate in ['掌柜', '小翠', '林轩', '白发老者', '小姐']:
    result = sm._match_candidate_to_character(candidate, '')
    if result:
        print(f"  '{candidate}' -> {result.name} (id={result.id})")
    else:
        print(f"  '{candidate}' -> None")

print(f"\n=== analyze_dialogue 端到端测试 ===")
test_paragraph = '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"'
sm.reset_activity()
results = sm.analyze_dialogue(test_paragraph, chapter_id=1)
for dialogue_text, speaker in results:
    print(f"  对话: {dialogue_text[:30]} -> 说话人: {speaker.name if speaker else '未知'} (id={speaker.id if speaker else '?'})")
