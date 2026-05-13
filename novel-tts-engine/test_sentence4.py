# -*- coding: utf-8 -*-
"""追踪句子 [4] 的说话人匹配过程"""
import sys
sys.path.insert(0, '.')

test_text = """第一章：周末计划

「小明，这周末你有什么打算吗？」林悦问道。
「嗯……我本来想宅在家打游戏，但感觉太浪费了。你呢？」小明回答。
林悦笑了笑说：「我想去郊外的枫叶谷看看，听说现在红叶正美。」
小明眼睛一亮：「好主意！我正好也想出去走走。」
「那我们周六早上八点在学校门口集合吧。」林悦说道。
「没问题，我会准时到的。」小明点点头。"""

from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS

# 提取所有对话
dialogues = []
seen_ranges = []

for pattern in DIALOGUE_PATTERNS:
    for match in pattern.finditer(test_text):
        start, end = match.start(), match.end()
        dialogue = match.group(1)
        is_overlap = False
        for s, e in seen_ranges:
            if start < e and end > s:
                is_overlap = True
                break
        if not is_overlap:
            dialogues.append((start, end, dialogue))
            seen_ranges.append((start, end))

dialogues.sort(key=lambda x: x[0])

print("提取到的对话:")
for i, (s, e, d) in enumerate(dialogues):
    print(f"  [{i}] [{s},{e}): {d[:40]}...")

# 句子 [4] 对应 dialogues[4]
idx = 4
start, end, dialogue = dialogues[idx]

prefix_start = dialogues[idx-1][1] if idx > 0 else 0
prefix = test_text[prefix_start:start].strip()

suffix_end = dialogues[idx+1][0] if idx < len(dialogues) - 1 else len(test_text)
suffix = test_text[end:suffix_end].strip()

print(f"\n句子 [4] ({dialogue[:30]}...) 的上下文:")
print(f"  prefix: '{prefix}'")
print(f"  suffix: '{suffix}'")

# 提取说话人提示
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import DialogueContext

char_manager = CharacterManager()
speaker_matcher = SpeakerMatcher(char_manager)
speaker_matcher._current_project_id = "test_s4"

speaker_hint, hint_type = speaker_matcher.extract_speaker_hint(prefix + " " + suffix)
print(f"\nextract_speaker_hint 返回: hint='{speaker_hint}', type='{hint_type}'")

# 模拟 match_speaker
context = DialogueContext(
    text=prefix + " " + dialogue + " " + suffix,
    speaker_hint=speaker_hint,
    prev_speaker=None,
    mentioned_characters=[],
    chapter_id=0,
    context_before=prefix,
    context_after=suffix,
)

print(f"\n调用 match_speaker...")
match_result = speaker_matcher.match_speaker(context)

if match_result and match_result.character:
    c = match_result.character
    print(f"  → character: name='{c.name}', id={c.id}")
    print(f"  → confidence: {match_result.confidence}")
    print(f"  → match_type: {match_result.match_type}")
    
    is_valid = c.name != '未知' and not c.name.startswith('未知_')
    print(f"  → 是否有效: {is_valid}")
    
    if is_valid:
        char_manager.find_or_create(c.name, project_id="test_s4")
else:
    print(f"  → None")
