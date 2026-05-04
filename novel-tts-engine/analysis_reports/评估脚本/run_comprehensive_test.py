# -*- coding: utf-8 -*-
"""
综合分析能力测试脚本
测试整个文本分析管道的能力：
1. 对话分类 - 判断哪些句子是对话
2. 引号内容分类 - 判断引号内容是对话/心理活动/书面内容
3. 说话人识别 - 识别对话的说话人
"""
import sys
import os
from pathlib import Path
import json
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ['DEBUG_NER'] = '0'

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.quotation_classifier import QuotationClassifier, QuotationType
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import get_nlp
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.semantic_ranker import get_semantic_ranker


def normalize_quotes(text):
    """统一中英文引号"""
    return text.replace('\u201c', '"').replace('\u201d', '"')


def load_ground_truth(gt_path):
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def register_characters(char_manager, persons, aliases_map=None):
    for name in persons:
        aliases = set()
        if aliases_map and name in aliases_map:
            aliases = set(aliases_map[name])
        existing = char_manager.get_character_by_name(name)
        if not existing:
            char_manager.add_character(name, gender="unknown", aliases=aliases)
        else:
            for alias in aliases:
                char_manager.add_alias(existing.id, alias)


def extract_dialogues_from_text(text):
    """从文本中提取所有带引号的内容"""
    dialogues = []
    # 匹配中文引号和英文引号
    pattern = r'(["""])([^"""]*?)\1'
    for match in re.finditer(pattern, text):
        dialogues.append({
            'full_match': match.group(0),
            'content': match.group(2),
            'quote_char': match.group(1),
            'start': match.start(),
            'end': match.end()
        })
    return dialogues


