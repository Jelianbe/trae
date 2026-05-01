# -*- coding: utf-8 -*-
"""
泛化性测试脚本 - 对指定测试小说进行全面的分析测试
支持任意测试小说文件，验证模型的泛化能力
"""
import sys
from pathlib import Path
from datetime import datetime
import json
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['DEBUG_NER'] = '0'

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import NLPBasics, Entity, filter_chapter_title_entities
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext


def evaluate_chapter_splitting(structure, novel_text):
    chapters = structure.chapters
    expected_count = len(re.findall(r'第[一二三四五六七八九十\d]+[章节回卷]', novel_text))
    if expected_count == 0:
        return 0.0
    actual_count = len(chapters)
    diff = abs(actual_count - expected_count)
    score = max(0, 100 * (1 - diff / max(expected_count, 1)))
    return round(score, 1)


def evaluate_dialogue_classification(classifier, chapters):
    correct = 0
    total = 0
    for ch in chapters:
        for sent in ch.content.split('\n'):
            sent = sent.strip()
            if not sent or len(sent) < 5:
                continue
            is_dialogue = sent.startswith('"') or sent.endswith('"')
            result = classifier.classify(sent)
            predicted_is_dialogue = (result.sentence_type == 'dialogue')
            if is_dialogue == predicted_is_dialogue:
                correct += 1
            total += 1
    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)


def evaluate_sfx_detection(detector, chapters):
    correct = 0
    total = 0
    for ch in chapters:
        for sent in ch.content.split('\n'):
            sent = sent.strip()
            if not sent:
                continue
            total += 1
            expected_sfx = re.findall(r'[^\u4e00-\u9fa5a-zA-Z]*[A-Za-z\u4e00-\u9fa5]{2,}(?=！|!|。|，|\n|$)', sent)
            detected = detector.detect(sent)
            if detected:
                correct += 1
            else:
                has_sfx_in_dict = any(w in detector.sfx_words for w in expected_sfx)
                if not has_sfx_in_dict:
                    correct += 1
    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)


def evaluate_ner(nlp, chapters):
    all_entities = []
    for ch in chapters:
        result = nlp.analyze(ch.content)
        filtered = filter_chapter_title_entities(result.entities, chapters)
        all_entities.extend(filtered)
    
    persons = [e for e in all_entities if e.type == 'PER']
    locations = [e for e in all_entities if e.type == 'LOC']
    organizations = [e for e in all_entities if e.type == 'ORG']
    
    correct = 0
    total = 0
    expected_pattern = r'[\u4e00-\u9fa5]{2,4}'
    for ch in chapters:
        for sent in ch.content.split('\n'):
            sent = sent.strip()
            if not sent:
                continue
            expected = re.findall(expected_pattern, sent)
            for name in expected:
                if len(name) < 2:
                    continue
                if name in {'这是', '这是', '什么', '哪里', '怎么', '如此', '这个', '那个', '一起', '一定', '知道', '感觉', '心中', '身上', '手中', '面前', '身后', '面前', '周围', '远方', '北方', '南方', '东方', '西方'}:
                    continue
                total += 1
                if any(name == e.text or e.text in name or name in e.text for e in all_entities):
                    correct += 1
    
    if total == 0:
        return 100.0
    recall = correct / total if total > 0 else 0
    all_detected = len(all_entities)
    precision = correct / all_detected if all_detected > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return round(f1 * 100, 1)


def evaluate_speaker_matcher(matcher, chapters):
    correct = 0
    total = 0
    prev_speaker = None
    char_mgr = matcher.char_manager
    
    for ch in chapters:
        for i, sent in enumerate(ch.content.split('\n')):
            sent = sent.strip()
            if not sent or len(sent) < 5:
                continue
            is_dialogue = sent.startswith('"') or sent.endswith('"')
            if not is_dialogue:
                continue
            
            match = re.search(r'["\']([^"\']{2,})["\']\s*([^"，。！？\n]{1,10}?)(?:[说道|问道|答道|喊道|笑道|叫道|说|道|问|答|喊|笑|叫])', sent)
            if match:
                dialogue_text = match.group(1).strip()
                speaker_hint = match.group(2).strip()
                
                skip_keywords = ['脸色', '眼中', '心中', '暗道', '心想', '声音', '脚步', '身影', '大门', '房门']
                if any(kw in speaker_hint for kw in skip_keywords):
                    continue
                
                total += 1
                ctx = DialogueContext(
                    text=sent,
                    speaker_hint=speaker_hint,
                    chapter_id=ch.index
                )
                result = matcher.match_speaker(ctx)
                if result and result.character:
                    if speaker_hint in result.character.name or result.character.name in speaker_hint:
                        correct += 1
                        prev_speaker = result.character.name
                    elif any(speaker_hint in alias or alias in speaker_hint for alias in result.character.aliases):
                        correct += 1
                        prev_speaker = result.character.name
                    else:
                        prev_speaker = None
                else:
                    prev_speaker = None
    
    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)


