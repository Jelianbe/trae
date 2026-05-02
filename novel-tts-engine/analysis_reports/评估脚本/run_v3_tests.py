# -*- coding: utf-8 -*-
"""泛化性测试 v3 运行器 - 使用完整算法管道（修正版）"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Project root
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

from evaluate_generalization_v3 import *

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
    
    # 初始化角色管理器并注册角色
    char_manager = CharacterManager()
    persons = gt.get("entities", {}).get("persons", [])
    aliases_map = gt.get("entities", {}).get("aliases", {})
    register_characters(char_manager, persons, aliases_map)
    
    print("=" * 60)
    print(f"泛化性评估 v3：{test_path.stem}")
    print("=" * 60)
    
    # 1. 章节划分
    chapter_score = evaluate_chapter_splitter(novel_text, gt.get("chapters", {}))
    print(f"章节划分: {chapter_score}")
    
    # 2. 对话分类
    dialogue_score = evaluate_dialogue_classifier(novel_text, gt.get("对话分类", {}))
    print(f"对话分类: {dialogue_score}")
    
    # 3. 拟声词检测
    sfx_score = evaluate_sfx_detector(novel_text, gt.get("sfx", {}))
    print(f"拟声词检测: {sfx_score}")
    
    # 4. NER
    ner_score = evaluate_ner(novel_text, gt.get("entities", {}))
    print(f"命名实体识别: {ner_score}")
    
    # 5. 说话人匹配（分别测试L2关闭和开启）
    print("\n--- L2 关闭 ---")
    speaker_score_off = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager, enable_l2=False)
    print(f"说话人匹配: {speaker_score_off}")
    
    print("\n--- L2 开启 ---")
    speaker_score_on = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager, enable_l2=True)
    print(f"说话人匹配: {speaker_score_on}")
    
    speaker_score = speaker_score_on  # 使用L2开启的分数作为主分数
    print(f"\n说话人匹配最终分数(L2开启): {speaker_score}")
    
    avg = (chapter_score + dialogue_score + sfx_score + ner_score + speaker_score) / 5
    print(f"\n平均得分: {avg:.1f}")
    print()
