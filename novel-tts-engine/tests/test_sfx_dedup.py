"""
SFX 嵌套去重算法的单元测试。

验证 _deduplicate() 方法正确处理嵌套匹配，如：
- "哗啦啦" 包含 "哗啦" 包含 "哗"
- "轰隆隆隆" 包含 "轰隆"
- 重叠但不包含的情况应保留

去重算法使用基于包含关系的去重策略：完全在更长匹配内部的短匹配应被移除。
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.sfx_detector import SfxDetector, SfxWord


class TestNestedDeduplication:
    """测试嵌套匹配的去重逻辑"""

    @pytest.fixture
    def detector(self):
        return SfxDetector()

    def test_huala_nested_dedup(self, detector):
        """
        "哗啦啦" 在位置 0 时，不应同时产生 "哗啦" 在位置 0 或 "哗" 在位置 0。
        只有最长匹配 "哗啦啦" 应被保留。
        """
        text = "哗啦啦！"
        results = detector.detect(text)
        
        pos_0_words = [r.text for r in results if r.position == 0]
        
        assert "哗啦啦" in pos_0_words, "应保留最长匹配 '哗啦啦'"
        assert "哗啦" not in pos_0_words, "不应保留嵌套的 '哗啦'"
        assert "哗" not in pos_0_words, "不应保留嵌套的 '哗'"

    def test_honglonglong_nested_dedup(self, detector):
        """
        "轰隆隆隆" 不应产生重复的 "轰隆"。
        最长匹配应被保留，较短的嵌套匹配应被移除。
        """
        text = "轰隆隆隆！"
        results = detector.detect(text)
        
        pos_0_words = [r.text for r in results if r.position == 0]
        
        assert "轰隆隆隆" in pos_0_words, "应保留最长匹配 '轰隆隆隆'"
        assert "轰隆" not in pos_0_words, "不应保留嵌套的 '轰隆'"
        assert "轰隆隆" not in pos_0_words, "不应保留嵌套的 '轰隆隆'"

    def test_overlapping_not_contained_both_kept(self, detector):
        """
        重叠但不完全包含的匹配应都被保留。
        例如：文本中有两个分离的 "咚咚" 匹配。
        """
        text = "咚咚！间隔文字咚咚！"
        results = detector.detect(text)
        
        dong_results = [r for r in results if "咚" in r.text and r.position in [0, 6, 7]]
        positions = [r.position for r in dong_results]
        
        # 应该检测到两个位置的咚咚
        assert len(dong_results) >= 2, f"两个 '咚咚' 都应被检测到，实际只有 {len(dong_results)} 个"

    def test_same_word_different_positions(self, detector):
        """
        同一词语在不同位置的出现应全部保留。
        """
        text = "咚咚！咚咚！咚咚！"
        results = detector.detect(text)
        
        dong_results = [r for r in results if "咚" in r.text and r.text.count("咚") >= 2]
        positions = [r.position for r in dong_results]
        
        # 应该有多个不同位置的匹配
        assert len(positions) >= 3, f"三个 '咚咚' 都应被检测到，实际只有 {len(positions)} 个"

    def test_dingdingdangdang_no_separate_matches(self, detector):
        """
        "叮叮当当" 不应产生独立的 "叮叮" 和 "当当" 匹配（如果位置重叠）。
        """
        text = "叮叮当当！"
        results = detector.detect(text)
        
        pos_0_words = [r.text for r in results if r.position == 0]
        pos_2_words = [r.text for r in results if r.position == 2]
        
        # 在位置 0，应保留最长匹配 "叮叮当当"
        if "叮叮当当" in pos_0_words:
            assert "叮叮" not in pos_0_words, "不应在位置 0 同时保留 '叮叮'"
            assert "当当" not in pos_2_words, "不应在位置 2 保留被包含的 '当当'"

    def test_honglong_in_middle(self, detector):
        """
        测试 "轰隆" 在文本中间位置的去重。
        """
        text = "突然轰隆一声巨响"
        results = detector.detect(text)
        
        pos_matches = [r.text for r in results if r.position == 2]
        
        assert "轰隆" in pos_matches, "'轰隆' 应在位置 2 被检测到"


class TestEdgeCases:
    """测试去重算法的边界情况"""

    @pytest.fixture
    def detector(self):
        return SfxDetector()

    def test_empty_input(self, detector):
        """空列表应返回空列表"""
        results = detector._deduplicate([])
        assert results == []

    def test_single_match(self, detector):
        """单个匹配应保持不变"""
        matches = [SfxWord(text="哗啦", position=0, sfx_type="water")]
        results = detector._deduplicate(matches)
        
        assert len(results) == 1
        assert results[0].text == "哗啦"

    def test_identical_matches_same_position(self, detector):
        """
        相同文本、相同位置的重复匹配应被去重。
        修复前：由于 text 相同，containment 检查不会触发，导致重复。
        修复后：增加显式检查，确保完全相同的匹配只保留一个。
        """
        matches = [
            SfxWord(text="哗啦", position=0, sfx_type="water"),
            SfxWord(text="哗啦", position=0, sfx_type="water"),
        ]
        results = detector._deduplicate(matches)
        
        # 修复后应该只有一个匹配
        assert len(results) == 1, f"应去重为 1 个匹配，实际有 {len(results)} 个"
        assert results[0].text == "哗啦"

    def test_three_level_nesting(self, detector):
        """
        测试三级嵌套："嗡嗡嗡嗡" 包含 "嗡嗡嗡" 包含 "嗡嗡"
        """
        matches = [
            SfxWord(text="嗡嗡嗡", position=0, sfx_type="other"),
            SfxWord(text="嗡嗡", position=0, sfx_type="other"),
            SfxWord(text="嗡嗡嗡嗡", position=0, sfx_type="other"),
        ]
        results = detector._deduplicate(matches)
        
        texts = [r.text for r in results if r.position == 0]
        assert "嗡嗡嗡嗡" in texts, "应保留最长的 '嗡嗡嗡嗡'"
        assert "嗡嗡嗡" not in texts, "不应保留 '嗡嗡嗡'"
        assert "嗡嗡" not in texts, "不应保留 '嗡嗡'"

    def test_overlapping_different_starts(self, detector):
        """
        测试重叠但起始位置不同的情况。
        例如："嗡嗡" 在位置 1，而 "嗡嗡嗡嗡" 在位置 0。
        由于 [1,3) 完全在 [0,4) 内，应被移除。
        """
        matches = [
            SfxWord(text="嗡嗡嗡嗡", position=0, sfx_type="other"),
            SfxWord(text="嗡嗡", position=1, sfx_type="other"),
            SfxWord(text="嗡嗡", position=2, sfx_type="other"),
        ]
        results = detector._deduplicate(matches)
        
        pos_1_words = [r.text for r in results if r.position == 1]
        pos_2_words = [r.text for r in results if r.position == 2]
        
        assert "嗡嗡" not in pos_1_words, "位置 1 的 '嗡嗡' 被 [0,4) 包含，应移除"
        assert "嗡嗡" not in pos_2_words, "位置 2 的 '嗡嗡' 被 [0,4) 包含，应移除"

    def test_non_overlapping_adjacent(self, detector):
        """
        测试相邻但不重叠的匹配应都被保留。
        例如："咚咚" 在位置 0 和 "咚咚" 在位置 2。
        [0,2) 和 [2,4) 相邻但不重叠。
        """
        matches = [
            SfxWord(text="咚咚", position=0, sfx_type="knock"),
            SfxWord(text="咚咚", position=2, sfx_type="knock"),
        ]
        results = detector._deduplicate(matches)
        
        assert len(results) == 2, "相邻但不重叠的匹配应都保留"


class TestRealWorldScenarios:
    """测试真实场景下的去重效果"""

    @pytest.fixture
    def detector(self):
        return SfxDetector()

    def test_end_to_end_dedup(self, detector):
        """
        端到端测试：输入包含多个 SFX 的文本，验证嵌套去重是否正常工作。
        输入："哗啦啦！轰隆一声，咚咚咚的敲门声"
        预期：["哗啦啦", "轰隆", "咚咚咚"] - 无重复
        """
        text = "哗啦啦！轰隆一声，咚咚咚的敲门声"
        results = detector.detect(text)
        
        texts = [r.text for r in results]
        
        assert "哗啦啦" in texts, "应检测到 '哗啦啦'"
        assert "轰隆" in texts, "应检测到 '轰隆'"
        assert "咚咚咚" in texts, "应检测到 '咚咚咚'"
        
        # 验证没有产生嵌套重复
        pos_0_words = [r.text for r in results if r.position == 0]
        assert "哗啦" not in pos_0_words, "位置 0 不应有 '哗啦'"
        assert "哗" not in pos_0_words, "位置 0 不应有 '哗'"
        
        pos_4_words = [r.text for r in results if r.position == 4]
        assert "轰" not in pos_4_words, "位置 4 不应有 '轰'"
        
        pos_9_words = [r.text for r in results if r.position == 9]
        assert "咚咚" not in pos_9_words, "位置 9 不应有 '咚咚'"
        assert "咚" not in pos_9_words, "位置 9 不应有 '咚'"

    def test_complex_novel_text(self, detector):
        """
        测试复杂小说文本中的去重效果。
        """
        text = "哗啦啦的雨声中，突然轰隆一声雷响，接着是咚咚咚的敲门声，最后传来叮叮当当的风铃声。"
        results = detector.detect(text)
        
        texts = [r.text for r in results]
        
        # 应该检测到主要的 SFX
        assert "哗啦啦" in texts or "哗啦啦的" in texts, "应检测到水声 SFX"
        assert "轰隆" in texts, "应检测到爆炸声 SFX"
        assert "咚咚咚" in texts, "应检测到敲门声 SFX"
        assert "叮叮当当" in texts, "应检测到风铃声 SFX"

    def test_multiple_same_sfx(self, detector):
        """
        测试同一 SFX 在文本中多次出现的情况。
        """
        text = "咚咚！咚咚！咚！咚咚咚！"
        results = detector.detect(text)
        
        # 应该检测到多个 "咚咚" 或 "咚咚咚" 的出现
        assert len(results) > 0, "应检测到至少一个 SFX"


class TestAlgorithmCorrectness:
    """直接测试 _deduplicate() 算法的正确性"""

    @pytest.fixture
    def detector(self):
        return SfxDetector()

    def test_sort_order(self, detector):
        """
        验证去重前先按位置升序、长度降序排序。
        """
        matches = [
            SfxWord(text="哗", position=0, sfx_type="water"),
            SfxWord(text="哗啦啦", position=0, sfx_type="water"),
            SfxWord(text="哗啦", position=0, sfx_type="water"),
        ]
        results = detector._deduplicate(matches)
        
        # 应该只保留最长的
        assert len(results) == 1
        assert results[0].text == "哗啦啦"

    def test_containment_check(self, detector):
        """
        验证包含关系检查：短匹配完全在长匹配内部时应被移除。
        """
        matches = [
            SfxWord(text="轰隆隆隆", position=0, sfx_type="explosion"),
            SfxWord(text="轰隆", position=0, sfx_type="explosion"),
        ]
        results = detector._deduplicate(matches)
        
        assert len(results) == 1
        assert results[0].text == "轰隆隆隆"

    def test_no_containment_same_length(self, detector):
        """
        验证相同长度但不同文本的匹配不应被移除。
        """
        matches = [
            SfxWord(text="轰隆", position=0, sfx_type="explosion"),
            SfxWord(text="隆隆", position=1, sfx_type="explosion"),
        ]
        results = detector._deduplicate(matches)
        
        # [0,2) 和 [1,3) 重叠但不包含
        assert len(results) == 2

    def test_partial_overlap_not_contained(self, detector):
        """
        验证部分重叠但不完全包含的匹配应都被保留。
        例如：[0,3) 和 [1,4) 重叠但互不包含。
        """
        matches = [
            SfxWord(text="嗡嗡嗡", position=0, sfx_type="other"),
            SfxWord(text="嗡嗡嗡", position=1, sfx_type="other"),
        ]
        results = detector._deduplicate(matches)
        
        # [0,3) 和 [1,4) 互不包含
        assert len(results) == 2

    def test_contained_in_middle(self, detector):
        """
        验证中间位置被包含的情况。
        例如：长匹配 [0,5)，短匹配 [1,3) 完全在内部。
        """
        matches = [
            SfxWord(text="叮叮当当", position=0, sfx_type="other"),  # [0,4)
            SfxWord(text="叮当", position=1, sfx_type="other"),  # [1,3)
        ]
        results = detector._deduplicate(matches)
        
        assert len(results) == 1
        assert results[0].text == "叮叮当当"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
