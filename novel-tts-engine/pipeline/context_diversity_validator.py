# -*- coding: utf-8 -*-
"""
ContextDiversityValidator - 上下文多样性实体验证器

对NER实体列表进行二次过滤，自动调整置信度：
- 过滤掉"固定搭配中的高频片段"（如"青龙帮"中的"青龙"）
- 保留"多种上下文中出现的真实实体"（如"林轩"、"艾德温"）
- 降低低频噪声实体的置信度
"""
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import re
from collections import defaultdict


@dataclass
class Entity:
    text: str
    type: str  # PER, LOC, ORG
    start: int
    end: int
    confidence: float = 1.0


class ContextDiversityValidator:
    """
    基于上下文多样性的实体验证器
    
    核心判定逻辑：
    - 总出现次数 < 3 → 降为低置信度（0.3），疑似噪声
    - 总出现次数 ≥ 3，右邻字种类 ≤ 1 → 极可能为固定搭配片段，降为极低置信度（0.2）
    - 总出现次数 ≥ 3，右邻字种类 ≥ 2 → 维持原置信度
    - 总出现次数 ≥ 5，右邻字种类 ≥ 3，且章节分布 ≥ 2 → 提升为高置信度（最低0.8）
    """
    
    def __init__(
        self,
        min_occurrences: int = 3,
        high_conf_threshold: int = 5,
        diversity_threshold: int = 2,
        whitelist: Optional[Set[str]] = None,
        mode: str = 'general',  # 'general' 或 'speaker_role'
    ):
        self.mode = mode
        
        # 根据模式调整阈值
        if mode == 'speaker_role':
            # 说话角色模式：阈值降低，因为说话角色信号更强
            self.min_occurrences = 2        # 说话角色出现2次即可
            self.high_conf_threshold = 3     # 3次即认为高频
        else:
            self.min_occurrences = min_occurrences
            self.high_conf_threshold = high_conf_threshold
        
        self.diversity_threshold = diversity_threshold
        self.whitelist = whitelist or set()  # 白名单实体（不受低频降级影响）
    
    def validate(
        self,
        entities: List[Entity],
        full_text: str,
        chapters: Optional[List[Dict]] = None,
    ) -> List[Entity]:
        """
        主入口：对实体列表进行上下文多样性验证，返回调整后的实体列表
        
        Args:
            entities: 原始实体列表（来自nlp_basics）
            full_text: 完整文本
            chapters: 章节信息列表（可选），用于计算章节分布
            
        Returns:
            调整置信度后的实体列表
        """
        # 步骤1：为每个唯一实体文本收集上下文统计
        stats = self._collect_context_stats(entities, full_text, chapters)
        
        # 步骤2：根据多样性调整置信度
        validated = []
        for entity in entities:
            key = entity.text
            if key in stats:
                new_conf = self._calculate_confidence(entity, stats[key])
                entity.confidence = new_conf
            validated.append(entity)
        
        return validated
    
    def _collect_context_stats(
        self,
        entities: List[Entity],
        full_text: str,
        chapters: Optional[List[Dict]] = None,
    ) -> Dict[str, Dict]:
        """
        收集每个实体文本的出现次数、右邻字集合、所在章节（如有）
        
        性能优化：只对唯一实体文本进行全文扫描，避免重复搜索
        """
        # 获取唯一实体文本
        unique_texts = set(e.text for e in entities)
        
        stats = {}
        for text in unique_texts:
            stats[text] = {
                'occurrences': 0,
                'right_neighbors': set(),
                'chapter_ids': set(),
            }
        
        # 对每个唯一文本进行全文扫描
        for text in unique_texts:
            # 使用正则查找所有出现位置（转义特殊字符）
            pattern = re.compile(re.escape(text))
            
            # 收集所有出现位置
            positions = []
            for match in pattern.finditer(full_text):
                start = match.start()
                end = match.end()
                positions.append((start, end))
                
                # 获取右邻字（实体后第1-2个非标点字符）
                right_chars = self._get_right_neighbors(full_text, end)
                stats[text]['right_neighbors'].update(right_chars)
            
            stats[text]['occurrences'] = len(positions)
            
            # 计算章节分布（如果提供了章节信息）
            if chapters:
                for pos_start, pos_end in positions:
                    for chapter_idx, chapter in enumerate(chapters):
                        if chapter.get('start', 0) <= pos_start < chapter.get('end', len(full_text)):
                            stats[text]['chapter_ids'].add(chapter_idx)
                            break
        
        return stats
    
    def _get_right_neighbors(self, text: str, end_pos: int, max_count: int = 2) -> Set[str]:
        """获取实体后的右邻字（非标点字符）"""
        neighbors = set()
        pos = end_pos
        count = 0
        
        while pos < len(text) and count < max_count:
            char = text[pos]
            # 跳过标点和空白字符
            if char not in '，。！？；：""''（）【】《》\n\r\t ':
                neighbors.add(char)
                count += 1
            pos += 1
        
        return neighbors
    
    def _calculate_confidence(self, entity: Entity, stat: Dict) -> float:
        """
        根据上下文多样性计算新置信度
        
        判定逻辑：
        - 白名单实体 → 保持原置信度
        - 总出现次数 < 3 → 0.3（低频噪声）
        - 总出现次数 ≥ 3，右邻字种类 ≤ 1 → 0.2（固定搭配片段）
        - 总出现次数 ≥ 5，右邻字种类 ≥ 3 → max(原置信度, 0.8)（高置信实体）
        - 其他 → 保持原置信度
        """
        # 白名单实体不受影响
        if entity.text in self.whitelist:
            return entity.confidence
        
        occ = stat['occurrences']
        diversity = len(stat['right_neighbors'])
        
        # 低频实体 → 降置信度
        if occ < self.min_occurrences:
            return 0.3
        
        # 固定搭配片段（右邻字种类少）→ 极低置信度
        if occ >= self.min_occurrences and diversity <= 1:
            return 0.2
        
        # 高频高多样实体 → 提升置信度
        if occ >= self.high_conf_threshold and diversity >= self.diversity_threshold:
            return max(entity.confidence, 0.8)
        
        # 其他情况 → 保持原置信度
        return entity.confidence


# ============================================================
# 全局单例
# ============================================================

_validator_instance = None

def get_context_validator(
    min_occurrences: int = 3,
    high_conf_threshold: int = 5,
    diversity_threshold: int = 2,
    whitelist: Optional[Set[str]] = None,
    mode: str = 'general',
) -> ContextDiversityValidator:
    """获取或创建全局上下文验证器实例"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ContextDiversityValidator(
            min_occurrences=min_occurrences,
            high_conf_threshold=high_conf_threshold,
            diversity_threshold=diversity_threshold,
            whitelist=whitelist,
            mode=mode,
        )
    return _validator_instance
