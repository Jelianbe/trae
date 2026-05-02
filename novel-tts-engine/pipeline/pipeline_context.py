# -*- coding: utf-8 -*-
"""Pipeline上下文 - 贯穿整个流水线的数据传输对象

所有模块读写同一个上下文，不再需要层层传递参数。
注意：此文件目前仅供定义使用，尚未被 pipeline_runner.py 引入。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class ChapterData:
    """章节数据"""
    chapter_id: int
    title: str
    content: str
    start_pos: int = 0
    end_pos: int = 0


@dataclass
class SentenceData:
    """句子数据"""
    text: str
    sentence_id: int = 0
    speaker: Optional[str] = None
    emotion: str = "neutral"
    entities: List[dict] = field(default_factory=list)
    sfx_words: List[str] = field(default_factory=list)


@dataclass
class PipelineContext:
    """
    Pipeline上下文 - 贯穿整个流水线

    所有模块读写同一个上下文，不再需要层层传递参数
    """
    raw_text: str
    chapters: List[ChapterData] = field(default_factory=list)
    entities_by_chapter: Dict[int, List] = field(default_factory=dict)
    linked_entities_by_chapter: Dict[int, List] = field(default_factory=dict)
    sfx_by_chapter: Dict[int, List] = field(default_factory=dict)
    sentences_by_chapter: Dict[int, List[SentenceData]] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
