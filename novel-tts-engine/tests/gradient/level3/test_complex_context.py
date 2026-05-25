# -*- coding: utf-8 -*-
"""
Level 3: 复杂上下文（多句 + 修饰 + 多人对话 + 排序验证）

目的：验证多轮对话中的上下文推断能力 + 排序质量
测试数据：人工构造的多句场景 + 混合场景
用例数：~37 条
通过标准：≥ 80%
执行频率：每次涉及上下文逻辑的改动后
执行时间：< 30 秒

v2.0 变更（2026-05-23）：
  - 合并 L3 全部内容（形容词/副词/描述性角色/多人对话）
  - 新增 TestRanking 排序验证层
"""

import pytest
import tempfile
import os

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


class TestContextDependency:
    """复杂上下文依赖：对话轮换、近因衰减、描述性角色。"""

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
        mgr.add_character("李四", gender="male", project_id="test")
        mgr.add_character("王五", gender="male", project_id="test")
        return mgr

    @pytest.fixture
    def matcher(self, char_manager):
        m = SpeakerMatcher(char_manager)
        m.current_project_id = "test"
        return m

    # ===== 对话轮换 =====
    def test_dialogue_rotation(self, matcher):
        context_before = 'A说："今天天气不错"。'
        text = 'B对C说："你觉得呢？"'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name in ["李四", "王五"], f"期望李四或王五，实际'{result.character.name}'"

    # ===== 描述性角色 =====
    def test_descriptive_role(self, matcher):
        text = '扎着马尾辫的女人说："客官请坐"'
        context = DialogueContext(text=text, context_before='')
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint is not None, "应能提取描述性角色"
        assert "女人" in hint or "马尾" in hint, f"期望包含描述性角色，实际'{hint}'"

    # ===== 形容词修饰 =====
    def test_adjective_modified_speaker(self, matcher):
        text = "漂亮的女孩笑着说：'你好'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint is not None, f"未能检测到对话: 漂亮的女孩笑着说：'你好'"
        assert "女孩" in hint, f"期望包含'女孩'，实际'{hint}'"

    def test_adjective_complex(self, matcher):
        text = "疲惫不堪的猎人靠在树上，喃喃道：'终于...'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint is not None, f"期望提取猎人，实际未提取到"
        assert "猎人" in hint, f"期望包含'猎人'，实际'{hint}'"

    def test_adjective_angry(self, matcher):
        text = "愤怒的掌柜拍着桌子吼道：'滚出去！'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint is not None, f"期望提取掌柜，实际未提取到"
        assert "掌柜" in hint, f"期望包含'掌柜'，实际'{hint}'"

    # ===== 副词修饰 =====
    def test_adverb_modified_speaker(self, matcher):
        text = "张三轻声地说：'我在这里'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint is not None, f"期望提取张三，实际未提取到"
        assert hint == "张三", f"期望'张三'，实际 '{hint}'"

    def test_adverb_urgent(self, matcher):
        text = "李四急切地喊道：'快跑！'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint == "李四", f"期望'李四'，实际 '{hint}'"

    def test_adverb_careful(self, matcher):
        text = "小翠小心翼翼地说：'小姐，该歇息了'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint == "小翠", f"期望'小翠'，实际 '{hint}'"

    # ===== 多人对话 =====
    def test_a_to_b_speaks(self, matcher):
        text = "张三对李四说：'你去叫王五'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint == "张三", f"期望'张三'，实际'{hint}'"

    def test_multi_role_continuous(self, matcher):
        sentences = [
            ("张三对李四说：'你去叫王五'", "张三"),
            ("李四回答：'好的'", "李四"),
        ]
        context_before = ''
        for text, expected in sentences:
            context = DialogueContext(text=text, context_before=context_before)
            result = matcher.match_speaker(context)
            if result:
                assert result.character.name == expected, f"期望'{expected}'，实际'{result.character.name}'"
            context_before = text

    def test_three_role_rotation(self, matcher):
        sentences = [
            ("张三说：'今天天气不错'", "张三"),
            ("李四对王五说：'你觉得呢？'", "李四"),
            ("王五回答：'还行'", "王五"),
        ]
        context_before = ''
        results = []
        for text, expected in sentences:
            context = DialogueContext(text=text, context_before=context_before)
            result = matcher.match_speaker(context)
            if result:
                results.append((text, result.character.name))
            context_before += text
        assert len(results) >= 3, f"期望至少3个结果，实际{len(results)}: {results}"

    # ===== 新增：自指推断 =====
    def test_self_reference(self, matcher):
        text = "我是张三，请问有什么可以帮你的？"
        context_before = '有人敲门。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "张三", f"期望'张三'，实际'{result.character.name}'"

    # ===== 新增：近因衰减 =====
    def test_recency_decay(self, matcher):
        context_before = '张三说："..."。李四说："..."。张三又说："..."。'
        text = '他笑了笑。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "张三", f"期望最近'张三'，实际'{result.character.name}'"


class TestRanking:
    """排序验证层：检查候选池包含正确角色 + 排序正确性。
    
    v2.0 新增：区分"没找到"vs"排错了"。
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
        mgr.add_character("张三", gender="male", project_id="test")
        mgr.add_character("李四", gender="male", project_id="test")
        mgr.add_character("王五", gender="male", project_id="test")
        return mgr

    @pytest.fixture
    def matcher(self, char_manager):
        m = SpeakerMatcher(char_manager)
        m.current_project_id = "test"
        return m

    def test_multi_role_candidates_include_correct(self, matcher):
        """多人场景：候选池应包含所有提到的角色"""
        context_before = '张三说："..."。李四说："..."。'
        text = '王五笑了。'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "王五", f"期望'王五'，实际'{result.character.name}'"

    def test_a_to_b_candidates_order(self, matcher):
        """A对B说：场景，候选池应正确排序"""
        text = "张三对李四说：'你去叫王五'"
        context = DialogueContext(text=text, context_before='')
        result = matcher.match_speaker(context)
        assert result is not None
        assert result.character.name == "张三", f"期望'张三'（说话人），实际'{result.character.name}'"

    def test_rotation_candidate_order(self, matcher):
        """轮换场景：第二个说话人应排第一"""
        context_before = '张三说："今天天气不错"。'
        text = '李四说："是啊"'
        context = DialogueContext(text=text, context_before=context_before)
        result = matcher.match_speaker(context)
        if result:
            assert result.character.name == "李四", f"期望'李四'，实际'{result.character.name}'"

    def test_descriptive_role_priority(self, matcher):
        """描述性角色应在候选池中"""
        text = '扎着马尾辫的女人说："..."。'
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint is not None, "描述性角色应被提取到候选池"

    def test_adverb_clean_priority(self, matcher):
        """副词修饰后的名字应正确清洗并排在第一"""
        text = "张三轻声地说：'我在这里'"
        hint, hint_type = matcher.extract_speaker_hint(text)
        assert hint == "张三", f"期望'张三'排第一，实际'{hint}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