def run_comprehensive_test(test_file, gt_file):
    """运行综合测试"""
    print("=" * 70)
    print(f"综合分析能力测试: {Path(test_file).stem}")
    print("=" * 70)
    
    # 加载数据
    novel_text = Path(test_file).read_text(encoding='utf-8')
    gt = load_ground_truth(gt_file)
    
    # 初始化组件
    dialogue_classifier = DialogueClassifier()
    quotation_classifier = QuotationClassifier()
    char_manager = CharacterManager()
    
    persons = gt.get("entities", {}).get("persons", [])
    aliases_map = gt.get("entities", {}).get("aliases", {})
    register_characters(char_manager, persons, aliases_map)
    
    semantic_ranker = get_semantic_ranker(enable_l2=True)
    semantic_ranker.load_model()
    
    speaker_matcher = SpeakerMatcher(
        character_manager=char_manager,
        semantic_ranker=semantic_ranker,
        l2_threshold=0.55,
    )
    
    # ========== 1. 对话分类测试 ==========
    print("\n【1. 对话分类测试】")
    print("-" * 50)
    
    sentences = [s.strip() for s in novel_text.split('\n') if s.strip()]
    classified = dialogue_classifier.classify_batch(sentences)
    
    dialogue_sentences = [s for s, c in zip(sentences, classified) if c.is_dialogue]
    expected_dialogue_count = gt.get("对话分类", {}).get("总对话数", 0)
    
    print(f"  预期对话数: {expected_dialogue_count}")
    print(f"  检测对话数: {len(dialogue_sentences)}")
    
    dialogue_recall = min(len(dialogue_sentences), expected_dialogue_count) / expected_dialogue_count if expected_dialogue_count else 1.0
    print(f"  召回率: {dialogue_recall*100:.1f}%")
    
    # ========== 2. 引号内容分类测试 ==========
    print("\n【2. 引号内容分类测试】")
    print("-" * 50)
    
    extracted = extract_dialogues_from_text(novel_text)
    print(f"  提取到 {len(extracted)} 个引号内容")
    
    # 分类统计
    type_counts = {QuotationType.DIALOGUE: 0, QuotationType.THOUGHT: 0, 
                   QuotationType.WRITTEN: 0, QuotationType.UNKNOWN: 0}
    
    for d in extracted:
        result = quotation_classifier.classify(novel_text, d['start'], d['end'])
        type_counts[result.type] += 1
    
    print(f"  对话(DIALOGUE): {type_counts[QuotationType.DIALOGUE]}")
    print(f"  心理(THOUGHT): {type_counts[QuotationType.THOUGHT]}")
    print(f"  书面(WRITTEN): {type_counts[QuotationType.WRITTEN]}")
    print(f"  未知(UNKNOWN): {type_counts[QuotationType.UNKNOWN]}")
    
    # ========== 3. 说话人识别测试 ==========
    print("\n【3. 说话人识别测试】")
    print("-" * 50)
    
    gt_dialogues = gt.get("dialogue_speakers", [])
    gt_map = {}
    for item in gt_dialogues:
        text_key = normalize_quotes(item["text"]).strip('"\'"\'')[:30]
        gt_map[text_key] = item["speaker"]
    
    print(f"  Ground Truth 对话数: {len(gt_dialogues)}")
    
    # 第一遍：建立对话历史
    lines = novel_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or not ('\u201c' in line or '"' in line):
            continue
        
        gt_speaker = None
        normalized = normalize_quotes(line)
        for key, speaker in gt_map.items():
            if key in normalized:
                gt_speaker = speaker
                break
        
        if gt_speaker:
            char = char_manager.get_character_by_name(gt_speaker)
            if char:
                speaker_matcher.update_activity(char.id, char.name)
                speaker_matcher.cache_dialogue(char.name, line)
    
    # 第二遍：评估
    correct = 0
    total = 0
    errors = []
    
    for line in lines:
        line = line.strip()
        if not line or not ('\u201c' in line or '"' in line):
            continue
        
        gt_speaker = None
        normalized = normalize_quotes(line)
        for key, speaker in gt_map.items():
            if key in normalized:
                gt_speaker = speaker
                break
        
        if not gt_speaker:
            continue
        
        total += 1
        ctx = DialogueContext(text=line, chapter_id=0, prev_speaker=None)
        result = speaker_matcher.match_speaker(ctx)
        matched = result.character.name if result else None
        
        if matched == gt_speaker:
            correct += 1
        else:
            if len(errors) < 5:  # 只记录前5个错误
                errors.append({
                    'text': line[:50] + '...' if len(line) > 50 else line,
                    'expected': gt_speaker,
                    'got': matched
                })
    
    speaker_accuracy = correct / total * 100 if total > 0 else 100.0
    print(f"  测试对话数: {total}")
    print(f"  正确匹配: {correct}")
    print(f"  准确率: {speaker_accuracy:.1f}%")
    
    if errors:
        print(f"\n  错误示例:")
        for i, err in enumerate(errors, 1):
            print(f"    {i}. 文本: {err['text']}")
            print(f"       期望: {err['expected']}, 实际: {err['got']}")
    
    # ========== 汇总 ==========
    print("\n" + "=" * 70)
    print("【测试汇总】")
    print("=" * 70)
    print(f"  对话分类召回率: {dialogue_recall*100:.1f}%")
    print(f"  引号分类分布: 对话{type_counts[QuotationType.DIALOGUE]}, 心理{type_counts[QuotationType.THOUGHT]}, 书面{type_counts[QuotationType.WRITTEN]}")
    print(f"  说话人识别准确率: {speaker_accuracy:.1f}%")
    
    overall = (dialogue_recall * 100 + speaker_accuracy) / 2
    print(f"\n  综合得分: {overall:.1f}%")
    
    return {
        'dialogue_recall': dialogue_recall * 100,
        'speaker_accuracy': speaker_accuracy,
        'overall': overall
    }


def main():
    test_cases = [
        ('tests/test_novel_urban.txt', 'tests/test_novel_urban_ground_truth.json'),
        ('tests/test_novel_western.txt', 'tests/test_novel_western_ground_truth.json'),
        ('tests/test_novel.txt', 'tests/test_novel_ground_truth.json'),
    ]
    
    results = {}
    for test_file, gt_file in test_cases:
        test_path = Path(__file__).parent.parent.parent / test_file
        gt_path = Path(__file__).parent.parent.parent / gt_file
        
        if test_path.exists() and gt_path.exists():
            name = test_path.stem
            results[name] = run_comprehensive_test(str(test_path), str(gt_path))
            print("\n")
    
    # 最终汇总
    if results:
        print("=" * 70)
        print("【全部测试汇总】")
        print("=" * 70)
        for name, r in results.items():
            print(f"  {name}: 对话召回 {r['dialogue_recall']:.1f}%, 说话人 {r['speaker_accuracy']:.1f}%, 综合 {r['overall']:.1f}%")
        
        avg = sum(r['overall'] for r in results.values()) / len(results)
        print(f"\n  平均综合得分: {avg:.1f}%")


if __name__ == "__main__":
    main()
