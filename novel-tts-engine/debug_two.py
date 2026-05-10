# -*- coding: utf-8 -*-
"""T-007 测试双对话场景"""
from pipeline.speaker_hint_matcher import SpeakerHintMatcher, SPEAKER_PATTERNS, DIALOGUE_PATTERNS
from pipeline.character_name_validator import CharacterNameValidator
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
import tempfile
import os

validator = CharacterNameValidator()
matcher = SpeakerHintMatcher(validator)

print("=== 测试双对话场景 ===")
text = '林轩说道："你好。"小翠回应道："你好呀。"'
print(f"文本: {text}")
print()

dialogues = []
seen_positions = set()

for pattern in DIALOGUE_PATTERNS:
    for m in pattern.finditer(text):
        start, end = m.start(), m.end()
        if start not in seen_positions:
            dialogues.append((start, end, m.group(1)))
            seen_positions.add(start)

dialogues.sort(key=lambda x: x[0])
print(f"找到 {len(dialogues)} 个对话:")
for i, (start, end, dialogue) in enumerate(dialogues):
    prefix_start = dialogues[i-1][1] if i > 0 else 0
    prefix = text[prefix_start:start].strip()
    suffix_end = dialogues[i+1][0] if i < len(dialogues) - 1 else len(text)
    suffix = text[end:suffix_end].strip()
    hint_text = prefix + " " + suffix
    
    hint, hint_type = matcher.extract_speaker_hint(hint_text)
    print(f"  对话 {i+1}: start={start}, {repr(dialogue)}")
    print(f"    prefix: {repr(prefix)}")
    print(f"    suffix: {repr(suffix)}")
    print(f"    hint_text: {repr(hint_text)}")
    print(f"    speaker_hint: {repr(hint)}, type: {hint_type}")
    print()

print("\n=== analyze_dialogue 结果 ===")
db = tempfile.mktemp(suffix='.db')
cm = CharacterManager(db)
cm.add_character('林轩', gender='male')
cm.add_character('小翠', gender='female')
sm = SpeakerMatcher(cm)

results = sm.analyze_dialogue(text)
for d, c in results:
    print(f"  对话: {repr(d)} -> 说话人: {c.name if c else None}")

os.remove(db)
