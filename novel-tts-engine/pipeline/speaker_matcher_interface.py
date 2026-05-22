# -*- coding: utf-8 -*-
"""说话人匹配器抽象接口。

定义所有说话人匹配实现必须遵守的契约。
无论是基于规则的 LegacyRuleMatcher，还是未来基于 LLM 的 LlmSpeakerMatcher，
都必须实现此接口，以便在 PipelineRunner 中无缝切换。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field


@dataclass
class DialogueContext:
    text: str
    speaker_hint: Optional[str] = None
    prev_speaker: Optional[str] = None
    mentioned_characters: List[str] = field(default_factory=list)
    chapter_id: Optional[int] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    dialogue: Optional[str] = None  # 纯对话原文，不含 prefix/suffix
    prefix_narration: Optional[str] = None  # 纯旁白前缀，已移除[DIALOGUE]占位符


@dataclass
class MatchResult:
    character: object  # Character type from character_manager
    confidence: float
    match_type: str


class AbstractSpeakerMatcher(ABC):
    """说话人匹配器抽象基类。

    所有说话人匹配实现必须继承此类并实现以下方法。
    设计目的：提供统一的切换接口，支持规则系统、LLM 系统之间的降级（Fallback）。
    """

    @abstractmethod
    def analyze_dialogue(self, text: str, chapter_id: int = None) -> List[Tuple[str, Optional[object]]]:
        """分析整章文本，提取所有对话及其说话人。

        Args:
            text: 完整章节文本
            chapter_id: 章节 ID

        Returns:
            [(对话文本, 说话人Character), ...] 列表
        """
        ...

    @abstractmethod
    def get_speaker_for_sentence(self, sentence: str, prev_speaker: str = None,
                                  chapter_id: int = None) -> Tuple[Optional[object], str]:
        """为单个句子匹配说话人。

        Args:
            sentence: 句子文本
            prev_speaker: 上一个说话人名称
            chapter_id: 章节 ID

        Returns:
            (说话人Character, 说话人名称) 元组
        """
        ...

    @abstractmethod
    def match_speaker(self, context: DialogueContext) -> Optional[MatchResult]:
        """根据对话上下文匹配说话人。

        Args:
            context: 对话上下文

        Returns:
            MatchResult 或 None
        """
        ...

    @abstractmethod
    def reset_activity(self) -> None:
        """重置活跃度追踪（章节结束或显式重置时调用）。"""
        ...

    @abstractmethod
    def backfill_unknown_speakers(self, sentences: list) -> int:
        """回填未知说话人。

        Args:
            sentences: 句子列表

        Returns:
            回填数量
        """
        ...

    def match_by_name(self, name: str) -> Optional[MatchResult]:
        """通过角色名精确匹配。"""
        return None

    def match_by_alias(self, alias: str) -> Optional[MatchResult]:
        """通过别名匹配。"""
        return None

    def match_by_title(self, title: str) -> Optional[MatchResult]:
        """通过称谓匹配。"""
        return None

    def match_by_semantic(self, sentence: str) -> Optional[MatchResult]:
        """通过语义相似度匹配。"""
        return None

    def match_by_trigger_words(self, text: str, context: DialogueContext) -> Optional[MatchResult]:
        """通过触发词匹配。"""
        return None

    def match_by_pronoun(self, pronoun: str, context: DialogueContext) -> Optional[MatchResult]:
        """通过代词匹配。"""
        return None

    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        """从文本中提取说话人提示。"""
        return None, ''

    def extract_mentioned_characters(self, text: str) -> List[str]:
        """从文本中提取被提及的角色。"""
        return []

    def update_activity(self, character_id: int, name: str):
        """更新角色活跃度。"""
        pass

    def cache_dialogue(self, character_name: str, dialogue_text: str):
        """缓存角色对话历史。"""
        pass

    def update_mentions(self, names: List[str]):
        """更新被提及角色列表。"""
        pass

    @property
    def current_project_id(self) -> str:
        """获取当前项目 ID。"""
        return getattr(self, '_current_project_id', '')

    @current_project_id.setter
    def current_project_id(self, value: str):
        """设置当前项目 ID。"""
        self._current_project_id = value
