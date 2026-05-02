# -*- coding: utf-8 -*-
"""EntityLinker 单元测试"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.entity_linker import EntityLinker, LinkedEntity, reset_entity_linker
from pipeline.nlp_basics import Entity
from pipeline.character_manager import CharacterManager


class TestEntityLinker:
    @pytest.fixture
    def linker(self):
        """创建实体链接器实例（不依赖全局单例）"""
        return EntityLinker()

    def test_link_non_per_entity_passthrough(self, linker):
        """测试非PER实体直接通过，不进行链接"""
        entities = [
            Entity(text="暗影会", type="ORG", start=0, end=3, confidence=0.9),
            Entity(text="江城", type="LOC", start=10, end=12, confidence=0.85),
        ]
        result = linker.link(entities, "暗影会在江城活动")
        assert len(result) == 2
        assert all(not e.is_linked for e in result)
        assert all(e.standard_name == "" for e in result)

    def test_link_single_char_per_filtered(self, linker):
        """测试单字PER实体被过滤"""
        entities = [
            Entity(text="林", type="PER", start=0, end=1, confidence=0.9),
            Entity(text="苏夜", type="PER", start=5, end=7, confidence=0.95),
        ]
        result = linker.link(entities, "林遇到了苏夜")
        # 单字PER应该被过滤
        per_results = [e for e in result if e.type == "PER"]
        assert len(per_results) == 1
        assert per_results[0].text == "苏夜"

    def test_link_returns_linked_entity_type(self, linker):
        """测试返回值包含 standard_name 和 is_linked 字段"""
        entities = [
            Entity(text="未知人物", type="PER", start=0, end=4, confidence=0.7),
        ]
        result = linker.link(entities, "未知人物走进了房间")
        assert len(result) == 1
        assert isinstance(result[0], LinkedEntity)
        assert hasattr(result[0], "standard_name")
        assert hasattr(result[0], "is_linked")

    def test_link_low_confidence_per_filtered(self, linker):
        """测试低置信度PER实体被过滤"""
        entities = [
            Entity(text="张三", type="PER", start=0, end=2, confidence=0.3),
        ]
        result = linker.link(entities, "张三不在角色库中")
        # 不在角色库且置信度 < 0.5 的PER应被过滤
        assert len(result) == 0
