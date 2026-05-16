# -*- coding: utf-8 -*-
"""进度管理器：专门负责进度跟踪、暂停/恢复功能"""

import logging
import threading
from typing import Optional, Callable

from pipeline.types import PipelineState, ProgressInfo

logger = logging.getLogger(__name__)


class ProgressManager:
    """进度管理器：专门负责进度跟踪、暂停/恢复功能"""

    def __init__(self, total_steps: int = 6):
        self._progress = ProgressInfo(total_steps=total_steps)
        self._pause_event = threading.Event()
        self._pause_event.set()

    @property
    def progress(self) -> ProgressInfo:
        return self._progress

    def pause(self):
        """暂停流水线"""
        self._progress.state = PipelineState.PAUSED
        self._pause_event.clear()
        logger.info("流水线已暂停")

    def resume(self):
        """恢复流水线"""
        self._progress.state = PipelineState.RUNNING
        self._pause_event.set()
        logger.info("流水线已恢复")

    def check_pause(self):
        """检查是否暂停，如果暂停则阻塞"""
        self._pause_event.wait()

    def update_progress(
        self,
        step: str,
        chapter: int,
        total: int,
        step_idx: int,
        message: str = "",
    ):
        """更新进度信息"""
        self._progress.current_step = step
        self._progress.current_chapter = chapter
        self._progress.total_chapters = total
        self._progress.current_step_index = step_idx
        self._progress.message = message

    def set_state(self, state: PipelineState):
        """设置流水线状态"""
        self._progress.state = state

    def notify_progress(self, callback: Optional[Callable[[ProgressInfo], None]]):
        """通知进度更新"""
        if callback:
            callback(self._progress)
