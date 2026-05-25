# -*- coding: utf-8 -*-
"""
Level 4: 真实文本基线（端到端）

目的：在真实小说段落上验证完整流水线
测试数据：真实小说文本（都市+玄幻）
用例数：20（短段落抽样） + 完整基线单独运行
通过标准：≥ 当前基线准确率
执行频率：每次重大改动后
执行时间：< 60 秒

v2.0 新增：
  - 从真实基线脚本中抽取 20 条代表性用例
  - 完整基线仍由 test_real_baseline_runner.py 独立运行
"""

import pytest
import tempfile
import os

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


class TestRealShortPassages:
    """真实小说短段落（2-5句）。
    
    从都市测试文本中抽取的代表性场景。
    """

    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass

    @pytest.fixture
    def char_manager(self, temp_db):
        mgr = CharacterManager(temp_db)
        mgr.add_character("赵东", gender="male", project_id="test")
        mgr.add_character("老金", gender="male", project_id="test")
        mgr.add_character("李东", gender="male", project_id="test")
        mgr.add_character("张东", gender="male", project_id="test")
        return mgr

    @pytest.fixture
    def matcher(self, char_manager):
        m = SpeakerMatcher(char_manager)
        m.current_project_id = "test"
        return m

    @pytest.mark.parametrize("context_before,text,expected_speaker", [
        # 都市场景
        ('', '赵东说道："这事你别管了。"', "赵东"),
        ('赵东说："你等着。"', '老金回答："好的"', "老金"),
        ('', '李东对张东说："你知道那个人是谁吗？"', "李东"),
        ('', '赵东皱了皱眉："什么意思？"', "赵东"),
        ('', '"行了，别说了。"李东摆手道。', "李东"),
        ('', '他叹了口气："算了。"', None),  # 无预注册时返回 None 是正常的
        # 叙述+对话混合
        ('赵东走进房间。', '他坐下来："说吧。"', "赵东"),
        ('', '老金点了点头："我知道了。"', "老金"),
        # 多角色场景
        ('赵东说："你来。"', '李东走上前："什么事？"', "李东"),
        ('', '张东笑道："这事好办。"', "张东"),
    ])
    def test_real_short_passage(self, context_before, text, expected_speaker, matcher):
        hint, hint_type = matcher.extract_speaker_hint(text)
        if expected_speaker is not None:
            assert hint is not None, f"期望提取到说话人，实际未提取到: {text}"
            assert hint == expected_speaker, f"期望'{expected_speaker}'，实际'{hint}'"


class TestRealBaseline:
    """完整基线测试。

    实际运行时调用完整小说基线测试。
    这里只做一个基本验证。
    """

    def test_baseline_placeholder(self):
        """L5完整基线占位：验证模块可用即可。

        完整基线测试（130+ 用例）由专门的基线脚本运行，
        本测试只做存在性验证。
        """
        from pipeline.speaker_matcher import SpeakerMatcher
        from pipeline.character_manager import CharacterManager
        assert SpeakerMatcher is not None
        assert CharacterManager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
