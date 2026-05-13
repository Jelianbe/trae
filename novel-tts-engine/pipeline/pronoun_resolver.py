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
        return PRONOUNS.get(pronoun)

    def resolve_in_local_window(self, gender: str, recent_speakers: List[str],
                                character_activity: Optional[Dict[str, int]] = None,
                                recent_mentions: Optional[List[str]] = None,
                                context_before: Optional[str] = None) -> Optional:
        """在局部窗口内解析代词

        增强：同时考虑最近说话人、最近被提及的角色，以及主语位置加权

        Args:
            gender: 代词性别
            recent_speakers: 最近说话人列表
            character_activity: 角色活跃度计数字典（可选）
            recent_mentions: 最近被提及的角色列表（可选）
            context_before: 对话前的旁白文本（用于主语/宾语位置判断）

        Returns:
            MatchResult or None
        """
        from pipeline.speaker_matcher import MatchResult

        candidates = []

        # 从最近说话人中找性别匹配的（优先级高）
        if recent_speakers:
            window_size = 10
            window_speakers = recent_speakers[-window_size:]

            for idx, speaker_name in enumerate(reversed(window_speakers)):
                char = self.char_manager.get_character_by_name(speaker_name)
                if char and char.gender == gender:
                    position_score = 1.0 - (idx / len(window_speakers)) if window_speakers else 0.5
                    activity_score = 0.0
                    if character_activity:
                        activity_count = character_activity.get(char.id, 0)
                        activity_score = min(activity_count * 0.05, 0.2)

                    # P3 新增：主语位置加权
                    syntax_bonus = 0.0
                    if context_before:
                        if self._is_subject_position(speaker_name, context_before):
                            syntax_bonus = 0.15
                        elif self._is_object_position(speaker_name, context_before):
                            syntax_bonus = -0.10

                    combined_score = position_score + activity_score + syntax_bonus
                    candidates.append((char, combined_score))

        # 从最近被提及的角色中找性别匹配的
        if recent_mentions:
            for idx, mentioned_name in enumerate(reversed(recent_mentions[-10:])):
                char = self.char_manager.get_character_by_name(mentioned_name)
                if char and char.gender == gender:
                    if not any(c.name == char.name for c, _ in candidates):
                        position_score = 1.0 - (idx / min(len(recent_mentions), 10)) if recent_mentions else 0.5
                        activity_score = 0.0
                        if character_activity:
                            activity_count = character_activity.get(char.id, 0)
                            activity_score = min(activity_count * 0.03, 0.1)

                        syntax_bonus = 0.0
                        if context_before:
                            if self._is_subject_position(mentioned_name, context_before):
                                syntax_bonus = 0.15
                            elif self._is_object_position(mentioned_name, context_before):
                                syntax_bonus = -0.10

                        combined_score = position_score + activity_score - 0.1 + syntax_bonus
                        candidates.append((char, combined_score))

        if not candidates:
            return None

        best_char, best_score = max(candidates, key=lambda x: x[1])
        confidence = min(0.85 + best_score * 0.1, 0.95)

        return MatchResult(
            character=best_char,
            confidence=confidence,
            match_type='pronoun_local_window'
        )

    def _is_subject_position(self, name: str, context: str) -> bool:
        """判断实体是否位于主语位置。

        启发式规则：
        1. 显式提示动词前最近的名词（正则匹配 {实体}.*[说道问喊叫]）
        2. 句首实体（句号或开头后的第一个名词性实体）

        来源：基于错误案例分析（P7、P28 等代词消解错误案例）
        边界：仅判断主语/宾语位置，不处理复杂句法
        更新日期：2026-05-10
        维护者：P3 代词消解修复方案
        """
        # 规则1：提示动词前的实体
        speech_verbs = '道说问喊叫呼唤喝'
        pattern = rf'{re.escape(name)}[^{speech_verbs}]{{0,10}}[{speech_verbs}]'
        if re.search(pattern, context):
            return True

        # 规则2：句首实体
        sentences = re.split(r'[。！？\n]', context)
        for sent in sentences:
            sent = sent.strip()
            if sent.startswith(name):
                return True

        return False

    def _is_object_position(self, name: str, context: str) -> bool:
        """判断实体是否位于宾语位置。

        启发式规则：实体紧邻"对/向/给/把/看"等介词/动词后
        """
        # 介词宾语
        prepositions = '对向给把'
        pattern = rf'[{re.escape(prepositions)}]{re.escape(name)}'
        if re.search(pattern, context):
            return True

        # 动词宾语（看了 X、打了 X、问了 X）
        verbs = '看打问叫喊'
        pattern = rf'[{re.escape(verbs)}]了{re.escape(name)}'
        if re.search(pattern, context):
            return True

        return False

    def _resolve_single(self, pronoun: str, gender: str, text: str) -> Optional[Tuple[str, str, float]]:
        """解析单个代词"""
        if gender == 'male':
            return (f'代词_男性:{pronoun}', '代词消解', 0.50)
        elif gender == 'female':
            return (f'代词_女性:{pronoun}', '代词消解', 0.50)
        else:
            return (f'代词_未知:{pronoun}', '代词消解', 0.30)
