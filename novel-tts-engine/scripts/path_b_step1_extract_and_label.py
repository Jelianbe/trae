#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路径B-第一步：从《斗破苍穹》抽取150句对话样本并初标

输出：
- data/raw_sentences_150.json: 原始句子（含上下文）
- data/raw_sentences_150_labeled.json: 规则标注结果
"""

import sys
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emotion_tagger import get_emotion_tagger


def extract_dialogues_from_novel(novel_path: str, max_sentences: int = 150) -> list:
    """
    从小说中抽取对话样本
    
    策略：
    1. 按段落分割
    2. 提取包含引号的段落
    3. 每段提取1句对话（带前后各20字上下文）
    4. 尽量覆盖有/无引导词、有/无情绪词、问句/陈述句
    """
    with open(novel_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按段落分割
    paragraphs = content.split('\n')
    
    sentences = []
    sentence_id = 0
    
    for i, para in enumerate(paragraphs):
        if len(sentences) >= max_sentences:
            break
        
        # 查找引号内容（中文弯引号）
        quotes = re.findall(r'\u201c(.*?)\u201d', para)
        
        for quote in quotes:
            if len(quote) < 5 or len(quote) > 100:
                continue
            
            sentence_id += 1
            
            # 提取上下文（中文弯引号格式）
            quote_pos = para.find('\u201c' + quote + '\u201d')
            if quote_pos == -1:
                continue
            quote_pos += 1  # move past opening quote
            
            context_before = para[max(0, quote_pos - 20):quote_pos].strip()
            context_after = para[quote_pos + len(quote):quote_pos + len(quote) + 20].strip()
            
            # 获取前后段落上下文（各20字）
            before_para = paragraphs[i-1][-20:] if i > 0 else ""
            after_para = paragraphs[i+1][:20] if i < len(paragraphs) - 1 else ""
            
            sentences.append({
                "id": sentence_id,
                "text": quote,
                "full_sentence": para,
                "context_before": before_para + context_before,
                "context_after": context_after + after_para,
                "has_guide_word": bool(re.search(r'道|说|问|喊|笑|叹', context_before)),
                "is_question": '？' in quote or '?' in quote,
            })
            
            if len(sentences) >= max_sentences:
                break
    
    return sentences


def label_sentences(sentences: list) -> list:
    """用当前规则标注器初标"""
    tagger = get_emotion_tagger()
    
    for s in sentences:
        # 组合上下文 + 对话作为输入
        full_text = s["context_before"][-30:] + s["text"] + s["context_after"][:30]
        
        result = tagger.tag_with_score(full_text)
        
        s["predicted_emotion"] = result.emotion
        s["predicted_intensity"] = result.intensity
        s["predicted_confidence"] = result.confidence
        s["predicted_reason"] = result.reason
    
    return sentences


def main():
    novel_path = PROJECT_ROOT / "《斗破苍穹》【爱上阅读_www.isyd.net】.txt"
    output_raw = PROJECT_ROOT / "data" / "raw_sentences_150.json"
    output_labeled = PROJECT_ROOT / "data" / "raw_sentences_150_labeled.json"
    
    print(f"正在从小说中抽取对话样本...")
    sentences = extract_dialogues_from_novel(str(novel_path), max_sentences=150)
    print(f"抽取到 {len(sentences)} 句对话")
    
    # 保存原始数据
    with open(output_raw, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)
    print(f"原始数据已保存到: {output_raw}")
    
    # 规则标注
    print(f"正在用规则标注器初标...")
    labeled = label_sentences(sentences)
    
    # 保存标注结果
    with open(output_labeled, 'w', encoding='utf-8') as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)
    print(f"标注结果已保存到: {output_labeled}")
    
    # 统计分布
    emotion_dist = {}
    for s in labeled:
        em = s["predicted_emotion"]
        emotion_dist[em] = emotion_dist.get(em, 0) + 1
    
    print(f"\n情绪分布:")
    for em, count in sorted(emotion_dist.items()):
        print(f"  {em}: {count}")


if __name__ == '__main__':
    main()
