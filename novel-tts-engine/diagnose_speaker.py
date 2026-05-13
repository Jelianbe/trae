import sys, os
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
project_id = 'test_diag'

precreate_chars = [
    ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
    ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
    ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
    ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
    ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
    ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
]

for name, gender in precreate_chars:
    char = cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    print(f"  创建角色: {name} (id={char.id})")

all_chars = cm.get_all_characters()
print(f"\n角色库中共 {len(all_chars)} 个角色")
print("角色列表:", [c.name for c in all_chars])

reset_semantic_ranker()
ranker = get_semantic_ranker(enable_l2=True)
ranker.load_model()

sm = SpeakerMatcher(character_manager=cm, semantic_ranker=ranker)
sm._current_project_id = project_id

test_cases = [
    ('林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"'),
    ('小翠端着茶走进书房，轻声道："小姐，该用茶了。"'),
]

for text in test_cases:
    print(f"\n--- 测试: {text[:50]}... ---")
    sm.reset_activity()
    results = sm.analyze_dialogue(text, chapter_id=1)
    for dialogue_text, speaker in results:
        print(f"  对话: {dialogue_text[:30]} -> 说话人: {speaker.name if speaker else '未知'}")
        if speaker:
            print(f"    (id={speaker.id}, gender={speaker.gender})")

print("\n=== 诊断完成 ===")
