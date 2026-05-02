# -*- coding: utf-8 -*-
"""调试都市异能说话人匹配"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
import json
import re

test_file = Path('tests/test_novel_urban.txt')
gt_file = Path('tests/test_novel_urban_ground_truth.json')

novel_text = test_file.read_text(encoding='utf-8')
with open(gt_file, 'r', encoding='utf-8') as f:
    gt = json.load(f)

char_manager = CharacterManager()
persons = gt.get("entities", {}).get("persons", [])
aliases_map = gt.get("entities", {}).get("aliases", {})

for name in persons:
    aliases = set()
    if aliases_map and name in aliases_map:
        aliases = set(aliases_map[name])
    char_manager.add_character(name, gender="unknown", aliases=aliases)

matcher = SpeakerMatcher(character_manager=char_manager)

gt_dialogue_speakers = gt.get("dialogue_speakers", [])
gt_map = {}
for item in gt_dialogue_speakers:
    text_key = item["text"][:30]
    gt_map[text_key] = item["speaker"]

sentences = []
for line in novel_text.split('\n'):
    line = line.strip()
    if not line:
        continue
    if '"' in line or '"' in line or "'" in line:
        sentences.append(('dialogue', line))
    else:
        sentences.append(('narration', line))

correct = 0
total = 0
prev_speaker = None
errors = []

for line_type, line_text in sentences:
    if line_type != 'dialogue':
        continue
    
    gt_speaker = None
    for key, speaker in gt_map.items():
        if key in line_text:
            gt_speaker = speaker
            break
    if not gt_speaker:
        continue
    
    total += 1
    char, matched_name = matcher.get_speaker_for_sentence(
        line_text,
        prev_speaker=prev_speaker
    )
    
    if matched_name == gt_speaker:
        correct += 1
        prev_speaker = matched_name
    else:
        errors.append({
            'text': line_text[:50],
            'expected': gt_speaker,
            'got': matched_name if matched_name else 'None',
            'prev_speaker': prev_speaker
        })
        prev_speaker = gt_speaker

print(f"总对话数: {total}")
print(f"正确: {correct}")
print(f"准确率: {correct/total*100:.1f}%")
print(f"\n错误详情（前20个）:")
for i, err in enumerate(errors[:20]):
    print(f"\n{i+1}. 文本: ...{err['text']}")
    print(f"   期望: {err['expected']}, 实际: {err['got']}, 前一个说话人: {err['prev_speaker']}")
