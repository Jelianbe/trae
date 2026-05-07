# -*- coding: utf-8 -*-
"""代词消解器：将"他/她/它"等代词解析为具体角色

设计原则：
1. 代词消解基于就近原则（local window）和性别匹配
2. PRONOUNS 是封闭集合（中文人称代词有限）
"""

import re
import logging
from typing import List, Optional, Tuple

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

    def resolve_in_local_window(self, gender: str, recent_speakers: List[str]) -> Optional:
        """在局部窗口内解析代词
        
        Returns:
            MatchResult or None
        """
        from pipeline.speaker_matcher import MatchResult

        if not recent_speakers:
            return None

        # 从最近的说话人中找性别匹配的
        for speaker_name in reversed(recent_speakers[-5:]):
            char = self.char_manager.get_character_by_name(speaker_name)
            if char and char.gender == gender:
                return MatchResult(
                    character=char,
                    confidence=0.85,
                    match_type='pronoun_local_window'
                )

        return None

    def _resolve_single(self, pronoun: str, gender: str, text: str) -> Optional[Tuple[str, str, float]]:
        """解析单个代词"""
        if gender == 'male':
            return (f'代词_男性:{pronoun}', '代词消解', 0.50)
        elif gender == 'female':
            return (f'代词_女性:{pronoun}', '代词消解', 0.50)
        else:
            return (f'代词_未知:{pronoun}', '代词消解', 0.30)
