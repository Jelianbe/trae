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

reset_semantic_ranker()
ranker = get_semantic_ranker(enable_l2=True)
ranker.load_model()

sm = SpeakerMatcher(character_manager=cm, semantic_ranker=ranker)
sm._current_project_id = project_id

# 测试身份词提取
text = '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"'

print("=== 身份词提取测试 ===")
for ctx in ['林轩推开客栈的门，对着掌柜说道：', '掌柜抬头看了看他，笑道：']:
    words = sm._extract_identity_words(ctx)
    print(f"  上下文: {ctx[:40]}... -> 身份词: {words}")

print("\n=== 完整 _extract_context_speakers 测试 ===")
# 分析段落，看候选人生成
text_parts = sm._split_dialogue_text(text)
print(f"拆分结果: {text_parts}")

if len(text_parts) >= 3:
    context_before = text_parts[0]  # 旁白
    dialogue_text = text_parts[1]   # 对话1
    context_after = text_parts[2]   # 旁白2 + 对话2

    # 对于第一段对话 "来一间上房。"
    # context_before = "林轩推开客栈的门，对着掌柜说道："
    # context_after = "掌柜抬头看了看他，笑道：..."
    
    print(f"\n对于第一段对话:")
    print(f"  context_before: {context_before[:50]}")
    print(f"  context_after: {context_after[:50]}")
    
    # 提取候选
    candidates = sm._extract_context_speakers(dialogue_text, context_before, context_after)
    print(f"  候选人生成: {candidates}")

    print(f"\n对于第二段对话:")
    # 第二段对话的 context_before 包含第一段对话和旁白
    # 需要看 analyze_dialogue 如何构造上下文
    
    results = sm.analyze_dialogue(text, chapter_id=1)
    print(f"\n最终结果:")
    for dialogue_text, speaker in results:
        print(f"  对话: {dialogue_text[:30]} -> {speaker.name if speaker else '未知'}")
