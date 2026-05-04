# -*- coding: utf-8 -*-
"""完整 Pipeline 评估脚本（角色识别 + 情绪标注）- 详细版

输出每一条测试结果，便于分析
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pipeline_runner import PipelineRunner


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_speaker(speaker: str) -> str:
    if not speaker:
        return ""
    speaker = speaker.replace("未知", "").strip()
    if speaker.endswith("角色"):
        speaker = speaker[:-2]
    return speaker


def find_target_sentence(sentences, target_text: str):
    target_text = target_text.strip()
    for s in sentences:
        if s.text.strip() == target_text:
            return s
        if target_text in s.text:
            return s
    return None


def evaluate_pipeline(gt_data: list, runner: PipelineRunner):
    results = []
    
    for item in gt_data:
        item_id = item['id']
        text = item['text']
        context_before = item.get('context_before', '')
        context_after = item.get('context_after', '')
        style = item['style']
        
        gt_speaker = item['speaker']
        gt_emotion = item['emotion_label']
        role_challenge = item.get('role_challenge', '')
        emotion_challenge = item.get('emotion_challenge', '')
        
        full_text = f"{context_before}\n{text}\n{context_after}"
        
        try:
            chapter_results = runner.analyze_chapters(full_text, force=True)
            all_sentences = []
            for cr in chapter_results:
                all_sentences.extend(cr.sentences)
            
            target_sentence = find_target_sentence(all_sentences, text)
            
            if target_sentence:
                pred_speaker = target_sentence.speaker
                pred_emotion = target_sentence.emotion
            else:
                pred_speaker = ""
                pred_emotion = "neutral"
            
        except Exception as e:
            pred_speaker = ""
            pred_emotion = "neutral"
        
        gt_speaker_norm = normalize_speaker(gt_speaker)
        pred_speaker_norm = normalize_speaker(pred_speaker)
        
        speaker_ok = (gt_speaker_norm == pred_speaker_norm) or (not gt_speaker_norm and not pred_speaker_norm)
        emotion_ok = (gt_emotion == pred_emotion)
        
        results.append({
            'id': item_id,
            'text': text,
            'style': style,
            'gt_speaker': gt_speaker,
            'pred_speaker': pred_speaker,
            'speaker_ok': speaker_ok,
            'gt_emotion': gt_emotion,
            'pred_emotion': pred_emotion,
            'emotion_ok': emotion_ok,
            'role_challenge': role_challenge[:60] + '...' if len(role_challenge) > 60 else role_challenge,
            'emotion_challenge': emotion_challenge[:60] + '...' if len(emotion_challenge) > 60 else emotion_challenge,
        })
    
    return results


def main():
    gt_path = Path(__file__).parent.parent / 'tests' / 'role_emotion_gt_50.json'
    gt_data = load_gt(gt_path)
    
    runner = PipelineRunner()
    results = evaluate_pipeline(gt_data, runner)
    
    # 输出 JSON 格式结果
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
