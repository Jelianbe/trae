# -*- coding: utf-8 -*-
"""
L2语义排序层对比测试 v2
先构建对话历史，再评估L2效果。
"""
import sys
from pathlib import Path
import os
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

import pipeline.nlp_basics as nlp_basics
original_analyze = nlp_basics.NLPBasics.analyze
def quiet_analyze(self, text):
    import sys
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        result = original_analyze(self, text)
    finally:
        sys.stdout = old_stdout
    return result
nlp_basics.NLPBasics.analyze = quiet_analyze

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import json

def evaluate_with_l2(novel_text, gt_dialogue_speakers, char_manager, enable_l2=False):
    """评估说话人匹配，可选启用L2。"""
    if enable_l2:
        semantic_ranker = get_semantic_ranker(enable_l2=True)
        semantic_ranker.load_model()
        matcher = SpeakerMatcher(character_manager=char_manager, semantic_ranker=semantic_ranker, l2_threshold=0.55)
    else:
        matcher = SpeakerMatcher(character_manager=char_manager, semantic_ranker=None)
    
    # 评估 - 按章节顺序处理
    correct = 0
    total = 0
    prev_speaker = None
    current_chapter = 0
    
    gt_map = {}
    for item in gt_dialogue_speakers:
        text_key = item["text"][:30]
        gt_map[text_key] = item["speaker"]
    
    # 按章节分段处理
    lines = novel_text.split('\n')
    chapter_lines = []
    for line in lines:
        if re.match(r'(?:第[一二三四五六七八九十\d]+[章节回卷]|#{1,6}\s*第[一二三四五六七八九十\d]+[章节回卷])', line):
            if chapter_lines:
                # 处理当前章节
                for line_text in chapter_lines:
                    line_text = line_text.strip()
                    if not line_text or '"' not in line_text:
                        continue
                    
                    gt_speaker = None
                    for key, speaker in gt_map.items():
                        if key in line_text:
                            gt_speaker = speaker
                            break
                    if not gt_speaker:
                        continue
                    
                    total += 1
                    ctx = DialogueContext(
                        text=line_text,
                        chapter_id=current_chapter,
                        prev_speaker=prev_speaker
                    )
                    result = matcher.match_speaker(ctx)
                    matched_name = result.character.name if result else None
                    
                    if matched_name == gt_speaker:
                        correct += 1
                        prev_speaker = matched_name
                    else:
                        prev_speaker = gt_speaker
                
                current_chapter += 1
                chapter_lines = []
        
        chapter_lines.append(line)
    
    # 处理最后一章
    for line_text in chapter_lines:
        line_text = line_text.strip()
        if not line_text or '"' not in line_text:
            continue
        
        gt_speaker = None
        for key, speaker in gt_map.items():
            if key in line_text:
                gt_speaker = speaker
                break
        if not gt_speaker:
            continue
        
        total += 1
        ctx = DialogueContext(
            text=line_text,
            chapter_id=current_chapter,
            prev_speaker=prev_speaker
        )
        result = matcher.match_speaker(ctx)
        matched_name = result.character.name if result else None
        
        if matched_name == gt_speaker:
            correct += 1
            prev_speaker = matched_name
        else:
            prev_speaker = gt_speaker
    
    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)


test_cases = [
    ('tests/test_novel_urban.txt', 'tests/test_novel_urban_ground_truth.json'),
    ('tests/test_novel_western.txt', 'tests/test_novel_western_ground_truth.json'),
]

for test_file, gt_file in test_cases:
    test_path = Path(test_file)
    gt_path = Path(gt_file)
    
    if not test_path.exists() or not gt_path.exists():
        print(f"文件不存在: {test_path} 或 {gt_path}")
        continue
    
    novel_text = test_path.read_text(encoding='utf-8')
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    
    persons = gt.get("entities", {}).get("persons", [])
    aliases_map = gt.get("entities", {}).get("aliases", {})
    gt_dialogue_speakers = gt.get("dialogue_speakers", [])
    
    print("=" * 70)
    print(f"L2对比测试：{test_path.stem}")
    print("=" * 70)
    
    # L2关闭
    print("\n【L2关闭】")
    char_manager_off = CharacterManager()
    for name in persons:
        aliases = set()
        if aliases_map and name in aliases_map:
            aliases = set(aliases_map[name])
        char_manager_off.add_character(name, gender="unknown", aliases=aliases)
    speaker_off = evaluate_with_l2(novel_text, gt_dialogue_speakers, char_manager_off, enable_l2=False)
    print(f"说话人匹配: {speaker_off}")
    
    # L2开启
    print("\n【L2开启】")
    char_manager_on = CharacterManager()
    for name in persons:
        aliases = set()
        if aliases_map and name in aliases_map:
            aliases = set(aliases_map[name])
        char_manager_on.add_character(name, gender="unknown", aliases=aliases)
    speaker_on = evaluate_with_l2(novel_text, gt_dialogue_speakers, char_manager_on, enable_l2=True)
    print(f"说话人匹配: {speaker_on}")
    
    # 对比
    diff = speaker_on - speaker_off
    print(f"\n【差异】说话人匹配: {'+' if diff > 0 else ''}{diff:.1f}")
    print()
