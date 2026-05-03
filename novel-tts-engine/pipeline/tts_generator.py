# -*- coding: utf-8 -*-
"""TTS 音频生成器：将处理后的文本转换为音频文件

本模块实现了从文本到音频的完整转换流程，支持：
1. 多角色声音映射（不同角色使用不同声音）
2. 情绪驱动的声音调整（语速、音调、音量变化）
3. 音频文件导出（MP3 格式）

技术选型：Edge-TTS（免费在线 TTS 服务）
优势：免费、多语言支持、无需本地模型
劣势：需要网络连接
"""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import threading

from pipeline.pipeline_runner import ChapterResult, SentenceData


# 角色到 Edge-TTS 声音的映射
# 声音列表参考：https://github.com/rany2/edge-tts
VOICE_MAP: Dict[str, str] = {
    "default": "zh-CN-XiaoxiaoNeural",      # 默认：年轻女性
    "Narrator": "zh-CN-YunxiNeural",         # 旁白：年轻男性
    # 角色声音映射（可根据需要扩展）
    # "萧炎": "zh-CN-YunxiNeural",          # 年轻男性
    # "药老": "zh-CN-YunjianNeural",        # 老年男性
    # "女性角色": "zh-CN-XiaoyiNeural",     # 年轻女性（活泼）
}

# 情绪到声音参数的映射
# 语速：相对百分比（Edge-TTS 支持 "+10%" 格式）
# 音调：Hz 单位（Edge-TTS 要求 Hz 格式，如 "+10Hz"）
# 音量：相对百分比
EMOTION_VOICE_PARAMS: Dict[str, Dict[str, str]] = {
    "neutral": {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"},
    "joy": {"rate": "+10%", "pitch": "+10Hz", "volume": "+5%"},
    "anger": {"rate": "+30%", "pitch": "+20Hz", "volume": "+20%"},
    "sadness": {"rate": "-20%", "pitch": "-10Hz", "volume": "-10%"},
    "surprise": {"rate": "+40%", "pitch": "+15Hz", "volume": "+10%"},
    "fear": {"rate": "+20%", "pitch": "+5Hz", "volume": "+5%"},
    "written": {"rate": "-10%", "pitch": "+0Hz", "volume": "+0%"},  # 书面内容：慢速念读
    "thought": {"rate": "-15%", "pitch": "-5Hz", "volume": "-5%"},   # 内心独白：小声慢速
}


@dataclass
class AudioSegment:
    """音频片段"""
    text: str
    speaker: str
    emotion: str
    audio_file: Path
    duration_ms: int = 0  # 音频时长（毫秒）
    quotation_type: str = "none"


class TTSGenerator:
    """TTS 音频生成器
    
    使用 Edge-TTS 服务将文本转换为音频。
    支持角色声音映射和情绪驱动的声音调整。
    """
    
    def __init__(self, voice_map: Optional[Dict[str, str]] = None):
        """
        Args:
            voice_map: 自定义角色声音映射（可选）
        """
        self.voice_map = {**VOICE_MAP, **(voice_map or {})}
        self._lock = threading.Lock()
    
    def get_voice_for_speaker(self, speaker: str) -> str:
        """
        获取角色对应的 TTS 声音
        
        Args:
            speaker: 角色名称
        
        Returns:
            Edge-TTS 声音名称
        """
        return self.voice_map.get(speaker, self.voice_map["default"])
    
    def get_voice_params_for_emotion(self, emotion: str) -> Dict[str, str]:
        """
        获取情绪对应的声音参数
        
        Args:
            emotion: 情绪标签
        
        Returns:
            声音参数字典（rate, pitch, volume）
        """
        return EMOTION_VOICE_PARAMS.get(emotion, EMOTION_VOICE_PARAMS["neutral"])
    
    async def generate_audio_async(
        self,
        text: str,
        speaker: str = "default",
        emotion: str = "neutral",
        output_file: Optional[Path] = None,
    ) -> Path:
        """
        异步生成音频（内部方法）
        
        Args:
            text: 文本内容
            speaker: 角色名称
            emotion: 情绪标签
            output_file: 输出文件路径（可选，默认临时文件）
        
        Returns:
            输出音频文件路径
        """
        import edge_tts
        
        voice = self.get_voice_for_speaker(speaker)
        params = self.get_voice_params_for_emotion(emotion)
        
        if output_file is None:
            # 创建临时文件
            fd, output_file = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            output_file = Path(output_file)
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=params["rate"],
            pitch=params["pitch"],
            volume=params["volume"],
        )
        
        await communicate.save(str(output_file))
        
        return output_file
    
    def generate_audio(
        self,
        text: str,
        speaker: str = "default",
        emotion: str = "neutral",
        output_file: Optional[Path] = None,
    ) -> Path:
        """
        生成音频（同步包装器）
        
        Args:
            text: 文本内容
            speaker: 角色名称
            emotion: 情绪标签
            output_file: 输出文件路径（可选）
        
        Returns:
            输出音频文件路径
        """
        if not text or not text.strip():
            raise ValueError("文本内容不能为空")
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_audio_async(text, speaker, emotion, output_file)
                )
            finally:
                loop.close()
        
        return run_async()
    
    def generate_from_sentence(
        self,
        sentence: SentenceData,
        output_dir: Path,
    ) -> AudioSegment:
        """
        从句子数据生成音频片段
        
        Args:
            sentence: 句子数据
            output_dir: 输出目录
        
        Returns:
            音频片段
        """
        # 生成文件名：chapter_sentence.mp3
        filename = f"sentence_{sentence.sentence_id:04d}.mp3"
        output_file = output_dir / filename
        
        audio_file = self.generate_audio(
            text=sentence.text,
            speaker=sentence.speaker or "default",
            emotion=sentence.emotion or "neutral",
            output_file=output_file,
        )
        
        return AudioSegment(
            text=sentence.text,
            speaker=sentence.speaker or "default",
            emotion=sentence.emotion or "neutral",
            audio_file=audio_file,
            quotation_type=sentence.quotation_type,
        )
    
    def generate_from_chapter(
        self,
        chapter_result: ChapterResult,
        output_dir: Optional[Path] = None,
    ) -> List[AudioSegment]:
        """
        从章节结果生成完整音频
        
        Args:
            chapter_result: 章节处理结果
            output_dir: 输出目录（可选，默认临时目录）
        
        Returns:
            音频片段列表
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        audio_segments = []
        
        for sentence in chapter_result.sentences:
            try:
                segment = self.generate_from_sentence(sentence, output_dir)
                audio_segments.append(segment)
            except Exception as e:
                # 记录错误但继续处理其他句子
                print(f"生成音频失败（句子 {sentence.sentence_id}）：{e}")
                continue
        
        return audio_segments


# 全局实例管理
_generator: Optional[TTSGenerator] = None
_generator_lock = threading.Lock()


def get_tts_generator(voice_map: Optional[Dict[str, str]] = None) -> TTSGenerator:
    """
    获取或创建全局 TTS 生成器实例（线程安全）
    
    Args:
        voice_map: 自定义角色声音映射（可选）
    
    Returns:
        TTS 生成器实例
    """
    global _generator
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                _generator = TTSGenerator(voice_map)
    return _generator


def reset_tts_generator() -> None:
    """重置全局 TTS 生成器实例，用于测试或重新初始化"""
    global _generator
    with _generator_lock:
        _generator = None
