# -*- coding: utf-8 -*-
"""TTS 音频生成器：将处理后的文本转换为音频文件

本模块实现了从文本到音频的完整转换流程，支持：
1. Kokoro 离线 TTS（100+ 中文音色）
2. 旁白/对话声线分离
3. 多角色声音映射
4. 情绪驱动的声音调整（预留接口）
5. 音频文件导出 + 章节合并

技术选型：Kokoro 82M
优势：离线、高质量、多音色、CPU 可运行
"""

import os
import asyncio
import tempfile
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import threading

from pipeline.pipeline_runner import ChapterResult, SentenceData
from pipeline.tts_kokoro import (
    KokoroTTSGenerator,
    get_kokoro_generator,
    NARRATOR_VOICE,
    ROLE_VOICE_MAP,
    merge_audio_files,
)

logger = logging.getLogger(__name__)


# 旁白固定参数（无情绪）
NARRATOR_EMOTION = "neutral"
NARRATOR_INTENSITY = "mild"


@dataclass
class AudioSegment:
    """音频片段"""
    text: str
    speaker: str
    emotion: str
    audio_file: Path
    duration_ms: int = 0
    quotation_type: str = "none"
    sentence_type: str = "narration"  # "narration" / "dialogue"


class TTSGenerator:
    """TTS 音频生成器
    
    使用 Kokoro 离线 TTS 将文本转换为音频。
    旁白和对话使用不同音色，角色各有专属音色。
    """
    
    def __init__(self, voice_map: Optional[Dict[str, str]] = None):
        self.voice_map = {**VOICE_MAP, **(voice_map or {})}
        self._lock = threading.Lock()
        self._kokoro: Optional[KokoroTTSGenerator] = None
    
    def _get_kokoro(self) -> KokoroTTSGenerator:
        """懒加载 Kokoro 实例"""
        if self._kokoro is None:
            with self._lock:
                if self._kokoro is None:
                    self._kokoro = get_kokoro_generator()
        return self._kokoro
    
    def _get_voice_id(self, speaker: str, sentence_type: str) -> str:
        """
        获取音色ID
        
        旁白 -> NARRATOR_VOICE
        对话 -> 角色映射 -> 默认男声
        """
        if sentence_type == "narration":
            return NARRATOR_VOICE
        return self._get_kokoro().get_voice_for_speaker(speaker)
    
    async def generate_audio_async(
        self,
        text: str,
        speaker: str = "default",
        emotion: str = "neutral",
        output_file: Optional[Path] = None,
        sentence_type: str = "narration",
    ) -> Path:
        """异步生成音频"""
        kokoro = self._get_kokoro()
        voice_id = self._get_voice_id(speaker, sentence_type)
        
        if output_file is None:
            fd, output_file = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            output_file = Path(output_file)
        
        kokoro.generate_audio_to_file(
            text=text,
            voice_id=voice_id,
            output_file=output_file,
            emotion=emotion,
        )
        
        return output_file
    
    def generate_audio(
        self,
        text: str,
        speaker: str = "default",
        emotion: str = "neutral",
        output_file: Optional[Path] = None,
        sentence_type: str = "narration",
    ) -> Path:
        """同步生成音频（包装器）"""
        if not text or not text.strip():
            raise ValueError("文本内容不能为空")
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_audio_async(text, speaker, emotion, output_file, sentence_type)
                )
            finally:
                loop.close()
        
        return run_async()
    
    def generate_from_sentence(
        self,
        sentence: SentenceData,
        output_dir: Path,
    ) -> AudioSegment:
        """从句子数据生成音频片段"""
        sentence_type = getattr(sentence, 'sentence_type', 'narration')
        
        filename = f"sentence_{sentence.sentence_id:04d}.wav"
        output_file = output_dir / filename
        
        emotion = sentence.emotion or NARRATOR_EMOTION
        if sentence_type == "narration":
            emotion = NARRATOR_EMOTION
        
        audio_file = self.generate_audio(
            text=sentence.text,
            speaker=sentence.speaker or "default",
            emotion=emotion,
            output_file=output_file,
            sentence_type=sentence_type,
        )
        
        return AudioSegment(
            text=sentence.text,
            speaker=sentence.speaker or "narrator",
            emotion=emotion,
            audio_file=audio_file,
            quotation_type=sentence.quotation_type,
            sentence_type=sentence_type,
        )
    
    def generate_from_chapter(
        self,
        chapter_result: ChapterResult,
        output_dir: Optional[Path] = None,
        merge_output: bool = True,
    ) -> Dict:
        """
        从章节结果生成完整音频
        
        Args:
            chapter_result: 章节处理结果
            output_dir: 输出目录
            merge_output: 是否合并为单个 MP3
        
        Returns:
            {"segments": [AudioSegment], "merged_file": Path 或 None}
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_segments = []
        wav_files = []
        
        for sentence in chapter_result.sentences:
            try:
                segment = self.generate_from_sentence(sentence, output_dir)
                audio_segments.append(segment)
                wav_files.append(segment.audio_file)
            except Exception as e:
                logger.error(f"生成音频失败（句子 {sentence.sentence_id}）：{e}")
                continue
        
        merged_file = None
        if merge_output and wav_files:
            chapter_name = chapter_result.chapter_title or "unknown"
            merged_name = f"{chapter_name.replace(' ', '_')}.mp3"
            merged_path = output_dir.parent / merged_name
            try:
                merged_file = merge_audio_files(wav_files, merged_path)
                logger.info(f"章节音频已合并: {merged_file}")
            except Exception as e:
                logger.error(f"合并音频失败: {e}")
        
        return {
            "segments": audio_segments,
            "merged_file": merged_file,
            "wav_files": wav_files,
        }


_generator: Optional[TTSGenerator] = None
_generator_lock = threading.Lock()


def get_tts_generator(voice_map: Optional[Dict[str, str]] = None) -> TTSGenerator:
    global _generator
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                _generator = TTSGenerator(voice_map)
    return _generator


def reset_tts_generator() -> None:
    global _generator
    with _generator_lock:
        _generator = None
