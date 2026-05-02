# -*- coding: utf-8 -*-
"""
L2语义排序层对比测试脚本
对比L2启用和关闭的效果差异。
"""
import sys
from pathlib import Path
import os
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

# Suppress all debug prints
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

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import NLPBasics
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.semantic_ranker import get_semantic_ranker
from analysis_reports.evaluate_generalization_v3 import *

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
    gt = load_ground_truth(gt_path)
    
    print("=" * 70)
    print(f"L2对比测试：{test_path.stem}")
    print("=" * 70)
    
    # ---- L2关闭模式 ----
    print("\n【L2关闭】")
    char_manager_l2_off = CharacterManager()
    persons = gt.get("entities", {}).get("persons", [])
    aliases_map = gt.get("entities", {}).get("aliases", {})
    register_characters(char_manager_l2_off, persons, aliases_map)
    matcher_l2_off = SpeakerMatcher(character_manager=char_manager_l2_off, semantic_ranker=None)
    speaker_score_l2_off = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager_l2_off)
    avg_l2_off = (100 + 100 + 88.9 + 36.8 + speaker_score_l2_off) / 5
    print(f"说话人匹配: {speaker_score_l2_off}")
    print(f"平均得分: {avg_l2_off:.1f}")
    
    # ---- L2开启模式 ----
    print("\n【L2开启】")
    char_manager_l2_on = CharacterManager()
    register_characters(char_manager_l2_on, persons, aliases_map)
    semantic_ranker = get_semantic_ranker(enable_l2=True)
    semantic_ranker.load_model()
    matcher_l2_on = SpeakerMatcher(character_manager=char_manager_l2_on, semantic_ranker=semantic_ranker)
    speaker_score_l2_on = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager_l2_on)
    avg_l2_on = (100 + 100 + 88.9 + 36.8 + speaker_score_l2_on) / 5
    print(f"说话人匹配: {speaker_score_l2_on}")
    print(f"平均得分: {avg_l2_on:.1f}")
    
    # ---- 对比 ----
    diff_speaker = speaker_score_l2_on - speaker_score_l2_off
    diff_avg = avg_l2_on - avg_l2_off
    print(f"\n【差异】")
    print(f"说话人匹配: {'+' if diff_speaker > 0 else ''}{diff_speaker:.1f}")
    print(f"平均得分: {'+' if diff_avg > 0 else ''}{diff_avg:.1f}")
    print()
