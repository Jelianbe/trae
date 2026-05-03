# -*- coding: utf-8 -*-
"""
SpeakerRoleFilter - 说话角色过滤器

只保留出现在对话引导词附近的实体，过滤掉旁白中的非说话角色。
与 ContextDiversityValidator 正交融合，形成交叉验证。
"""
import re
import threading
from typing import List, Set, Dict, Optional
from pipeline.nlp_basics import NLPBasics, Entity, get_nlp


class SpeakerRoleFilter:
    """说话角色过滤器：只保留出现在对话引导词附近的实体"""
    
    # 对话引导词模式
    DIALOGUE_PATTERNS = [
        r'["\u201c]',  # 左引号
    ]
    
    def __init__(self, semantic_ranker=None, l2_threshold=0.7):
        self.semantic_ranker = semantic_ranker
        self.l2_threshold = l2_threshold
        self._dialogue_entities = set()  # 说话角色集合
        self._entity_scene_count: Dict[str, int] = {}  # 实体出现在不同对话场景的次数
    
    def _get_dialogue_contexts(self, text: str) -> List[str]:
        """提取所有可能包含说话人提示的上下文窗口
        
        支持四种模式：
        - 模式1：引号前的上下文（如 "苏夜说道："）
        - 模式2：引号后的上下文（如 ""少爷，您醒了。"老陈说道。"）
        - 模式3：引号中间的说话人提示（如 ""少爷，"老陈说道，"您醒了。"）
        - 模式4：引号后的"是XX的声音/话"（如 ""苏夜，来会议室一趟。"是老陈的声音。"）
        """
        contexts = []
        
        # 模式1：引号前的上下文（已有）
        # 匹配左引号前的15字符窗口
        pattern1 = re.compile(r'["\u201c].*?["\u201d]')
        for match in pattern1.finditer(text):
            start = match.start()
            context_window = text[max(0, start-15):start]
            contexts.append(context_window.strip())
        
        # 模式2：引号后的上下文（新增）
        # 匹配 "dialogue" 后面紧跟的 "XX说道"
        pattern2 = re.compile(r'["\u201d]\s*([^，。！？\n]{2,10}?)(?:说道|问道|喊道|笑道|道|说)')
        for match in pattern2.finditer(text):
            speaker = match.group(1).strip()
            if speaker:
                contexts.append(speaker)
        
        # 模式3：引号中间的说话人提示（新增）
        # 匹配 "dialogue，" XX说道，"dialogue"
        pattern3 = re.compile(r'["\u201d]\s*，\s*([^，。！？\n]{2,10}?)(?:说道|问道|喊道|笑道|道|说)\s*[，,]\s*["\u201c]')
        for match in pattern3.finditer(text):
            speaker = match.group(1).strip()
            if speaker:
                contexts.append(speaker)
        
        # 模式4：引号后的"是XX的声音/话"（新增）
        # 匹配 "dialogue" 是 XX 的声音/话
        # 兼容格式："苏夜，来会议室一趟。"是部门经理老陈的声音。
        # 策略：提取右引号到"的声音"之间的文本，让NLP从中提取PER实体
        pattern4 = re.compile(r'["\u201d]([^。！？\n]{1,30}?)的(?:声音|话)')
        for match in pattern4.finditer(text):
            context = match.group(1).strip()
            if context and '是' in context:
                contexts.append(context)
        
        return contexts
    
    def _extract_dialogue_entities(self, text: str, nlp: NLPBasics) -> Set[str]:
        """从所有对话上下文中提取说话角色候选实体"""
        contexts = self._get_dialogue_contexts(text)
        entities = set()
        seen_scenes = set()
        
        for ctx in contexts:
            if not ctx:
                continue
            
            # 用NLP分析上下文窗口，提取PER实体
            result = nlp.analyze(ctx)
            for e in result.entities:
                if e.type == 'PER':
                    entities.add(e.text)
                    # 统计出现在不同场景的次数（用上下文窗口作为场景区分）
                    scene_key = ctx[:30]  # 截取前30字作为场景ID
                    if scene_key not in seen_scenes:
                        self._entity_scene_count[e.text] = self._entity_scene_count.get(e.text, 0) + 1
                        seen_scenes.add(scene_key)
        
        return entities
    
    def filter(self, entities: List[Entity], text: str, nlp: NLPBasics) -> List[Entity]:
        """
        对实体列表执行说话角色过滤：
        - 非PER实体（ORG/LOC）直接放行
        - PER实体：只有出现在 dialogue_entities 集合中的才能被保留
        - 对低频但多次出现在不同对话场景中的实体，通过L2提升置信度
        
        2026-05-02 修复：统计发现的实体（confidence=0.65）直接放行。
        这些实体是通过discover_compound_entities从全文扫描中发现的，
        已经经过了严格的统计验证（出现在对话引导词附近≥2次），
        不需要再经过_dialogue_entities的二次过滤。
        """
        # 每次调用时重置状态，避免跨章节/跨文本的状态污染
        self._dialogue_entities = set()
        self._entity_scene_count = {}
        
        # 提取说话角色集合
        self._dialogue_entities = self._extract_dialogue_entities(text, nlp)
        
        filtered = []
        for e in entities:
            # ORG/LOC处理已移除（2026-05-02 修正方案）
            # nlp_basics.analyze() 现在只返回 PER 实体，无需再过滤
            if e.type != 'PER':
                filtered.append(e)
                continue
            
            # 2026-05-02 修复：统计发现的实体直接放行
            # 这些实体已经通过discover_compound_entities的严格验证
            if getattr(e, 'confidence', 1.0) == 0.65:
                filtered.append(e)
                continue
            
            # PER实体：过滤非说话角色
            if e.text not in self._dialogue_entities:
                continue
            
            # 对低频实体进行L2补偿
            if e.confidence < 0.5 and self.semantic_ranker:
                new_conf = self._apply_l2_boost(e, text)
                if new_conf > e.confidence:
                    e.confidence = new_conf
            
            filtered.append(e)
        
        return filtered
    
    def _apply_l2_boost(self, entity: Entity, full_text: str) -> float:
        """
        检查该实体作为说话人的场景次数，提升置信度
        
        2026-05-02 修复：L2补偿不应覆盖统计验证的降级结果。
        统计验证（ContextDiversityValidator）已经将某些实体降级为低置信度（如0.3），
        这表示该实体在统计意义上不可靠（右邻字单一、共现多样性低等）。
        L2补偿只能在原始置信度的基础上做小幅增量，不能超过原始值的1.5倍。
        这确保统计验证的降级结果不会被意外覆盖。
        """
        original_conf = entity.confidence
        scene_count = self._entity_scene_count.get(entity.text, 0)
        
        if scene_count >= 2 and self.semantic_ranker.is_available():
            # 根据场景次数计算L2提升后的置信度
            if scene_count >= 3:
                l2_boosted = 0.8
            else:
                l2_boosted = 0.65
            
            # 修复：L2补偿不能超过原始置信度的1.5倍
            # 防止统计验证已降级的实体（如0.3）被提升到过高值（如0.65）
            max_allowed = min(0.95, original_conf * 1.5)
            return min(l2_boosted, max_allowed)
        
        return entity.confidence


# ============================================================
# 全局单例
# ============================================================

_filter_instance: Optional[SpeakerRoleFilter] = None
_filter_lock = threading.Lock()


def get_speaker_role_filter(semantic_ranker=None, l2_threshold=0.7) -> SpeakerRoleFilter:
    """获取或创建全局说话角色过滤器实例（线程安全，双重检查锁）"""
    global _filter_instance
    if _filter_instance is None:
        with _filter_lock:
            if _filter_instance is None:
                _filter_instance = SpeakerRoleFilter(
                    semantic_ranker=semantic_ranker,
                    l2_threshold=l2_threshold,
                )
    return _filter_instance


def reset_speaker_role_filter() -> None:
    """重置全局说话角色过滤器实例，用于测试或重新初始化"""
    global _filter_instance
    with _filter_lock:
        if _filter_instance is not None:
            _filter_instance._dialogue_entities = set()
            _filter_instance._entity_scene_count = {}
        _filter_instance = None
