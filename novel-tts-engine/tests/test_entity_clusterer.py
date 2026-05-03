# -*- coding: utf-8 -*-
"""EntityClusterer 单元测试

测试覆盖：
1. 上下文收集 (_collect_entity_contexts)
2. 字面重叠度计算 (_char_overlap)
3. 降级聚类策略 (_cluster_by_char_overlap)
4. 聚类跳过条件（实体太少/文本太短）
5. 聚类结果映射（member_to_center）
6. 称谓提取 (_extract_titles)
7. 重名消歧保护 (_is_ambiguous)
8. FO-05 短文本三级联动 (_link_from_character_db)
9. 边界条件
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.entity_clusterer import EntityClusterer, Cluster
from pipeline.nlp_basics import Entity
from pipeline.character_manager import CharacterManager


class MockSemanticRanker:
    """模拟语义排序器（返回 None 以触发降级聚类）"""
    
    def __init__(self, available=False):
        self._available = available
        self._loaded = False
    
    def is_available(self):
        return self._available
    
    def load_model(self):
        self._loaded = True
    
    def encode_batch(self, texts):
        return None


class TestEntityClusterer:
    @pytest.fixture
    def clusterer(self):
        """创建一个使用降级策略的聚类器（不依赖真实模型）"""
        return EntityClusterer(
            semantic_ranker=MockSemanticRanker(available=False),
            char_manager=CharacterManager(),
            merge_threshold=0.85,
            new_threshold=0.5,
            min_occurrences=3,
        )

    def test_char_overlap_identical(self, clusterer):
        """测试：相同字符串的重叠度为 1.0"""
        assert clusterer._char_overlap("萧炎", "萧炎") == 1.0

    def test_char_overlap_partial(self, clusterer):
        """测试：部分重叠的字符串"""
        # "萧炎" 和 "萧炎冷" 的字符重叠度
        overlap = clusterer._char_overlap("萧炎", "萧炎冷")
        assert 0.0 < overlap < 1.0

    def test_char_overlap_none(self, clusterer):
        """测试：无重叠的字符串"""
        assert clusterer._char_overlap("张三", "李四") == 0.0

    def test_char_overlap_empty(self, clusterer):
        """测试：空字符串"""
        assert clusterer._char_overlap("", "萧炎") == 0.0
        assert clusterer._char_overlap("萧炎", "") == 0.0
        assert clusterer._char_overlap("", "") == 0.0

    def test_collect_entity_contexts(self, clusterer):
        """测试：上下文收集"""
        text = "苏夜走进房间，苏夜看了看。苏夜说道。"
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
            Entity(text="苏夜", type="PER", start=8, end=10, confidence=0.9),
            Entity(text="苏夜", type="PER", start=15, end=17, confidence=0.9),
        ]
        
        contexts = clusterer._collect_entity_contexts(entities, text, window=10)
        
        assert "苏夜" in contexts
        assert len(contexts["苏夜"]) == 3

    def test_skip_too_few_entities(self, clusterer):
        """测试：候选实体太少时跳过聚类"""
        text = "苏夜走进房间。" * 500  # 文本足够长
        
        # 只有 2 个不同的实体（< 3，跳过聚类）
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
            Entity(text="苏夜", type="PER", start=6, end=8, confidence=0.9),
        ]
        
        result = clusterer.cluster(entities, text)
        
        # 应该直接返回原始实体（不聚类）
        assert len(result) == 2

    def test_skip_short_text(self, clusterer):
        """测试：文本太短时跳过聚类"""
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
            Entity(text="苏夜", type="PER", start=5, end=7, confidence=0.9),
            Entity(text="苏夜", type="PER", start=10, end=12, confidence=0.9),
        ]
        
        # 文本太短（< MIN_CLUSTER_CHARS = 3000）
        text = "苏夜走进了房间。苏夜看了看。苏夜点头。"
        
        result = clusterer.cluster(entities, text)
        
        # 短文本下应该走 _link_from_character_db 路径
        # 如果没有注册角色，应该返回原始实体
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_cluster_by_char_overlap(self, clusterer):
        """测试：字面重叠度降级聚类"""
        entities = ["萧炎", "萧炎冷", "萧炎道", "苏夜", "薰儿"]
        entity_counts = {"萧炎": 10, "萧炎冷": 3, "萧炎道": 2, "苏夜": 8, "薰儿": 5}
        
        clusters = clusterer._cluster_by_char_overlap(entities, entity_counts)
        
        # "萧炎冷" 和 "萧炎" 应该有字符重叠，可能被聚到同一聚类
        assert len(clusters) > 0
        
        # 找到"萧炎"的聚类
        xiao_yan_cluster = None
        for c in clusters:
            if c.center == "萧炎":
                xiao_yan_cluster = c
                break
        
        assert xiao_yan_cluster is not None
        # "萧炎"应该是中心（出现次数最多）

    def test_cluster_result_mapping(self, clusterer):
        """测试：聚类结果正确映射到实体"""
        # 创建足够长的文本
        text_parts = []
        for i in range(150):
            text_parts.append(f"苏夜做了一些事情{i}。")
            text_parts.append(f"苏夜看了看{i}。")
            text_parts.append(f"苏夜点头{i}。")
        
        text = "".join(text_parts)
        
        entities = [
            Entity(text="苏夜", type="PER", start=0, end=2, confidence=0.9),
            Entity(text="苏夜", type="PER", start=10, end=12, confidence=0.9),
            Entity(text="苏夜", type="PER", start=20, end=22, confidence=0.9),
        ]
        
        result = clusterer.cluster(entities, text)
        
        # 结果应该是一个列表
        assert isinstance(result, list)
        # 每个结果都应该是 Entity 类型
        for e in result:
            assert isinstance(e, Entity)

    def test_extract_titles(self):
        """测试：称谓提取"""
        assert "哥" in EntityClusterer._extract_titles("炎哥")
        assert "总" in EntityClusterer._extract_titles("苏总")
        assert "少爷" in EntityClusterer._extract_titles("萧少爷")
        assert len(EntityClusterer._extract_titles("苏夜")) == 0
        assert len(EntityClusterer._extract_titles("")) == 0

    def test_cluster_class(self):
        """测试：Cluster 数据类"""
        c = Cluster(center="萧炎", members=["萧炎冷", "萧炎道"], similarity=0.9, status="confirmed")
        assert c.center == "萧炎"
        assert len(c.members) == 2
        assert c.similarity == 0.9
        assert c.status == "confirmed"

    def test_cluster_default_values(self):
        """测试：Cluster 默认值"""
        c = Cluster(center="苏夜")
        assert c.members == []
        assert c.similarity == 1.0
        assert c.status == "confirmed"

    def test_empty_entities_list(self, clusterer):
        """测试：空实体列表"""
        text = "这是一段没有实体的文本。" * 200
        
        result = clusterer.cluster([], text)
        
        assert result == []

    def test_non_per_entities_pass_through(self, clusterer):
        """测试：非 PER 实体应该正常传递"""
        text_parts = []
        for i in range(150):
            text_parts.append(f"北京发生了事情{i}。")
            text_parts.append(f"上海的天气{i}。")
            text_parts.append(f"广州的人们{i}。")
        
        text = "".join(text_parts)
        
        entities = [
            Entity(text="北京", type="LOC", start=0, end=2, confidence=0.9),
            Entity(text="上海", type="LOC", start=10, end=12, confidence=0.9),
            Entity(text="广州", type="LOC", start=20, end=22, confidence=0.9),
        ]
        
        result = clusterer.cluster(entities, text)
        
        # 非 PER 实体不应该被字面重叠度聚类合并
        # 因为 "北京"、"上海"、"广州" 没有字符重叠
        assert len(result) >= 1
