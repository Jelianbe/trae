# -*- coding: utf-8 -*-
"""共享数据类型：定义流水线中使用的数据结构和状态枚举"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class PipelineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"


@dataclass
class ProgressInfo:
    """进度信息"""
    current_step: str = ""
    current_chapter: int = 0
    total_chapters: int = 0
    total_steps: int = 6
    current_step_index: int = 0
    state: PipelineState = PipelineState.IDLE
    message: str = ""

    @property
    def progress_percent(self) -> float:
        if self.total_chapters == 0:
            return 0.0
        chapter_progress = self.current_chapter / self.total_chapters
        step_weight = 1.0 / self.total_steps
        return (self.current_step_index + chapter_progress) * step_weight * 100


@dataclass
class FragmentData:
    """句子片段数据（对话/旁白/拟声）"""
    text: str
    type: str  # "dialogue" / "narration" / "onomatopoeia"
    speaker: str = ""


@dataclass
class SentenceData:
    """单句处理结果（MVP 7字段）"""
    text: str
    type: str  # "dialogue" / "narration"
    speaker: str
    emotion: str
    emotion_class: str
    emotion_vector: Optional[List[float]]
    entities: List[dict] = field(default_factory=list)
    fragments: List[FragmentData] = field(default_factory=list)


@dataclass
class ChapterResult:
    """章节处理结果"""
    chapter_id: int = 0
    title: str = ""
    volume: int = 0
    sentences: List[SentenceData] = field(default_factory=list)
    statistics: dict = field(default_factory=dict)
