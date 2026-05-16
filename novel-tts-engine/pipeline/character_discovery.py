# -*- coding: utf-8 -*-
"""角色发现引擎：从文本中发现并临时注册候选角色。

用途：在无预注册角色的冷启动场景下，从文本中提取候选角色名并临时注册，
      提高系统的自动发现能力。

设计原则：
  1. 预处理模式：在 PipelineRunner 处理每个章节之前调用
  2. 临时角色：通过 is_temp=True 标记，不影响正式角色
  3. 去重：不重复注册已存在的角色
  4. 可配置：可通过环境变量 ENABLE_DISCOVERY=false 关闭
"""

import logging
from typing import List, Set, Optional

from pipeline.character_manager import CharacterManager, Character
from pipeline.pattern_extractor import extract_candidates, CHARACTER_BLACKLIST, FANTASY_TITLE_SUFFIXES
from utils.config import TEMP_CHARACTER_CONFIDENCE_FACTOR

logger = logging.getLogger(__name__)


class CharacterDiscoveryEngine:
    """角色发现引擎。
    
    从文本中提取候选角色名，过滤黑名单，归一化，去重，然后临时注册。
    """
    
    def __init__(self, char_manager: CharacterManager):
        self.char_manager = char_manager
        self._discovered_cache: Set[str] = set()
    
    def discover_from_chapter(
        self,
        chapter_text: str,
        chapter_id: int,
        project_id: str
    ) -> List[Character]:
        """从章节文本中发现并注册临时角色。
        
        Args:
            chapter_text: 章节文本内容
            chapter_id: 章节 ID
            project_id: 项目 ID
            
        Returns:
            新注册的临时角色列表
        """
        if not chapter_text or not project_id:
            return []
        
        # 提取候选
        candidates = extract_candidates(chapter_text)
        
        # 过滤和注册
        new_characters = []
        for candidate in candidates:
            name = candidate['name']
            
            # 黑名单过滤
            if name in CHARACTER_BLACKLIST:
                logger.debug(f"角色发现：黑名单过滤 '{name}'")
                continue
            
            # 归一化（去修饰语、剥离头衔）
            normalized_name = self._normalize_name(name)
            if not normalized_name:
                continue
            
            # 检查是否已存在（包括已发现的临时角色）
            if normalized_name in self._discovered_cache:
                continue
            
            # 检查角色库是否已有
            existing = self.char_manager.get_character_by_name(normalized_name, project_id)
            if existing:
                self._discovered_cache.add(normalized_name)
                continue
            
            # 注册临时角色
            try:
                char = self.char_manager.add_character(
                    name=normalized_name,
                    project_id=project_id,
                    is_temp=True,
                    temp_confidence=candidate['confidence'],
                    first_appearance=chapter_id
                )
                if char:
                    self._discovered_cache.add(normalized_name)
                    new_characters.append(char)
                    logger.debug(f"角色发现：注册临时角色 '{normalized_name}' (置信度: {candidate['confidence']:.2f})")
            except Exception as e:
                logger.warning(f"角色发现：注册临时角色失败 '{normalized_name}': {e}")
        
        logger.info(f"角色发现：章节 {chapter_id} 发现 {len(new_characters)} 个新临时角色")
        return new_characters
    
    def _normalize_name(self, name: str) -> Optional[str]:
        """归一化角色名。
        
        策略：
          1. 去除前后空白
          2. 剥离常见头衔后缀（复用 FANTASY_TITLE_SUFFIXES），保留核心人名
          3. 对于"姓+职位"模式，保留完整形式（如"赵总监"）
          4. 过滤长度异常的（<2 或 >6 汉字）
        
        Args:
            name: 原始候选名
            
        Returns:
            归一化后的名称，如果不合法则返回 None
        """
        if not name:
            return None
        
        name = name.strip()
        
        # 长度校验
        cn_chars = [c for c in name if '\u4e00' <= c <= '\u9fff']
        if len(cn_chars) < 2 or len(cn_chars) > 6:
            return None
        
        # 剥离头衔后缀（复用 pattern_extractor 中的封闭集）
        for title in FANTASY_TITLE_SUFFIXES:
            if name.endswith(title) and len(name) > len(title):
                core_name = name[:-len(title)]
                # 检查核心名长度是否合理（2-3 汉字）
                core_cn = [c for c in core_name if '\u4e00' <= c <= '\u9fff']
                if 2 <= len(core_cn) <= 3:
                    logger.debug(f"角色归一化：'{name}' → '{core_name}'")
                    return core_name
        
        return name
    
    def reset_cache(self):
        """重置发现缓存（用于新章节或新项目）。"""
        self._discovered_cache.clear()
