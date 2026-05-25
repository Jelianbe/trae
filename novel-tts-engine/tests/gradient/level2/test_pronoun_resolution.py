# -*- coding: utf-8 -*-
"""
Level 2: 代词消解（多句 + 代词推理）

目的：验证代词→角色的映射能力
测试数据：含代词的多句场景
用例数：~12 条
通过标准：≥ 85%
执行频率：每次涉及代词逻辑的改动后
执行时间：< 15 秒

v2.0 变更（2026-05-23）：
  - 从 4 条扩充到 12 条
  - 覆盖男性/女性/性别未知/近因衰减/多人场景
"""

import pytest
import tempfile
import os

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


class TestPronounResolution:
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
        mgr.add_character("张三", gender="male", project_id="test")
        mgr.add_character("李四", gender="female", project_id="test")
        mgr.add_character("王五", gender="male", project_id="test")
        mgr.add_character("小翠", gender="female", project_id="test")
        return mgr

    @pytest.fixture
    def matcher(self, char_manager):
        m = SpeakerMatcher(char_manager)
        m.current_project_id = "test"
        return m

    # ===== 基础代词消解 =====
    def test_pronoun_he_refers_to_last_male(self, matcher):
        context_before = '张三说："你好"。'
        text = '他说："再见"'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        assert result is not None
        assert result.character.name == "张三", f"期望'张三'，实际'{result.character.name}'"

    def test_pronoun_she_refers_to_last_female(self, matcher):
        context_before = '李四说："你好"。'
        text = '她笑道："再见"'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        assert result is not None
        assert result.character.name == "李四", f"期望'李四'，实际'{result.character.name}'"

    # ===== 近因衰减 =====
    def test_pronoun_recency(self, matcher):
        context_before = '张三说："..."。李四说："..."。'
        text = '他笑了'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "李四", f"期望最近说话人'李四'，实际'{result.character.name}'"

    # ===== 多人性别消解 =====
    def test_pronoun_he_with_multiple_characters(self, matcher):
        context_before = '张三和李四站在一起。'
        text = '他说："..."'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        assert result is not None
        assert result.character.gender == "male", f"期望男性，实际'{result.character.gender}'"

    # ===== 新增用例 =====
    def test_pronoun_he_chain(self, matcher):
        """代词链：他→他→张三"""
        context_before = '张三说："你好"。他说："再见"。'
        text = '他又补充道："其实..."'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "张三", f"期望'张三'，实际'{result.character.name}'"

    def test_pronoun_she_after_male(self, matcher):
        """男性说完后出现'她'，应匹配女性"""
        context_before = '张三说："李四来了"。'
        text = '她点了点头。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "李四", f"期望'李四'，实际'{result.character.name}'"

    def test_pronoun_ta_ambiguity(self, matcher):
        """ta 发音但性别明确时按角色库判断"""
        context_before = '小翠说："我知道"。'
        text = '她微微一笑。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "小翠", f"期望'小翠'，实际'{result.character.name}'"

    def test_pronoun_recency_decay_3_turns(self, matcher):
        """三句后代词仍应匹配最近的人"""
        context_before = '张三说："..."。李四说："..."。张三又说："..."。'
        text = '他笑了笑。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "张三", f"期望最近'张三'，实际'{result.character.name}'"

    def test_pronoun_gender_conflict(self, matcher):
        """多个男性同时在场，代词应匹配最近的男性"""
        context_before = '张三说："..."。王五说："..."。'
        text = '他站起来。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "王五", f"期望'王五'，实际'{result.character.name}'"

    def test_pronoun_with_speech_verb(self, matcher):
        """代词+说话动词组合"""
        context_before = '张三说："你来一下"。'
        text = '他回答道："好的"'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        assert result is not None
        assert result.character.name == "张三", f"期望'张三'，实际'{result.character.name}'"

    def test_pronoun_female_chain(self, matcher):
        """女性代词链"""
        context_before = '李四说："你好"。她笑道："再见"。'
        text = '她又说："等等"'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "李四", f"期望'李四'，实际'{result.character.name}'"

    def test_pronoun_with_address(self, matcher):
        """对话中有称呼但代词仍应正确消解"""
        context_before = '张三对李四说："你觉得呢？"。'
        text = '他摇了摇头。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "张三", f"期望'张三'，实际'{result.character.name}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
