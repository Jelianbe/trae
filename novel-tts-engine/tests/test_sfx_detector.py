import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.sfx_detector import (
    SfxDetector, SfxWord,
    detect_sfx, is_sfx_word, get_sfx_words
)


class TestSfxDetector:
    @pytest.fixture
    def detector(self):
        return SfxDetector()

    def test_detect_water_sfx(self, detector):
        text = "哗啦，水花四溅。"
        results = detector.detect(text)
        
        assert len(results) >= 1
        assert any(r.text == '哗啦' for r in results)

    def test_detect_explosion_sfx(self, detector):
        text = "轰隆，门被炸开了。"
        results = detector.detect(text)
        
        assert len(results) >= 1
        assert any(r.text in ['轰隆', '砰', '啪'] for r in results)

    def test_detect_knock_sfx(self, detector):
        text = "咚咚咚，有人敲门。"
        results = detector.detect(text)
        
        assert len(results) >= 1

    def test_detect_animal_sfx(self, detector):
        text = "小猫喵喵叫着，小狗汪汪回应。"
        results = detector.detect(text)
        
        assert len(results) >= 1
        assert any(r.text in ['喵', '喵喵', '汪', '汪汪'] for r in results)

    def test_detect_wind_sfx(self, detector):
        text = "呼呼的风声从窗外传来。"
        results = detector.detect(text)
        
        assert len(results) >= 1

    def test_detect_laugh_sfx(self, detector):
        text = "他哈哈大笑起来。"
        results = detector.detect(text)
        
        assert len(results) >= 1
        assert any(r.text in ['哈哈', '呵呵', '嘿嘿'] for r in results)

    def test_detect_multiple_sfx(self, detector):
        text = "哗啦啦下起了雨，轰隆隆的雷声响起。"
        results = detector.detect(text)
        
        assert len(results) >= 2

    def test_detect_no_sfx(self, detector):
        text = "今天天气很好，阳光明媚。"
        results = detector.detect(text)
        
        assert len(results) == 0

    def test_is_sfx_word_true(self, detector):
        assert detector.is_sfx('哗啦') is True
        assert detector.is_sfx('轰隆') is True
        assert detector.is_sfx('喵') is True

    def test_is_sfx_word_false(self, detector):
        assert detector.is_sfx('天气') is False
        assert detector.is_sfx('阳光') is False

    def test_add_word(self, detector):
        detector.add_word('测试拟声词')
        assert detector.is_sfx('测试拟声词') is True

    def test_remove_word(self, detector):
        detector.add_word('临时词')
        result = detector.remove_word('临时词')
        assert result is True
        assert detector.is_sfx('临时词') is False

    def test_get_sfx_type(self, detector):
        sfx_type = detector._get_sfx_type('哗啦')
        assert sfx_type == 'water'
        
        sfx_type = detector._get_sfx_type('轰隆')
        assert sfx_type == 'explosion'

    def test_position_correct(self, detector):
        text = "开始哗啦结束"
        results = detector.detect(text)
        
        assert len(results) >= 1
        assert results[0].position == 2

    def test_deduplicate(self, detector):
        text = "哗啦哗啦"
        results = detector.detect(text)
        
        positions = [r.position for r in results]
        assert len(positions) == len(set(positions))


class TestSfxWordDataclass:
    def test_creation(self):
        sfx = SfxWord(
            text="哗啦",
            position=10,
            sfx_type="water"
        )
        
        assert sfx.text == "哗啦"
        assert sfx.position == 10
        assert sfx.sfx_type == "water"


class TestConvenienceFunctions:
    def test_detect_sfx_function(self):
        text = "轰隆一声。"
        results = detect_sfx(text)
        
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_is_sfx_word_function(self):
        assert is_sfx_word('哗啦') is True
        assert is_sfx_word('普通词') is False

    def test_get_sfx_words_function(self):
        words = get_sfx_words()
        
        assert isinstance(words, list)
        assert len(words) > 0
        assert '哗啦' in words


class TestAccuracy:
    @pytest.fixture
    def detector(self):
        return SfxDetector()

    def test_accuracy_common_sfx(self, detector):
        test_cases = [
            ('哗啦', True),
            ('轰隆', True),
            ('咚咚', True),
            ('喵', True),
            ('汪', True),
            ('哈哈', True),
            ('天气', False),
            ('阳光', False),
            ('美丽', False),
            ('快乐', False),
        ]
        
        correct = 0
        for word, expected in test_cases:
            result = detector.is_sfx(word)
            if result == expected:
                correct += 1
        
        accuracy = correct / len(test_cases) * 100
        assert accuracy >= 90


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
