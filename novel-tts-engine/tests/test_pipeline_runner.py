# -*- coding: utf-8 -*-
"""PipelineRunner 单元测试"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.pipeline_runner import PipelineRunner


class TestPipelineRunner:
    @pytest.fixture
    def runner(self):
        return PipelineRunner()

    def test_entity_in_sentence_exact_match(self, runner):
        """测试精确匹配：实体完整出现在句子中"""
        assert PipelineRunner._entity_in_sentence("苏夜", 0, 2, "苏夜走进了房间") is True

    def test_entity_in_sentence_boundary_protection(self, runner):
        """测试边界保护：单字实体不应匹配到更长词的一部分"""
        # "林" 不应匹配到 "树林里"（"树林" 是一个完整词）
        assert PipelineRunner._entity_in_sentence("林", 0, 1, "他走进了树林里") is False

    def test_entity_in_sentence_not_found(self, runner):
        """测试实体不在句子中"""
        assert PipelineRunner._entity_in_sentence("张三", 0, 2, "李四走进了房间") is False

    def test_entity_in_sentence_empty_input(self, runner):
        """测试空输入"""
        assert PipelineRunner._entity_in_sentence("", 0, 0, "") is False
        assert PipelineRunner._entity_in_sentence("实体", 0, 2, "") is False
        assert PipelineRunner._entity_in_sentence("", 0, 0, "句子") is False
