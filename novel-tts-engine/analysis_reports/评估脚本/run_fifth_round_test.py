# -*- coding: utf-8 -*-
"""第五轮测试 - L2语义层集成 + SFX/HanLP修复验证"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import NLPBasics, Entity, filter_chapter_title_entities
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from utils.evaluator import evaluate_chapter_splitting, evaluate_dialogue_classification, evaluate_sfx_detection, evaluate_ner, evaluate_speaker_matcher

def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_dir = Path(__file__).parent / f'全面分析测试_{timestamp}'
    report_dir.mkdir(parents=True, exist_ok=True)

    print('=' * 60)
    print('第五轮测试 - L2语义层集成 + SFX/HanLP修复验证')
    print('=' * 60)
    print()

    # Read test data
    test_file = Path(__file__).parent.parent / 'tests' / '测试小说.txt'
    novel_text = test_file.read_text(encoding='utf-8')

    # Chapter splitting
    print('1. 章节划分测试...')
    chapters = split_with_volumes(novel_text)
    with open(report_dir / '章节划分结果.json', 'w', encoding='utf-8') as f:
        json.dump([{'index': ch.index, 'title': ch.title, 'content': ch.content[:50]} for ch in chapters], f, ensure_ascii=False, indent=2)
    chapter_score = evaluate_chapter_splitting(chapters, novel_text)
    print(f'   得分: {chapter_score}')

    # Dialogue classification
    print('2. 对话分类测试...')
    classifier = DialogueClassifier()
    dialogue_score = evaluate_dialogue_classification(classifier, chapters)
    print(f'   得分: {dialogue_score}')

    # SFX detection
    print('3. 拟声词检测测试...')
    detector = SfxDetector()
    sfx_score, _ = evaluate_sfx_detection(detector, chapters)
    print(f'   得分: {sfx_score}')

    # NER
    print('4. NER命名实体识别测试...')
    nlp = NLPBasics()
    ner_score = evaluate_ner(nlp, chapters)
    print(f'   得分: {ner_score}')

    # Speaker matching with L2
    print('5. 说话人匹配测试（含L2语义层）...')
    char_mgr = CharacterManager()
    matcher = SpeakerMatcher(character_manager=char_mgr)
    speaker_score = evaluate_speaker_matcher(matcher, chapters)
    print(f'   得分: {speaker_score}')

    # Summary
    avg_score = (chapter_score + dialogue_score + sfx_score + ner_score + speaker_score) / 5
    print()
    print('=' * 60)
    print(f'第五轮测试结果')
    print(f'章节划分: {chapter_score}')
    print(f'对话分类: {dialogue_score}')
    print(f'拟声词检测: {sfx_score}')
    print(f'NER: {ner_score}')
    print(f'说话人匹配: {speaker_score}')
    print(f'平均得分: {avg_score:.1f}')
    print('=' * 60)

    # Save report
    report_data = {
        'timestamp': timestamp,
        'chapter_splitting': chapter_score,
        'dialogue_classification': dialogue_score,
        'sfx_detection': sfx_score,
        'ner': ner_score,
        'speaker_matching': speaker_score,
        'average': round(avg_score, 1),
    }
    with open(report_dir / '汇总数据.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    with open(report_dir / '第五轮测试报告.txt', 'w', encoding='utf-8') as f:
        f.write(f'第五轮测试报告\n')
        f.write(f'时间: {timestamp}\n\n')
        f.write(f'章节划分: {chapter_score}\n')
        f.write(f'对话分类: {dialogue_score}\n')
        f.write(f'拟声词检测: {sfx_score}\n')
        f.write(f'NER: {ner_score}\n')
        f.write(f'说话人匹配: {speaker_score}\n')
        f.write(f'平均得分: {avg_score:.1f}\n')

if __name__ == '__main__':
    main()
