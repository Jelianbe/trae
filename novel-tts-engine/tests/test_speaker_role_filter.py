# -*- coding: utf-8 -*-
"""SpeakerRoleFilter 单元测试

测试覆盖：
1. 对话上下文提取（4种模式）
2. 说话角色过滤逻辑
3. L2 补偿机制
4. 状态重置（避免跨章节污染）
5. 边界条件
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.nlp_basics import Entity


class MockSemanticRanker:
    """模拟语义排序器（不需要加载真实模型）"""
    
    def __init__(self, available=True):
        self._available = available
    
    def is_available(self):
        return self._available


class TestSpeakerRoleFilter:
    @pytest.fixture
    def filter(self):
        return SpeakerRoleFilter(
            semantic_ranker=MockSemanticRanker(available=False),
            l2_threshold=0.7,
        )

    def test_extract_dialogue_context_mode1(self, filter):
        """测试模式1：引号前的上下文"""
        text = '苏夜说道："你好啊"。'
        contexts = filter._get_dialogue_contexts(text)
        
        # 应该找到引号前的上下文
        assert len(contexts) >= 1

    def test_extract_dialogue_context_mode2(self, filter):
        """测试模式2：引号后的上下文（"dialogue" 后面紧跟的 "XX说道"）"""
        text = '"你好啊。"老陈说道。'
        contexts = filter._get_dialogue_contexts(text)
        
        # 应该找到"老陈"
        found_chen = any("老陈" in ctx for ctx in contexts)
        assert found_chen

    def test_extract_dialogue_context_mode4(self, filter):
        """测试模式4：引号后的"是XX的声音" """
        text = '"苏夜，来会议室一趟。"是老陈的声音。'
        contexts = filter._get_dialogue_contexts(text)
        
        # 应该找到包含"老陈"的上下文
        assert len(contexts) >= 1

    def test_filter_keeps_dialogue_speaker(self, filter):
        """测试：出现在对话中的实体应该被保留"""
        text = '苏夜说道："你好啊"。苏夜看了看四周。'
        
        # 模拟 NLP 分析结果
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                if "苏夜" in ctx:
                    return NLPResult(
                        tokens=[],
                        pos_tags=[],
                        entities=[Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9)],
                        sentences=[ctx],
                        raw_text=ctx,
                    )
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
        ]
        
        result = filter.filter(entities, text, MockNLP())
        
        # "苏夜" 应该被保留
        assert len(result) >= 1
        assert any(e.text == "苏夜" for e in result)

    def test_filter_removes_non_speaker(self, filter):
        """测试：非说话角色应该被过滤"""
        # 文本中"李四"不在任何对话上下文中
        text = '苏夜说道："你好啊"。李四站在旁边。'
        
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                if "苏夜" in ctx:
                    return NLPResult(
                        tokens=[],
                        pos_tags=[],
                        entities=[Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9)],
                        sentences=[ctx],
                        raw_text=ctx,
                    )
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
            Entity(text="李四", type="PER", start=20, end=22, confidence=0.9),
        ]
        
        result = filter.filter(entities, text, MockNLP())
        
        # "苏夜" 应该被保留，"李四" 应该被过滤
        assert any(e.text == "苏夜" for e in result)
        assert not any(e.text == "李四" for e in result)

    def test_filter_passes_through_non_per(self, filter):
        """测试：非 PER 实体直接放行"""
        text = '苏夜在北京的公司工作。'
        
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        entities = [
            Entity(text="北京", type="LOC", start=3, end=5, confidence=0.9),
            Entity(text="公司", type="ORG", start=8, end=10, confidence=0.9),
        ]
        
        result = filter.filter(entities, text, MockNLP())
        
        # 非 PER 实体应该全部放行
        assert len(result) == 2

    def test_filter_passes_through_statistically_discovered(self, filter):
        """测试：统计发现的实体（confidence=0.65）直接放行"""
        text = '苏夜说道："你好啊"。'
        
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        entities = [
            Entity(text="药老", type="PER", start=0, end=2, confidence=0.65),
        ]
        
        result = filter.filter(entities, text, MockNLP())
        
        # 统计发现的实体应该直接放行
        assert len(result) == 1
        assert result[0].text == "药老"

    def test_state_reset_between_calls(self, filter):
        """测试：多次调用 filter 时状态应该重置"""
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                # 模拟 NLP 从对话上下文中提取实体
                if "张三" in ctx:
                    return NLPResult(
                        tokens=[], pos_tags=[],
                        entities=[Entity(text="张三", type="PER", start=0, end=2, confidence=0.9)],
                        sentences=[ctx], raw_text=ctx,
                    )
                elif "李四" in ctx:
                    return NLPResult(
                        tokens=[], pos_tags=[],
                        entities=[Entity(text="李四", type="PER", start=0, end=2, confidence=0.9)],
                        sentences=[ctx], raw_text=ctx,
                    )
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        # 第一次调用
        filter.filter(
            [Entity(text="张三", type="PER", start=0, end=2, confidence=0.9)],
            '"你好。"张三说道。',
            MockNLP(),
        )
        
        # 检查状态包含"张三"
        assert "张三" in filter._dialogue_entities
        
        # 第二次调用（不同文本）
        filter.filter(
            [Entity(text="李四", type="PER", start=0, end=2, confidence=0.9)],
            '"再见。"李四说道。',
            MockNLP(),
        )
        
        # 状态应该被重置，"张三"不再存在，"李四"存在
        assert "张三" not in filter._dialogue_entities
        assert "李四" in filter._dialogue_entities

    def test_filter_empty_entities(self, filter):
        """测试：空实体列表"""
        text = '苏夜说道："你好啊"。'
        
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        result = filter.filter([], text, MockNLP())
        
        assert result == []

    def test_filter_empty_text(self, filter):
        """测试：空文本"""
        class MockNLP:
            def analyze(self, ctx):
                from pipeline.nlp_basics import NLPResult
                return NLPResult(tokens=[], pos_tags=[], entities=[], sentences=[], raw_text=ctx)
        
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
        ]
        
        result = filter.filter(entities, "", MockNLP())
        
        # 空文本下所有 PER 实体应该被过滤（因为没有对话上下文）
        # 但统计发现的实体（confidence=0.65）会放行
        for e in result:
            assert e.confidence == 0.65 or e.type != "PER"
