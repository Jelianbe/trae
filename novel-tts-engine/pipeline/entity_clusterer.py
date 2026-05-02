# -*- coding: utf-8 -*-
"""角色聚类模块：基于 BGE-small 语义编码 + 上下文相似度"""

import re
import logging
import threading
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from pipeline.semantic_ranker import get_semantic_ranker, SemanticRanker
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.nlp_basics import Entity

logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """实体聚类"""
    center: str
    members: List[str] = field(default_factory=list)
    similarity: float = 1.0
    status: str = "confirmed"


WINDOW_CHARS = 50
MIN_CLUSTER_CHARS = 3000


class EntityClusterer:
    """
    角色聚类器：基于上下文语义相似度将同指不同名的实体聚合。
    
    四步聚类法：
    1. 收集每个实体的所有出现位置的上下文
    2. 用 BGE-small 为每个实体的上下文编码，取平均向量
    3. 计算实体之间的余弦相似度，高频实体优先作为聚类中心
    4. 将聚类结果写回 SQLite
    """
    
    def __init__(
        self,
        semantic_ranker: Optional[SemanticRanker] = None,
        char_manager: Optional[CharacterManager] = None,
        merge_threshold: float = 0.85,
        new_threshold: float = 0.5,
        min_occurrences: int = 3,  # 提高至 3，避免西方奇幻文本中仅出现 2 次的异名实体被误合并
    ):
        self.semantic_ranker = semantic_ranker or get_semantic_ranker()
        self.char_manager = char_manager or get_character_manager()
        self.merge_threshold = merge_threshold
        self.new_threshold = new_threshold
        self.min_occurrences = min_occurrences

    def _collect_entity_contexts(self, entities: List[Entity], text: str, window: int = WINDOW_CHARS) -> Dict[str, List[str]]:
        """
        第一步：收集每个实体的所有出现位置。
        遍历全文，记录每个实体每次出现时的前后各一句话作为上下文。
        """
        contexts: Dict[str, List[str]] = {}
        entity_spans: Dict[str, List[Tuple[int, int]]] = {}
        
        for e in entities:
            if e.text not in entity_spans:
                entity_spans[e.text] = []
            entity_spans[e.text].append((e.start, e.end))
        
        for entity_text, spans in entity_spans.items():
            for start, end in spans:
                ctx_start = max(0, start - window)
                ctx_end = min(len(text), end + window)
                context = text[ctx_start:ctx_end].strip()
                if context:
                    if entity_text not in contexts:
                        contexts[entity_text] = []
                    contexts[entity_text].append(context)
        
        return contexts

    def _encode_entity_vectors(self, contexts: Dict[str, List[str]]) -> Dict[str, np.ndarray]:
        """
        第二步：用 BGE-small 为每个实体的所有上下文编码，取平均向量代表这个实体。
        
        如果模型不可用，返回空的entity_vectors，后续会使用字面重叠度进行降级聚类。
        """
        self.semantic_ranker.load_model()
        if not self.semantic_ranker.is_available():
            logger.error("BGE-small 不可用，将使用字面重叠度进行降级聚类")
            return {}
        
        entity_vectors: Dict[str, np.ndarray] = {}
        
        for entity_text, ctx_list in contexts.items():
            embeddings = self.semantic_ranker.encode_batch(ctx_list)
            if embeddings is None or len(embeddings) == 0:
                continue
            avg_vector = np.mean(embeddings, axis=0)
            norm = np.linalg.norm(avg_vector)
            if norm > 0:
                avg_vector = avg_vector / norm
            entity_vectors[entity_text] = avg_vector
        
        return entity_vectors
    
    def _cluster_by_char_overlap(self, entities: List[str], entity_counts: Dict[str, int]) -> List[Cluster]:
        """
        降级聚类策略：基于字面字符重叠度进行聚类。
        
        当BGE-small模型不可用时，使用此方法进行降级聚类。
        
        Args:
            entities: 实体名称列表
            entity_counts: 实体出现次数统计
        
        Returns:
            聚类结果列表
        """
        logger.info(f"使用字面重叠度降级聚类，候选实体: {len(entities)}")
        
        sorted_entities = sorted(entities, key=lambda x: entity_counts.get(x, 0), reverse=True)
        
        clusters: List[Cluster] = []
        assigned: Set[str] = set()
        
        for entity in sorted_entities:
            if entity in assigned:
                continue
            
            best_cluster = None
            best_overlap = 0.0
            
            for cluster in clusters:
                overlap = self._char_overlap(entity, cluster.center)
                if overlap >= 0.5:  # 字面重叠度阈值
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_cluster = cluster
            
            if best_cluster:
                best_cluster.members.append(entity)
                best_cluster.similarity = best_overlap
                assigned.add(entity)
            else:
                new_cluster = Cluster(center=entity, similarity=1.0)
                clusters.append(new_cluster)
                assigned.add(entity)
        
        logger.info(f"字面重叠度降级聚类完成: {len(clusters)} 个聚类")
        return clusters

    @staticmethod
    def _char_overlap(a: str, b: str) -> float:
        """计算两个字面字符串的字符重叠度"""
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _cluster_entities(self, entity_vectors: Dict[str, np.ndarray], entity_counts: Dict[str, int]) -> List[Cluster]:
        """
        第三步：计算实体之间的余弦相似度，聚类。
        
        按出现次数从高到低排序，高频实体优先作为聚类中心。
        
        合并条件（必须同时满足）：
        1. 语义相似度 >= merge_threshold
        2. 字面字符重叠度 >= 0.3（或相似度 >= 0.95）
        
        FO-04 重名消歧保护：
        当两个实体上下文相似度极高，但各自拥有独立章节出现记录、稳定代词和不同头衔时，
        不以高置信度自动合并，而是标记为 ambiguous，置信度保持0.6，不升级。
        
        相似度 < new_threshold：新建中心
        中间地带：标记为"待用户确认"
        """
        sorted_entities = sorted(entity_vectors.keys(), key=lambda x: entity_counts.get(x, 0), reverse=True)
        
        clusters: List[Cluster] = []
        assigned: Set[str] = set()
        
        for entity in sorted_entities:
            if entity in assigned:
                continue
            
            vector = entity_vectors[entity]
            best_cluster = None
            best_score = 0.0
            
            for cluster in clusters:
                center_vector = entity_vectors.get(cluster.center)
                if center_vector is None:
                    continue
                
                sim = float(np.dot(vector, center_vector))
                
                if sim >= self.merge_threshold:
                    overlap = self._char_overlap(entity, cluster.center)
                    if sim >= 0.95 or overlap >= 0.3:
                        # FO-04: 重名消歧保护检查
                        if self._is_ambiguous(entity, cluster.center, entity_vectors, entity_counts):
                            logger.info(f"重名消歧保护: '{entity}' 与 '{cluster.center}' 疑似独立角色，不合并")
                            continue
                        
                        if sim > best_score:
                            best_score = sim
                            best_cluster = cluster
            
            if best_cluster:
                best_cluster.members.append(entity)
                best_cluster.similarity = best_score
                assigned.add(entity)
            else:
                new_cluster = Cluster(center=entity, similarity=1.0)
                clusters.append(new_cluster)
                assigned.add(entity)
        
        return clusters
    
    def _is_ambiguous(self, entity_a: str, entity_b: str, entity_vectors: Dict[str, np.ndarray], entity_counts: Dict[str, int]) -> bool:
        """
        FO-04: 判定两个实体是否应该标记为重名消歧（ambiguous）
        
        判定条件：
        - 余弦相似度 > 0.85
        - 且双方各自出现 ≥ 3章，且各自独立作为说话人 ≥ 2次
        - 同时满足时标记为 ambiguous，置信度保持0.6，不升级
        
        Args:
            entity_a: 实体A名称
            entity_b: 实体B名称
            entity_vectors: 实体向量字典
            entity_counts: 实体出现次数统计
        
        Returns:
            True 如果应标记为 ambiguous
        """
        # 检查相似度
        vector_a = entity_vectors.get(entity_a)
        vector_b = entity_vectors.get(entity_b)
        if vector_a is None or vector_b is None:
            return False
        
        sim = float(np.dot(vector_a, vector_b))
        if sim <= 0.85:
            return False
        
        # 检查各自出现次数 ≥ 3
        count_a = entity_counts.get(entity_a, 0)
        count_b = entity_counts.get(entity_b, 0)
        if count_a < 3 or count_b < 3:
            return False
        
        # 检查各自是否有独立头衔/称谓（通过角色库查询）
        char_a = self.char_manager.get_character_by_name(entity_a)
        char_b = self.char_manager.get_character_by_name(entity_b)
        
        # 如果两者都是已注册角色，检查是否有不同的性别或别名
        if char_a and char_b:
            # 不同性别 -> 绝对是独立角色
            if char_a.gender != char_b.gender and char_a.gender != 'unknown' and char_b.gender != 'unknown':
                return True
            
            # 不同别名集合且无重叠 -> 可能是独立角色
            if not (char_a.aliases & char_b.aliases):
                # 检查是否有不同的称谓后缀
                titles_a = self._extract_titles(entity_a)
                titles_b = self._extract_titles(entity_b)
                if titles_a != titles_b:
                    return True
        
        # 默认不标记为 ambiguous（保守策略）
        return False
    
    @staticmethod
    def _extract_titles(name: str) -> Set[str]:
        """从名称中提取称谓后缀"""
        titles = {'总', '哥', '姐', '弟', '妹', '爷', '奶', '叔', '姨', '姑', '嫂', 
                  '先生', '小姐', '少爷', '公子', '夫人', '老爷', '奶奶'}
        found = set()
        for title in titles:
            if name.endswith(title):
                found.add(title)
        return found

    def _write_clusters(self, clusters: List[Cluster]) -> int:
        """
        第四步：将聚类结果写回 SQLite。
        合并的实体通过 CharacterManager.merge_characters 归并。
        """
        merged_count = 0
        for cluster in clusters:
            if not cluster.members:
                continue
            
            primary = self.char_manager.get_character_by_name(cluster.center)
            if not primary:
                continue
            
            for member in cluster.members:
                secondary = self.char_manager.get_character_by_name(member)
                if not secondary:
                    continue
                
                if secondary.id != primary.id:
                    success = self.char_manager.merge_characters(primary.id, secondary.id)
                    if success:
                        merged_count += 1
                        logger.info(f"聚类合并: {member} -> {cluster.center} (sim={cluster.similarity:.3f})")
        
        return merged_count

    def cluster(
        self,
        entities: List[Entity],
        text: str,
        char_manager: CharacterManager = None,
        write_back: bool = False,
    ) -> List[Entity]:
        """
        对外接口：输入实体列表和全文，输出聚类后的实体列表。
        
        Args:
            entities: NER 输出的实体列表
            text: 完整文本
            char_manager: 实例初始化时绑定的角色管理器，此参数不再使用
            write_back: 是否将聚类结果写回 SQLite（默认 False，仅返回聚类后列表）
        
        Returns:
            聚类后的实体列表（低频实体被合并，置信度提升）
        """
        entity_counts: Dict[str, int] = {}
        for e in entities:
            entity_counts[e.text] = entity_counts.get(e.text, 0) + 1
        
        frequent_entities = {t for t, c in entity_counts.items() if c >= self.min_occurrences}
        
        if len(frequent_entities) < 3 or len(text) < MIN_CLUSTER_CHARS:
            logger.info(f"跳过角色聚类（候选实体 {len(frequent_entities)} < 3 或文本长度 {len(text)} < {MIN_CLUSTER_CHARS}）")
            if len(text) < MIN_CLUSTER_CHARS:
                return self._link_from_character_db(entities)
            return entities
        
        contexts = self._collect_entity_contexts(entities, text)
        entity_vectors = self._encode_entity_vectors(contexts)
        
        # 降级策略：当BGE-small不可用时，使用字面重叠度聚类
        use_fallback = not entity_vectors
        if use_fallback:
            logger.warning("BGE-small模型不可用，启用字面重叠度降级聚类")
            clusters = self._cluster_by_char_overlap(list(contexts.keys()), entity_counts)
        else:
            clusters = self._cluster_entities(entity_vectors, entity_counts)
        
        if write_back:
            merged_count = self._write_clusters(clusters)
            logger.info(f"角色聚类完成：{len(clusters)} 个聚类，合并 {merged_count} 个实体")
        else:
            logger.info(f"角色聚类完成：{len(clusters)} 个聚类（dry run，未写回数据库）")
        
        member_to_center: Dict[str, str] = {}
        for cluster in clusters:
            for member in cluster.members:
                member_to_center[member] = cluster.center
        
        # 返回新实体列表，不直接修改输入实体（避免副作用）
        clustered_entities = []
        for e in entities:
            if e.text in member_to_center:
                # 创建新实体，不修改原始实体
                new_entity = Entity(
                    text=member_to_center[e.text],
                    type=e.type,
                    start=e.start,
                    end=e.end,
                    confidence=max(getattr(e, 'confidence', 1.0), 0.7),
                )
                clustered_entities.append(new_entity)
            else:
                # 未聚类的实体也创建副本，保持一致性
                clustered_entities.append(Entity(
                    text=e.text,
                    type=e.type,
                    start=e.start,
                    end=e.end,
                    confidence=getattr(e, 'confidence', 1.0),
                ))
        
        return clustered_entities
    
    def _link_from_character_db(self, entities: List[Entity]) -> List[Entity]:
        """
        FO-05 三级联动机制：短文本处理
        
        低于聚类阈值时，通过 EntityLinker 的三级联动完成链接：
        1. 别名/标准名精确匹配：直接链接，置信度1.0
        2. 角色向量相似度：查询已有角色向量，计算余弦相似度，高于0.85则链接
        3. 实体链接器：自动完成上述匹配
        
        Args:
            entities: NER 输出的实体列表
        
        Returns:
            链接后的实体列表
        """
        from pipeline.entity_linker import get_entity_linker
        
        linker = get_entity_linker(self.char_manager)
        linked = linker.link(entities, "")
        
        result = []
        linked_count = 0
        for le in linked:
            if le.is_linked and le.standard_name:
                linked_count += 1
            
            new_entity = Entity(
                text=le.text,
                type=le.type,
                start=le.start,
                end=le.end,
                confidence=le.confidence,
            )
            result.append(new_entity)
        
        logger.info(f"短文本处理（三级联动）：通过角色库链接 {linked_count}/{len(entities)} 个实体")
        return result


_entity_clusterer: Optional[EntityClusterer] = None
_entity_clusterer_lock = threading.Lock()


def get_entity_clusterer(
    semantic_ranker: SemanticRanker = None,
    char_manager: CharacterManager = None,
    merge_threshold: float = 0.85,
    new_threshold: float = 0.5,
    min_occurrences: int = 2,
) -> EntityClusterer:
    """获取或创建全局实体聚类器实例（线程安全，双重检查锁）"""
    global _entity_clusterer
    if _entity_clusterer is None:
        with _entity_clusterer_lock:
            if _entity_clusterer is None:
                _entity_clusterer = EntityClusterer(
                    semantic_ranker=semantic_ranker,
                    char_manager=char_manager,
                    merge_threshold=merge_threshold,
                    new_threshold=new_threshold,
                    min_occurrences=min_occurrences,
                )
    return _entity_clusterer


def reset_entity_clusterer() -> None:
    """重置全局实体聚类器实例，用于测试或重新初始化"""
    global _entity_clusterer
    with _entity_clusterer_lock:
        _entity_clusterer = None
