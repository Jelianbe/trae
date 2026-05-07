# -*- coding: utf-8 -*-
"""自称词推断器：通过自称词（我、朕、本座等）推断说话人身份

设计原则：
1. self_reference_map 基于中文谦辞体系，是封闭集合
2. 上限约束：此集合不应超过15条，超出必须重构为统计方法

注意：
- 中文谦辞/尊称体系是封闭的，当前9条已覆盖绝大多数场景
- 新增条目需有明确的语言学依据，不得基于个案补丁
"""

import re
import logging
from typing import List, Optional, Tuple, Dict

logger = logging.getLogger(__name__)


# 自称词映射（约束：上限15条，当前9条）
# 基于中文谦辞体系——说话人用来自我指称的词汇
SELF_REFERENCE_MAP: Dict[str, str] = {
    '我': 'first_person',
    '吾': 'first_person_classical',
    '朕': 'first_person_emperor',
    '本座': 'first_person_cultivation',
    '本王': 'first_person_king',
    '老夫': 'first_person_elder_male',
    '老身': 'first_person_elder_female',
    '奴家': 'first_person_humble_female',
    '妾身': 'first_person_concubine',
}


class SelfReferenceInferrer:
    """自称词推断器"""

    def __init__(self, char_manager):
        self.char_manager = char_manager

    def infer(self, text: str, context: str = '') -> List[Tuple[str, str, float]]:
        """通过自称词推断说话人身份
        
        Returns:
            List of (name, reason, confidence)
        """
        candidates = []

        for ref_word, ref_type in SELF_REFERENCE_MAP.items():
            if ref_word in text:
                # 有自称词时，尝试从上下文中找到最近的已知角色
                # 策略：自称词本身不产生新角色名，但提供性别/身份线索
                # 如果上下文中只有一个已知角色，大概率就是该角色
                known_chars = self._find_nearby_characters(context)
                if known_chars:
                    for char in known_chars[:1]:  # 只取最可能的一个
                        candidates.append((char.name, f'自称词:{ref_word}→{char.name}', 0.75))
                else:
                    # 无已知角色匹配时，返回"未知_角色类型"而非强制匹配
                    role_type = self._infer_role_type_from_self_ref(ref_type)
                    candidates.append((f'未知_{role_type}', f'自称词:{ref_word}', 0.40))

        return candidates

    def infer_gender_from_context(self, name: str, context: str) -> str:
        """从上下文中推断角色性别"""
        male_indicators = ['他', '男子', '男人', '公子', '陛下', '王爷', '少爷',
                          '老夫', '朕', '本王', '本座']
        female_indicators = ['她', '女子', '女人', '小姐', '夫人', '姑娘', '娘娘',
                            '奴家', '妾身', '姑娘', '妹妹', '姐姐']

        male_count = sum(1 for w in male_indicators if w in context)
        female_count = sum(1 for w in female_indicators if w in context)

        if male_count > female_count:
            return 'male'
        elif female_count > male_count:
            return 'female'
        else:
            return 'unknown'

    def _find_nearby_characters(self, context: str) -> list:
        """在上下文中找到已知角色"""
        all_chars = self.char_manager.get_all_characters()
        found = []
        for char in all_chars:
            if char.name in context:
                found.append(char)
                continue
            for alias in char.aliases:
                if alias in context:
                    found.append(char)
                    break
        return found

    def _infer_role_type_from_self_ref(self, ref_type: str) -> str:
        """从自称词类型推断角色类型"""
        type_map = {
            'first_person_emperor': '帝王',
            'first_person_cultivation': '修士',
            'first_person_king': '王爷',
            'first_person_elder_male': '老者',
            'first_person_elder_female': '老妇',
            'first_person_humble_female': '女子',
            'first_person_concubine': '妾室',
            'first_person_classical': '古人',
            'first_person': '角色',
        }
        return type_map.get(ref_type, '角色')
