# -*- coding: utf-8 -*-
"""调试说话人匹配问题"""

import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent))

os.environ['DEBUG_NER'] = '0'

from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher


def test_extract_speaker_hint(matcher: SpeakerMatcher, text: str, expected_hint: str):
    """调试extract_speaker_hint"""
    speaker, hint_type = matcher.extract_speaker_hint(text)
    print(f"文本: {text}")
    print(f"  提取的说话人: {speaker}")
    print(f"  提示类型: {hint_type}")
    print(f"  期望: {expected_hint}")
    print(f"  结果: {'✓' if speaker == expected_hint else '✗'}")
    print()
    return speaker == expected_hint


def main():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        char_manager = CharacterManager(db_path)
        
        characters = [
            ("林轩", "male", {"轩儿", "林少爷", "少爷"}),
            ("小翠", "female", {"翠儿"}),
            ("林天豪", "male", {"老爷", "父亲"}),
            ("王管家", "male", {"王叔"}),
            ("赵虎", "male", {"赵少爷"}),
            ("李铁", "male", set()),
            ("陈风", "male", {"大师兄"}),
        ]
        
        for name, gender, aliases in characters:
            char_manager.add_character(name, gender=gender, aliases=aliases)
        
        matcher = SpeakerMatcher(char_manager)
        
        test_cases = [
            ('少爷，您终于醒了！', '小翠'),
            ('小翠，我睡了多久？', None),
            ('少爷，您昏迷了整整三天！', '小翠'),
            ('轩儿！你终于醒了！', None),
            ('父亲。', None),
            ('轩儿，你感觉如何？', None),
            ('父亲放心，孩儿已经无碍。', None),
        ]
        
        correct = 0
        total = len(test_cases)
        
        for text, expected in test_cases:
            if test_extract_speaker_hint(matcher, text, expected):
                correct += 1
        
        print(f"正确率: {correct}/{total} = {correct/total*100:.1f}%")
        
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except:
                pass


if __name__ == "__main__":
    main()
