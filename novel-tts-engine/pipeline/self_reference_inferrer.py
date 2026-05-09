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


# 自称词映射
#
# 用途：通过自称词（我、朕、本座等）推断说话人身份
# 来源：汉语称谓体系——古代官职谦辞与通用谦辞
#   - "朕"：秦始皇统一后的帝王自称，来源《史记·秦始皇本纪》
#   - "本座"：修仙/玄幻文通用自称，来源网文惯例（非历史文献）
#   - "本王"：诸侯王自称，来源《礼记》称谓体系
#   - "老夫/老身"：年长者自称，来源《论语》"老者安之"及后世白话小说
#   - "奴家/妾身"：女性谦辞，来源宋元话本及明清小说
#   - "吾"：文言第一人称，来源《论语》《孟子》等先秦文献
#   - "我"：现代汉语第一人称，来源通用
# 边界：仅包含有明确语言学/文献依据的谦辞，不包含方言或特定作品造词
#       不应往里加：网文特定角色自称（如"本尊"、"吾乃"等变体）
# 硬性约束：上限15条，当前9条。超出必须重构为统计方法，不得继续追加
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

# 上限约束检查
assert len(SELF_REFERENCE_MAP) <= 15, (
    f"SELF_REFERENCE_MAP 超出15条上限（当前{len(SELF_REFERENCE_MAP)}条），"
    "请审查是否越界，或重构为统计方法"
)


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
                known_chars = self._find_nearby_characters(context)
                if known_chars:
                    for char in known_chars[:1]:
                        candidates.append((char.name, f'自称词:{ref_word}→{char.name}', 0.75))
                else:
                    # 不确定时直接返回"未知"，不追加身份类型后缀
                    # 理由：身份推断（如"末将"→武将）本质上还是猜测，
                    # 错误的身份标签比信息不足更危险
                    candidates.append(('未知', f'自称词:{ref_word}', 0.40))

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
