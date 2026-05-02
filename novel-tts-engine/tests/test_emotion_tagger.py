# -*- coding: utf-8 -*-
"""EmotionTagger 单元测试"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.emotion_tagger import EmotionTagger, get_emotion_tagger, reset_emotion_tagger


class TestEmotionTagger:
    @pytest.fixture
    def tagger(self):
        return EmotionTagger()

    def test_tag_joy(self, tagger):
        """测试喜悦情绪识别"""
        result = tagger.tag("他哈哈大笑起来，心里十分高兴")
        assert result == "joy"

    def test_tag_anger(self, tagger):
        """测试愤怒情绪识别"""
        result = tagger.tag("他愤怒地咆哮着，气得发火")
        assert result == "anger"

    def test_tag_sadness(self, tagger):
        """测试悲伤情绪识别"""
        result = tagger.tag("他伤心地哭了，泪水不停地流")
        assert result == "sadness"

    def test_tag_neutral_default(self, tagger):
        """测试无情绪关键词返回默认值"""
        result = tagger.tag("他走进了房间，坐在椅子上")
        assert result == "neutral"

    def test_tag_empty_input(self, tagger):
        """测试空输入返回默认情绪"""
        assert tagger.tag("") == "neutral"
        assert tagger.tag(None) == "neutral"

    def test_tag_speaker_optional(self, tagger):
        """测试speaker参数可选"""
        result = tagger.tag("他开心地笑了", speaker="张三")
        assert result == "joy"

    def test_global_singleton(self):
        """测试全局单例模式"""
        reset_emotion_tagger()
        tagger1 = get_emotion_tagger()
        tagger2 = get_emotion_tagger()
        assert tagger1 is tagger2
