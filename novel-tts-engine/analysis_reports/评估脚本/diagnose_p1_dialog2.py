"""诊断P1对话2为什么返回未知"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

# P1对话2的上下文
# 原文: 林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"
# 对话2: "客官来得巧，正好还剩一间。"
# prefix: "掌柜抬头看了看他，笑道："
# suffix: ""

prefix = '掌柜抬头看了看他，笑道：'
suffix = ''
dialogue = '客官来得巧，正好还剩一间。'

# Create temp DB
db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = db_file.name
db_file.close()
cm = CharacterManager(db_path=db_path)
project_id = f'test_{uuid.uuid4().hex[:8]}'

# Pre-create characters
for name in ['林轩', '掌柜']:
    cm.add_character(name=name, project_id=project_id, aliases=set(), gender='male')

# Create matcher
sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
sm._current_project_id = project_id

print(f'prefix: {prefix}')
print(f'suffix: {suffix}')
print()

# Test identity word extraction
print('=== 身份词提取测试 ===')
identity_words_prefix = sm._extract_identity_words(prefix)
print(f'prefix中的身份词: {identity_words_prefix}')

identity_words_suffix = sm._extract_identity_words(suffix)
print(f'suffix中的身份词: {identity_words_suffix}')
print()

# Test character library matching
narration = sm._extract_narration(prefix, context_after=suffix)
print(f'旁白内容: {narration}')
char_match = sm._match_from_character_library(narration)
print(f'角色库匹配: {char_match.name if char_match else "None"}')
print()

# Test NER
ner_results = sm._extract_from_ner(narration)
print(f'NER结果: {ner_results}')
print()

# Test _extract_context_speakers
context_candidates = sm._extract_context_speakers(dialogue, prefix, suffix)
print(f'上下文候选: {context_candidates}')
print()

# Test full match_speaker
context = DialogueContext(
    text=prefix + dialogue + suffix,
    speaker_hint=None,
    prev_speaker='林轩',
    mentioned_characters=['掌柜'],
    chapter_id=1,
    context_before=prefix,
    context_after=suffix,
)
match_result = sm.match_speaker(context)
if match_result:
    print(f'最终匹配: {match_result.character.name} (method={match_result.match_type})')
else:
    print('最终匹配: None (未知)')

try:
    os.unlink(db_path)
except:
    pass
