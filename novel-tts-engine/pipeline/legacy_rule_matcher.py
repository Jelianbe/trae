# -*- coding: utf-8 -*-
"""LegacyRuleMatcher：基于规则的说话人匹配器（原 SpeakerMatcher）。

封装了项目前两个月积累的全部规则库，包括：
- 6 策略级联匹配（上下文推理 → 提示词 → 代词 → 角色库 → 语义 → 触发词）
- HanLP NLP 集成与优雅降级
- 冷启动回填机制
- 角色活跃度追踪

设计目的：即使未来引入 LLM 或依存句法分析，此模块仍可作为降级（Fallback）选项保留。
"""

from pipeline.speaker_matcher import (
    SpeakerMatcher,
    DialogueContext,
    MatchResult,
    detect_group_speaker,
    get_speaker_matcher,
    GROUP_NUMBER_PATTERN,
    CROWD_INDICATOR_WORDS,
    CROWD_ACTION_WORDS,
)
from pipeline.speaker_matcher_interface import AbstractSpeakerMatcher

# SpeakerMatcher 已经是 AbstractSpeakerMatcher 的子类
# LegacyRuleMatcher 是其别名，保持完全兼容
LegacyRuleMatcher = SpeakerMatcher


def get_legacy_rule_matcher() -> LegacyRuleMatcher:
    """获取全局 LegacyRuleMatcher 实例（向后兼容 get_speaker_matcher）。"""
    return get_speaker_matcher()


__all__ = [
    'LegacyRuleMatcher',
    'DialogueContext',
    'MatchResult',
    'detect_group_speaker',
    'get_legacy_rule_matcher',
    'get_speaker_matcher',  # 向后兼容
    'GROUP_NUMBER_PATTERN',
    'CROWD_INDICATOR_WORDS',
    'CROWD_ACTION_WORDS',
    'AbstractSpeakerMatcher',
]
