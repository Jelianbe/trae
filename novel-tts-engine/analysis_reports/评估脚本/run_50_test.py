# -*- coding: utf-8 -*-
"""
50条测试文本综合评估脚本（修正版）
测试：
1. 对话分类 - 判断是否是对话（仅测试有引号的文本）
2. 情绪识别 - 识别对话的情绪类别
3. 角色识别 - 识别说话人（需要上下文）
"""
import sys
import os
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ['DEBUG_NER'] = '0'

from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.emotion_tagger import EmotionTagger
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext


def load_test_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_emotion_test(test_file):
    """运行情绪标注测试"""
    print("=" * 70)
    print(f"情绪标注能力测试: {Path(test_file).stem}")
    print("=" * 70)
    
    data = load_test_data(test_file)
    
    dialogue_classifier = DialogueClassifier()
    emotion_tagger = EmotionTagger()
    
    results = {
        'dialogue_correct': 0,
        'dialogue_total': 0,
        'emotion_correct': 0,
        'total': 0,
        'errors': []
    }
    
    for item in data:
        text = item.get('text', '')
        expected_emotion = item.get('emotion_label', 'neutral')
        
        # 检查是否有引号
        has_quotes = any(q in text for q in ['「', '」', '"', '"', "'", '『', '』'])
        
        # 1. 对话分类测试（仅对有引号的文本）
        if has_quotes:
            classified = dialogue_classifier.classify(text)
            is_dialogue = classified.is_dialogue
            results['dialogue_total'] += 1
            if is_dialogue:
                results['dialogue_correct'] += 1
        
        # 2. 情绪识别测试
        predicted_emotion = emotion_tagger.tag(text) or 'neutral'
        results['total'] += 1
        
        if predicted_emotion == expected_emotion:
            results['emotion_correct'] += 1
        else:
            if len(results['errors']) < 10:
                results['errors'].append({
                    'id': item.get('id', ''),
                    'text': text[:40],
                    'expected': expected_emotion,
                    'predicted': predicted_emotion
                })
    
    # 输出结果
    dialogue_acc = results['dialogue_correct'] / results['dialogue_total'] * 100 if results['dialogue_total'] > 0 else 100.0
    emotion_acc = results['emotion_correct'] / results['total'] * 100
    
    if results['dialogue_total'] > 0:
        print(f"\n【对话分类】(仅测试有引号的文本)")
        print(f"  正确: {results['dialogue_correct']}/{results['dialogue_total']}")
        print(f"  准确率: {dialogue_acc:.1f}%")
    else:
        print(f"\n【对话分类】跳过（测试数据无引号）")
    
    print(f"\n【情绪识别】")
    print(f"  正确: {results['emotion_correct']}/{results['total']}")
    print(f"  准确率: {emotion_acc:.1f}%")
    
    if results['errors']:
        print(f"\n  错误示例 (前5个):")
        for err in results['errors'][:5]:
            print(f"    [{err['id']}] {err['text']}")
            print(f"      期望: {err['expected']}, 预测: {err['predicted']}")
    
    return {
        'dialogue_accuracy': dialogue_acc,
        'emotion_accuracy': emotion_acc,
        'total': results['total']
    }


def run_role_test(test_file):
    """运行角色识别测试"""
    print("\n" + "=" * 70)
    print(f"角色识别能力测试: {Path(test_file).stem}")
    print("=" * 70)
    
    data = load_test_data(test_file)
    
    char_manager = CharacterManager()
    speaker_matcher = SpeakerMatcher(character_manager=char_manager)
    
    results = {
        'correct': 0,
        'total': 0,
        'not_found': 0,
        'errors': []
    }
    
    for item in data:
        text = item.get('text', '')
        context_before = item.get('context_before', '')
        context_after = item.get('context_after', '')
        expected_speaker = item.get('speaker', '')
        mentioned = item.get('mentioned', [])
        
        # 注册上下文中提到的角色
        all_names = []
        if expected_speaker and expected_speaker not in ['未知下属', '那人', '路人', '三人', '众人', '黑衣人']:
            all_names.append(expected_speaker)
        all_names.extend(mentioned)
        
        for name in all_names:
            if name and not char_manager.get_character_by_name(name):
                char_manager.add_character(name, gender="unknown")
        
        # 构建对话上下文
        ctx = DialogueContext(text=text, chapter_id=0, prev_speaker=None)
        result = speaker_matcher.match_speaker(ctx)
        predicted = result.character.name if result else None
        
        results['total'] += 1
        
        # 判断是否正确
        is_unknown = expected_speaker in ['未知下属', '那人', '路人', '三人', '众人', '黑衣人', '未知角色']
        
        if predicted == expected_speaker:
            results['correct'] += 1
        elif is_unknown:
            results['not_found'] += 1
        else:
            if len(results['errors']) < 10:
                results['errors'].append({
                    'id': item.get('id', ''),
                    'text': text[:40],
                    'expected': expected_speaker,
                    'predicted': predicted,
                    'context_before': context_before[:30]
                })
    
    # 输出结果
    valid_total = results['total'] - results['not_found']
    accuracy = results['correct'] / valid_total * 100 if valid_total > 0 else 0
    
    print(f"\n【角色识别】")
    print(f"  正确: {results['correct']}/{valid_total} (排除未知角色)")
    print(f"  准确率: {accuracy:.1f}%")
    print(f"  未知角色: {results['not_found']} (不计入错误)")
    
    if results['errors']:
        print(f"\n  错误示例 (前5个):")
        for err in results['errors'][:5]:
            print(f"    [{err['id']}] {err['text']}")
            print(f"      上下文: {err['context_before']}")
            print(f"      期望: {err['expected']}, 预测: {err['predicted']}")
    
    return {
        'accuracy': accuracy,
        'total': results['total'],
        'not_found': results['not_found']
    }


def main():
    test_files = [
        ('tests/emotion_gt_50.json', 'emotion'),
        ('tests/role_emotion_gt_50.json', 'role'),
    ]
    
    all_results = {}
    
    for test_file, test_type in test_files:
        test_path = Path(__file__).parent.parent.parent / test_file
        
        if not test_path.exists():
            print(f"文件不存在: {test_path}")
            continue
        
        if test_type == 'emotion':
            all_results['emotion'] = run_emotion_test(str(test_path))
        elif test_type == 'role':
            all_results['role'] = run_role_test(str(test_path))
    
    # 汇总
    print("\n" + "=" * 70)
    print("【测试汇总】")
    print("=" * 70)
    
    if 'emotion' in all_results:
        r = all_results['emotion']
        print(f"  emotion_gt_50: 情绪识别 {r['emotion_accuracy']:.1f}%")
    
    if 'role' in all_results:
        r = all_results['role']
        print(f"  role_emotion_gt_50: 角色识别 {r['accuracy']:.1f}%")
    
    # 计算综合得分
    if 'emotion' in all_results and 'role' in all_results:
        overall = (
            all_results['emotion']['emotion_accuracy'] + 
            all_results['role']['accuracy']
        ) / 2
        print(f"\n  综合得分: {overall:.1f}%")


if __name__ == "__main__":
    main()
