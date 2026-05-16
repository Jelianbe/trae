# -*- coding: utf-8 -*-
"""缓存管理器：专门负责结果缓存的管理"""

import logging
from collections import OrderedDict
from typing import List, Optional, TypeVar

from utils.config import MAX_RESULT_CACHE_SIZE

logger = logging.getLogger(__name__)


T = TypeVar("T")


class CacheManager:
    """缓存管理器：专门负责结果缓存的管理，支持LRU淘汰策略"""

    def __init__(self, max_size: int = MAX_RESULT_CACHE_SIZE):
        self._cache: "OrderedDict[str, List[T]]" = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> Optional[List[T]]:
        """从缓存获取结果，命中时更新访问顺序"""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: List[T]):
        """添加结果到缓存，超过容量时淘汰最旧的"""
        if key in self._cache:
            del self._cache[key]
        self._cache[key] = value
        self._evict_if_needed()

    def has(self, key: str) -> bool:
        """检查缓存中是否存在指定key"""
        return key in self._cache

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def size(self) -> int:
        """获取当前缓存大小"""
        return len(self._cache)

    def _evict_if_needed(self):
        """超过容量时淘汰最旧的"""
        while len(self._cache) > self._max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"缓存已满，淘汰最旧记录: {evicted_key}")