def main():
    if len(sys.argv) < 2:
        print("用法: python 泛化性测试脚本.py <测试小说文件路径>")
        sys.exit(1)
    
    test_file_path = Path(sys.argv[1])
    if not test_file_path.exists():
        print(f"错误: 文件 {test_file_path} 不存在")
        sys.exit(1)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    novel_name = test_file_path.stem
    report_dir = Path(__file__).parent / f'泛化性测试_{novel_name}_{timestamp}'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    print('=' * 60)
    print(f'泛化性测试 - {novel_name}')
    print('=' * 60)
    print()
    
    novel_text = test_file_path.read_text(encoding='utf-8')
    print(f'文本长度: {len(novel_text)} 字符')
    print(f'文本行数: {len(novel_text.splitlines())} 行')
    print()
    
    # 1. 章节划分
    print('1. 章节划分测试...')
    structure = split_with_volumes(novel_text)
    chapters = structure.chapters
    chapter_score = evaluate_chapter_splitting(structure, novel_text)
    print(f'   检测到 {len(chapters)} 个章节')
    print(f'   得分: {chapter_score}')
    
    with open(report_dir / '章节划分结果.json', 'w', encoding='utf-8') as f:
        json.dump([{'index': ch.index, 'title': ch.title, 'content_len': len(ch.content)} for ch in chapters], f, ensure_ascii=False, indent=2)
    
    # 2. 对话分类
    print('2. 对话分类测试...')
    classifier = DialogueClassifier()
    dialogue_score = evaluate_dialogue_classification(classifier, chapters)
    print(f'   得分: {dialogue_score}')
    
    # 3. 拟声词检测
    print('3. 拟声词检测测试...')
    detector = SfxDetector()
    sfx_score = evaluate_sfx_detection(detector, chapters)
    print(f'   得分: {sfx_score}')
    
    # 4. NER
    print('4. NER命名实体识别测试...')
    nlp = NLPBasics()
    ner_score = evaluate_ner(nlp, chapters)
    print(f'   得分: {ner_score}')
    
    # 5. 说话人匹配
    print('5. 说话人匹配测试...')
    char_mgr = CharacterManager()
    matcher = SpeakerMatcher(character_manager=char_mgr)
    speaker_score = evaluate_speaker_matcher(matcher, chapters)
    print(f'   得分: {speaker_score}')
    
    # 汇总
    avg_score = (chapter_score + dialogue_score + sfx_score + ner_score + speaker_score) / 5
    
    print()
    print('=' * 60)
    print(f'泛化性测试结果 - {novel_name}')
    print(f'章节划分: {chapter_score}')
    print(f'对话分类: {dialogue_score}')
    print(f'拟声词检测: {sfx_score}')
    print(f'NER: {ner_score}')
    print(f'说话人匹配: {speaker_score}')
    print(f'平均得分: {avg_score:.1f}')
    print('=' * 60)
    
    # 保存报告
    report_data = {
        'timestamp': timestamp,
        'novel': novel_name,
        'text_length': len(novel_text),
        'line_count': len(novel_text.splitlines()),
        'chapter_count': len(chapters),
        'chapter_splitting': chapter_score,
        'dialogue_classification': dialogue_score,
        'sfx_detection': sfx_score,
        'ner': ner_score,
        'speaker_matching': speaker_score,
        'average': round(avg_score, 1),
    }
    with open(report_dir / '汇总数据.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    with open(report_dir / '泛化性测试报告.txt', 'w', encoding='utf-8') as f:
        f.write(f'泛化性测试报告 - {novel_name}\n')
        f.write(f'时间: {timestamp}\n\n')
        f.write(f'文本长度: {len(novel_text)} 字符\n')
        f.write(f'文本行数: {len(novel_text.splitlines())} 行\n')
        f.write(f'章节数: {len(chapters)}\n\n')
        f.write(f'章节划分: {chapter_score}\n')
        f.write(f'对话分类: {dialogue_score}\n')
        f.write(f'拟声词检测: {sfx_score}\n')
        f.write(f'NER: {ner_score}\n')
        f.write(f'说话人匹配: {speaker_score}\n')
        f.write(f'平均得分: {avg_score:.1f}\n')


if __name__ == '__main__':
    main()
