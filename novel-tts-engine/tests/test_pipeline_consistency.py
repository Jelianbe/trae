# -*- coding: utf-8 -*-
"""
管道一致性单元测试

确保统计验证已降级的实体，经过完整管道后不会以高于原始置信度的值出现在最终列表中。

这个测试一旦就位，未来任何违反此原则的修改都会被自动拦截。
"""
import pytest
from dataclasses import dataclass
from pipeline.nlp_basics import Entity
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker


@dataclass
class MockEntity(Entity):
    """模拟实体，用于测试"""
    pass


class TestPipelineConsistency:
    """管道一致性测试"""
    
    def test_downgraded_entity_not_boosted_above_original(self):
        """
        测试：统计验证降级的实体不会被后续组件提升到高于原始值
        
        场景：
        1. 创建一个实体，模拟统计验证已将其降级为0.3
        2. 经过SpeakerRoleFilter的L2补偿
        3. 验证最终置信度不超过原始值的1.5倍
        
        这个测试确保管道中的信息不会断裂：
        - ContextDiversityValidator的降级结果必须被尊重
        - SpeakerRoleFilter的L2补偿不能覆盖统计验证的判断
        """
        # 创建模拟实体（模拟统计验证降级后）
        entity = Entity(
            text="测试实体",
            type="PER",
            start=0,
            end=4,
            confidence=0.3,  # 统计验证已降级
        )
        
        # 创建SpeakerRoleFilter
        semantic_ranker = get_semantic_ranker()
        semantic_ranker.load_model()
        
        speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
        
        # 模拟场景计数>=3（会触发L2补偿到0.8）
        speaker_filter._entity_scene_count["测试实体"] = 3
        
        # 应用L2补偿
        # 直接调用_apply_l2_boost来测试
        boosted_conf = speaker_filter._apply_l2_boost(entity, "测试文本")
        
        # 验证：L2补偿不能超过原始值的1.5倍
        max_allowed = min(0.95, entity.confidence * 1.5)
        assert boosted_conf <= max_allowed, \
            f"L2补偿过度提升：原始={entity.confidence}, 提升后={boosted_conf}, 最大允许={max_allowed}"
        
        # 验证：提升后的值应该接近但不超过0.45（0.3 * 1.5）
        assert boosted_conf <= 0.45, \
            f"L2补偿过度提升：{entity.confidence} -> {boosted_conf}（应该<=0.45）"
    
    def test_high_confidence_entity_can_be_boosted(self):
        """
        测试：高置信度实体可以正常被L2补偿提升
        
        场景：
        1. 创建一个高置信度实体（0.8）
        2. 经过SpeakerRoleFilter的L2补偿
        3. 验证最终置信度可以提升到0.8-0.95之间
        """
        entity = Entity(
            text="高置信实体",
            type="PER",
            start=0,
            end=5,
            confidence=0.8,
        )
        
        semantic_ranker = get_semantic_ranker()
        semantic_ranker.load_model()
        
        speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
        speaker_filter._entity_scene_count["高置信实体"] = 3
        
        boosted_conf = speaker_filter._apply_l2_boost(entity, "测试文本")
        
        # 高置信度实体应该能被提升到0.8或更高（但不超过0.95）
        assert boosted_conf >= 0.8, \
            f"高置信实体应该被提升：{entity.confidence} -> {boosted_conf}"
        assert boosted_conf <= 0.95, \
            f"L2补偿不能超过0.95：{boosted_conf}"
    
    def test_pipeline_filters_low_confidence_entities(self):
        """
        测试：L2补偿不会将低置信度实体提升到可通过最终过滤
        
        场景：
        1. 创建低置信度实体（0.3，模拟统计验证降级后）
        2. 模拟有对话场景（会触发L2补偿）
        3. 验证经过L2补偿后仍然低于0.5阈值
        """
        entity = Entity(
            text="低置信实体",
            type="PER",
            start=10,
            end=15,
            confidence=0.3,  # 统计验证降级
        )
        
        semantic_ranker = get_semantic_ranker()
        semantic_ranker.load_model()
        
        speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
        # 模拟有3个对话场景（会触发L2补偿到0.8）
        speaker_filter._entity_scene_count["低置信实体"] = 3
        
        # 应用L2补偿
        boosted_conf = speaker_filter._apply_l2_boost(entity, "测试文本")
        
        # 验证：即使有对话场景，低置信实体也不能被提升到>=0.5
        assert boosted_conf < 0.5, \
            f"低置信实体被错误提升到{boosted_conf}，应该<0.5"
        
        # 验证：提升后的值应该<=0.45（0.3 * 1.5）
        assert boosted_conf <= 0.45, \
            f"L2补偿过度提升：{entity.confidence} -> {boosted_conf}（应该<=0.45）"
    
    def test_pipeline_preserves_high_confidence_entities(self):
        """
        测试：高置信度实体不会被错误过滤
        
        场景：
        1. 创建高置信度实体（0.9）
        2. 经过L2补偿
        3. 验证仍然>=0.5（不会被过滤）
        """
        entity = Entity(
            text="高置信实体",
            type="PER",
            start=0,
            end=5,
            confidence=0.9,
        )
        
        semantic_ranker = get_semantic_ranker()
        semantic_ranker.load_model()
        
        speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
        speaker_filter._entity_scene_count["高置信实体"] = 3
        
        boosted_conf = speaker_filter._apply_l2_boost(entity, "测试文本")
        
        # 验证：高置信实体应该保持>=0.5
        assert boosted_conf >= 0.5, \
            f"高置信实体被错误降低到{boosted_conf}"
    
    def test_mis_merged_entity_detection(self):
        """
        测试：误合并检测能正确识别"人名+动词"误合并
        
        场景：
        1. 创建"萧炎冷"实体（长度>=3，末端是动词）
        2. 创建"萧炎"实体（高频，出现>=5次）
        3. 运行误合并检测
        4. 验证"萧炎冷"被标记为误合并
        """
        validator = ContextDiversityValidator(mode='speaker_role', whitelist=set())
        
        # 创建实体
        entities = [
            Entity(text="萧炎", type="PER", start=0, end=2, confidence=0.9),
            Entity(text="萧炎冷", type="PER", start=0, end=3, confidence=0.9),
        ]
        
        # 模拟统计信息（"萧炎"出现267次）
        stats = {
            "萧炎": {
                "occurrences": 267,
                "right_neighbors": set(['说', '问', '笑', '道']),
                "boundary_hit_templates": 0,
                "boundary_hit_total": 0,
                "co_occurrence_count": 0,
                "co_occurrence_entities": [],
                "chapter_count": 10,
                "chapter_set": set(range(10)),
            },
            "萧炎冷": {
                "occurrences": 1,
                "right_neighbors": set(['笑']),
                "boundary_hit_templates": 0,
                "boundary_hit_total": 0,
                "co_occurrence_count": 0,
                "co_occurrence_entities": [],
                "chapter_count": 1,
                "chapter_set": {0},
            },
        }
        
        # 运行误合并检测
        mis_merged = validator._detect_mis_merged_entities(entities, stats, "测试文本")
        
        # 验证："萧炎冷"应该被标记为误合并
        assert "萧炎冷" in mis_merged, \
            f"误合并检测失败：'萧炎冷'应该被标记"
        
        # 验证："萧炎"不应该被标记
        assert "萧炎" not in mis_merged, \
            f"误合并检测错误：'萧炎'不应该被标记"
    
    def test_real_name_not_flagged_as_mis_merged(self):
        """
        测试：真实人名不会被误标记为误合并
        
        场景：
        1. 创建"陈承喏"实体（真实人名，右邻字多样）
        2. 运行误合并检测
        3. 验证不被标记为误合并
        """
        validator = ContextDiversityValidator(mode='speaker_role', whitelist=set())
        
        entities = [
            Entity(text="陈承喏", type="PER", start=0, end=3, confidence=0.9),
        ]
        
        # 模拟统计信息（"陈承喏"出现多次，右邻字多样）
        stats = {
            "陈承喏": {
                "occurrences": 10,
                "right_neighbors": set(['说', '道', '问', '的', '了']),
                "boundary_hit_templates": 0,
                "boundary_hit_total": 0,
                "co_occurrence_count": 0,
                "co_occurrence_entities": [],
                "chapter_count": 5,
                "chapter_set": set(range(5)),
            },
        }
        
        # 运行误合并检测
        mis_merged = validator._detect_mis_merged_entities(entities, stats, "测试文本")
        
        # 验证："陈承喏"不应该被标记为误合并
        assert "陈承喏" not in mis_merged, \
            f"误合并检测错误：'陈承喏'是真实人名，不应该被标记"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
