"""诊断角色识别率回退 — 直接跟踪匹配路径"""
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

# 用测试脚本的实际段落
test_paragraph = '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"'

print("=== 段落分析 ===")
print(f"输入: {test_paragraph}")
print()

# Step 1: 看 NLP 分析
from pipeline.nlp_analyzer import NLPAnalyzer
nlp = NLPAnalyzer()
result = nlp.analyze(test_paragraph)
print(f"NER 实体: {[(e.text, e.type) for e in result.entities]}")
print()

# Step 2: 看 _combine_fragments 结果
sentences = sm.analyze_dialogue(test_paragraph, chapter_id=1)
print(f"=== analyze_dialogue 结果 ({len(sentences)} 句) ===")
for i, (text, speaker) in enumerate(sentences):
    print(f"  {i+1}. {text[:50]} -> {speaker.name if speaker else '未知'}")
print()

# Step 3: 看 _extract_context_speakers 详细输出
import re
from pipeline.dialogue_classifier import DIALOGUE_PATTERNS

# 模拟测试脚本的段落处理
from pipeline.context_window_builder import ContextWindowBuilder
context_builder = ContextWindowBuilder()

# 模拟测试脚本的段落格式
test_data = {
    'id': 'P1',
    'paragraph': test_paragraph,
    'dialogues': [
        ('"来一间上房。"', {'name': '林轩', 'gender': 'male'}),
        ('"客官来得巧，正好还剩一间。"', {'name': '掌柜', 'gender': 'male'}),
    ]
}

print("=== 逐句匹配诊断 ===")
# 模拟测试脚本中的匹配
for expected_dialogue, expected_speaker in test_data['dialogues']:
    print(f"\n--- 期望: {expected_dialogue} -> {expected_speaker['name']} ---")
    
    # 找到匹配的句子
    matched = None
    for text, speaker in sentences:
        if expected_dialogue.strip('"') in text or expected_dialogue.replace('"', '') in text.replace('"', ''):
            matched = (text, speaker)
            break
    
    if matched:
        text, speaker = matched
        print(f"  实际匹配: {text[:40]}... -> {speaker.name if speaker else '未知'}")
    else:
        print(f"  未找到匹配句子")

# Step 4: 看 _extract_identity_words 的实际输出
print("\n=== 身份词提取 ===")
for ctx in [test_paragraph]:
    words = sm._extract_identity_words(ctx)
    print(f"  全文: {ctx[:60]}... -> 身份词: {words}")
