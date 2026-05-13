# -*- coding: utf-8 -*-
"""诊断后端分析功能问题的测试脚本"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import re
from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS
from utils.text_utils import split_sentences_smart

# 测试文本：包含中文引号对话的典型网文片段
TEST_TEXT = '''林轩看着苏夜，微微一笑道："你好，我是林轩。"

苏夜抬起头，淡淡回应道："我是苏夜，幸会。"

"今日天气不错，不如一起走走？"林轩提议。

苏夜点了点头："好。"

林轩说道："我们去看看那处秘境吧。"

「你说什么？」苏夜皱起眉头。

『此事不妥。』旁边有人插话。

"快走！"林轩大喊。

"不要过来！"苏夜惊恐地后退。'''

def test_dialogue_patterns():
    """测试 DIALOGUE_PATTERNS 是否能匹配各种引号"""
    print("=" * 60)
    print("测试 DIALOGUE_PATTERNS 引号匹配")
    print("=" * 60)
    
    for i, pattern in enumerate(DIALOGUE_PATTERNS):
        print(f"\nPattern {i}: {pattern.pattern}")
        matches = list(pattern.finditer(TEST_TEXT))
        if matches:
            for m in matches:
                print(f"  匹配: {m.group(0)[:40]}... (位置 {m.start()}-{m.end()})")
        else:
            print("  无匹配")
    
    # 检查是否能检测到引号类型
    print("\n" + "-" * 40)
    print("引号字符分析:")
    quote_chars = ['"', '"', '"', '"', '「', '」', '『', '』']
    for qc in quote_chars:
        count = TEST_TEXT.count(qc)
        if count > 0:
            print(f"  '{qc}' (U+{ord(qc):04X}): {count} 次")

def test_sentence_splitting():
    """测试句子分割"""
    print("\n" + "=" * 60)
    print("测试句子分割")
    print("=" * 60)
    
    sentences = split_sentences_smart(TEST_TEXT)
    print(f"共分割出 {len(sentences)} 个句子:")
    for i, sent in enumerate(sentences):
        print(f"  [{i}] {sent[:60]}{'...' if len(sent) > 60 else ''}")

def test_fragment_extraction():
    """测试片段提取"""
    print("\n" + "=" * 60)
    print("测试片段提取")
    print("=" * 60)
    
    from pipeline.pipeline_runner import PipelineRunner
    
    # 模拟 dialogue_map（来自 speaker_matcher）
    dialogue_map = {
        "你好，我是林轩。": "林轩",
        "我是苏夜，幸会。": "苏夜",
        "今日天气不错，不如一起走走？": "林轩",
        "好。": "苏夜",
        "我们去看看那处秘境吧。": "林轩",
        "你说什么？": "苏夜",
        "此事不妥。": "未知",
        "快走！": "林轩",
        "不要过来！": "苏夜",
    }
    
    sentences = split_sentences_smart(TEST_TEXT)
    for i, sent in enumerate(sentences):
        fragments = PipelineRunner._extract_fragments(sent, dialogue_map)
        print(f"句子[{i}]: {sent[:40]}...")
        print(f"  fragments 数量: {len(fragments)}")
        for j, frag in enumerate(fragments):
            print(f"    [{j}] type={frag.type}, speaker={frag.speaker}, text={frag.text[:30]}...")

def test_speaker_matcher():
    """测试 speaker_matcher 的对话提取"""
    print("\n" + "=" * 60)
    print("测试 SpeakerMatcher 对话提取")
    print("=" * 60)
    
    from pipeline.speaker_matcher import SpeakerMatcher, get_speaker_matcher
    
    matcher = get_speaker_matcher()
    results = matcher.analyze_dialogue(TEST_TEXT)
    
    print(f"检测到 {len(results)} 段对话:")
    for i, (dialogue_text, speaker) in enumerate(results):
        speaker_name = speaker.name if speaker else "(None)"
        print(f"  [{i}] 对话: '{dialogue_text}' -> 说话人: {speaker_name}")

if __name__ == "__main__":
    test_dialogue_patterns()
    test_sentence_splitting()
    test_fragment_extraction()
    test_speaker_matcher()
