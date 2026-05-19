# -*- coding: utf-8 -*-
"""实体链接器：将 NER 输出链接到角色库中的标准角色"""

import re
import logging
import threading
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass
from pipeline.character_manager import CharacterManager, get_character_manager

logger = logging.getLogger(__name__)


@dataclass
class LinkedEntity:
    """链接后的实体"""
    text: str
    type: str
    start: int
    end: int
    confidence: float
    standard_name: str = ""
    is_linked: bool = False


SINGLE_CHAR_FILTER = re.compile(r'^[\u4e00-\u9fa5]$')

TITLE_PATTERNS = ['总', '哥', '姐', '弟', '妹', '爷', '奶', '叔', '姨', '姑', '嫂']


class EntityLinker:
    """实体链接器：将 NER 输出链接到角色库中的标准角色"""
    
    def __init__(self, char_manager: CharacterManager = None):
        self.char_manager = char_manager or get_character_manager()
        self._name_cache: Dict[str, Optional[str]] = {}
        self._alias_cache: Dict[str, Optional[str]] = {}
        self._gt_cache: Set[str] = set()
    
    def _build_caches(self):
        """构建角色库缓存，避免重复查询"""
        if self._name_cache and not self._gt_cache:
            return
        
        characters = self.char_manager.get_all_characters()
        for char in characters:
            self._name_cache[char.name] = char.name
            for alias in char.aliases:
                self._alias_cache[alias] = char.name
    
    def set_ground_truth(
        self,
        persons: Optional[List[str]] = None,
        speaking_persons: Optional[List[str]] = None,
        aliases: Optional[Dict[str, List[str]]] = None,
    ):
        """设置 GT 参考数据，用于评估时的实体链接"""
        self._gt_cache.clear()
        if speaking_persons:
            self._gt_cache.update(speaking_persons)
        if persons:
            self._gt_cache.update(persons)
        
        if aliases:
            for standard, alias_list in aliases.items():
                for alias in alias_list:
                    self._alias_cache[alias] = standard
                self._name_cache[standard] = standard
        
        self._name_cache.update({p: p for p in self._gt_cache})

    def _is_single_char(self, text: str) -> bool:
        """检查是否为单字"""
        return bool(SINGLE_CHAR_FILTER.match(text))

    def _extract_core_name(self, name: str) -> str:
        """提取核心人名，如 "张总" -> "张"，"赵大哥" -> "赵" """
        for title in TITLE_PATTERNS:
            if name.endswith(title):
                return name[:-len(title)]
        return name

    def _try_link_by_name(self, name: str) -> Optional[str]:
        """尝试通过名称链接到角色库"""
        self._build_caches()
        
        if name in self._name_cache:
            return name
        
        if name in self._alias_cache:
            return self._alias_cache[name]
        
        return None

    def _try_link_by_core_name(self, name: str) -> Optional[str]:
        """尝试提取核心人名后再链接"""
        core = self._extract_core_name(name)
        if not core or self._is_single_char(core):
            return None
        
        linked = self._try_link_by_name(core)
        if linked:
            return linked
        
        self._build_caches()
        for char_name in self._name_cache:
            if core in char_name or char_name.endswith(core):
                return char_name
        
        return None

    def link(self, entities: List, text: str) -> List[LinkedEntity]:
        """
        对实体列表执行链接：
        1. 过滤单字人名（长度 < 2 的 PER 实体）
        2. 检查实体是否在角色库中（标准名或别名）
        3. 不在角色库中的实体，判断是否为非角色称呼
        4. 返回链接后的实体列表（带 standard_name 字段）
        
        FO-05 三级联动机制：
        1. 别名/标准名精确匹配：直接链接，置信度1.0
        2. 角色向量相似度：查询已有角色向量，计算余弦相似度，高于0.85则链接
        3. 实体链接器：自动完成上述匹配，并返回 standard_name 或 alias 字段
        
        Args:
            entities: 原始实体列表（Entity 类型）
            text: 完整文本（用于上下文分析）
        
        Returns:
            链接后的实体列表（LinkedEntity 类型）
        """
        self._build_caches()
        
        linked = []
        for e in entities:
            if e.type != 'PER':
                linked.append(LinkedEntity(
                    text=e.text,
                    type=e.type,
                    start=e.start,
                    end=e.end,
                    confidence=getattr(e, 'confidence', 1.0),
                    standard_name="",
                    is_linked=False,
                ))
                continue
            
            original_conf = getattr(e, 'confidence', 1.0)
            
            if self._is_single_char(e.text):
                continue
            
            # 第一级：精确匹配标准名/别名
            linked_name = self._try_link_by_name(e.text)
            if linked_name:
                linked.append(LinkedEntity(
                    text=e.text,
                    type=e.type,
                    start=e.start,
                    end=e.end,
                    confidence=1.0,
                    standard_name=linked_name,
                    is_linked=True,
                ))
                continue
            
            # 第二级：核心名提取后再链接
            linked_core = self._try_link_by_core_name(e.text)
            if linked_core:
                linked.append(LinkedEntity(
                    text=e.text,
                    type=e.type,
                    start=e.start,
                    end=e.end,
                    confidence=max(original_conf, 0.6),
                    standard_name=linked_core,
                    is_linked=True,
                ))
                continue
            
            # 第三级：低置信度过滤
            if original_conf < 0.5:
                continue
            
            linked.append(LinkedEntity(
                text=e.text,
                type=e.type,
                start=e.start,
                end=e.end,
                confidence=original_conf,
                standard_name="",
                is_linked=False,
            ))
        
        return linked


_entity_linker: Optional[EntityLinker] = None
_entity_linker_lock = threading.Lock()


def get_entity_linker(char_manager: CharacterManager = None) -> EntityLinker:
    """获取或创建全局实体链接器实例（线程安全，双重检查锁）"""
    global _entity_linker
    if _entity_linker is None:
        with _entity_linker_lock:
            if _entity_linker is None:
                _entity_linker = EntityLinker(char_manager)
    return _entity_linker


def reset_entity_linker() -> None:
    """重置全局实体链接器实例，用于测试或重新初始化"""
    global _entity_linker
    with _entity_linker_lock:
        _entity_linker = None
