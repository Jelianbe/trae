# -*- coding: utf-8 -*-
"""情绪标注器：规则标注六种基础情绪"""

import re
from typing import Dict, Optional

EMOTION_PATTERNS: Dict[str, list] = {
    "joy": [
        r"笑", r"开心", r"高兴", r"喜悦", r"欢快", r"欢喜", r"愉快",
        r"哈哈", r"呵呵", r"嘻嘻", r"大笑", r"微笑", r"欢笑",
        r"太好了", r"太棒了", r"好极了",
    ],
    "anger": [
        r"怒", r"愤怒", r"生气", r"大怒", r"发火", r"咆哮", r"怒吼",
        r"可恶", r"混蛋", r"放肆", r"岂有此理", r"气死",
    ],
    "sadness": [
        r"哭", r"悲伤", r"难过", r"伤心", r"流泪", r"泪水", r"痛哭",
        r"唉", r"呜", r"呜呜", r"惨", r"可怜", r"心疼",
    ],
    "surprise": [
        r"惊讶", r"震惊", r"吃惊", r"吃惊", r"意外", r"竟然", r"居然",
        r"什么", r"不会吧", r"怎么可能", r"天哪", r"哇",
    ],
    "fear": [
        r"害怕", r"恐惧", r"惊吓", r"惊恐", r"吓", r"慌", r"紧张",
        r"危险", r"糟糕", r"不妙", r"恐怖", r"可怕",
    ],
}

DEFAULT_EMOTION = "neutral"


class EmotionTagger:
    """情绪标注器：基于规则的情绪识别"""
    
    def tag(self, text: str, speaker: str = None) -> str:
        """
        对文本进行情绪标注。
        
        Args:
            text: 文本内容
            speaker: 说话人（可选，用于上下文记忆）
        
        Returns:
            情绪标签：joy/anger/sadness/surprise/fear/neutral
        """
        if not text:
            return DEFAULT_EMOTION
        
        best_emotion = DEFAULT_EMOTION
        best_count = 0
        
        for emotion, patterns in EMOTION_PATTERNS.items():
            count = 0
            for pattern in patterns:
                if re.search(pattern, text):
                    count += 1
            if count > best_count:
                best_count = count
                best_emotion = emotion
        
        return best_emotion


_emotion_tagger: Optional[EmotionTagger] = None


def get_emotion_tagger() -> EmotionTagger:
    """获取或创建全局情绪标注器实例"""
    global _emotion_tagger
    if _emotion_tagger is None:
        _emotion_tagger = EmotionTagger()
    return _emotion_tagger
