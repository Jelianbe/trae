# -*- coding: utf-8 -*-
"""代词消解器：将"他/她/它"等代词解析为具体角色

设计原则：
1. 代词消解基于就近原则（local window）和性别匹配
2. PRONOUNS 是封闭集合（中文人称代词有限）
"""

import re
import logging
from typing import List, Optional, Tuple, Dict

logger = logging.getLogger(__name__)


# 人称代词集合（封闭集合）
PRONOUNS = {
    '他': 'male',
    '她': 'female',
    '它': 'neutral',
    '他们': 'male_plural',
    '她们': 'female_plural',
    '它们': 'neutral_plural',
    '其': 'neutral',
    '此人': 'neutral',
}


class PronounResolver:
    """代词消解器"""

    def __init__(self, char_manager):
        self.char_manager = char_manager

    def resolve(self, text: str) -> List[Tuple[str, str, float]]:
        """从文本中解析代词候选
        
        Returns:
            List of (name, reason, confidence)
        """
        candidates = []

        for pronoun, gender in PRONOUNS.items():
            if pronoun in text:
                resolved = self._resolve_single(pronoun, gender, text)
                if resolved:
                    candidates.append(resolved)

        return candidates

    def resolve_by_pronoun(self, pronoun: str) -> Optional[str]:
        """通过代词获取性别
        
        Returns:
            'male' / 'female' / 'neutral' / None
        """
        return PRONOUNS.get(pronoun)

    def resolve_in_local_window(self, gender: str, recent_speakers: List[str],
                                character_activity: Optional[Dict[str, int]] = None) -> Optional:
        """在局部窗口内解析代词
        
        改进（T-007）：
        1. 扩大窗口：5 → 10
        2. 增加活跃度权重：最近发言的角色获得更高优先级
        
        Args:
            gender: 代词性别
            recent_speakers: 最近说话人列表
            character_activity: 角色活跃度计数字典（可选）
        
        Returns:
            MatchResult or None
        """
        from pipeline.speaker_matcher import MatchResult

        if not recent_speakers:
            return None

        # 窗口扩大：5 → 10
        window_size = 10
        window_speakers = recent_speakers[-window_size:]
        
        # 找出所有性别匹配的候选
        gender_matched = []
        for idx, speaker_name in enumerate(reversed(window_speakers)):
            char = self.char_manager.get_character_by_name(speaker_name)
            if char and char.gender == gender:
                # 计算位置权重（越近越高）
                position_score = 1.0 - (idx / len(window_speakers)) if window_speakers else 0.5
                
                # 计算活跃度权重（如果有）
                activity_score = 0.0
                if character_activity:
                    activity_count = character_activity.get(char.id, 0)
                    activity_score = min(activity_count * 0.05, 0.2)  # 最多+0.2
                
                combined_score = position_score + activity_score
                gender_matched.append((char, combined_score))
        
        if not gender_matched:
            return None
        
        # 选择得分最高的角色
        best_char, best_score = max(gender_matched, key=lambda x: x[1])
        
        # 置信度计算：基础0.85 + 得分加成
        confidence = min(0.85 + best_score * 0.1, 0.95)
        
        return MatchResult(
            character=best_char,
            confidence=confidence,
            match_type='pronoun_local_window'
        )

    def _resolve_single(self, pronoun: str, gender: str, text: str) -> Optional[Tuple[str, str, float]]:
        """解析单个代词"""
        if gender == 'male':
            return (f'代词_男性:{pronoun}', '代词消解', 0.50)
        elif gender == 'female':
            return (f'代词_女性:{pronoun}', '代词消解', 0.50)
        else:
            return (f'代词_未知:{pronoun}', '代词消解', 0.30)
