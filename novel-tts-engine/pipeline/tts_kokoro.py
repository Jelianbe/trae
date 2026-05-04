#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kokoro TTS 音频生成器

功能：
1. 使用 Kokoro 82M 模型进行离线中文语音合成
2. 支持多音色选择（100+ 中文音色）
3. 旁白/对话声线分离
4. 音频合并功能

依赖：
- pip install kokoro ordered-set cn2an pypinyin_dict soundfile pydub
- 模型文件：models/kokoro/kokoro-v1_1-zh.pth
- 音色文件：models/kokoro/voices/*.pt
"""

import os
import logging
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import torch
import soundfile as sf
from pydub import AudioSegment

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
KOKORO_MODEL_DIR = PROJECT_ROOT / "models" / "kokoro"

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """角色音色配置"""
    voice_id: str          # 音色文件名（不含 .pt）
    gender: str            # "male" / "female"
    description: str       # 描述


# 旁白默认音色（中性女声）
NARRATOR_VOICE = "zf_001"

# 角色声音映射（hardcode，后续可配置化）
# 可用音色：男 zm_009~zm_013, zm_020 等；女 zf_001~zf_008, zf_017~zf_024 等
ROLE_VOICE_MAP: Dict[str, VoiceConfig] = {
    # 萧炎 - 年轻男声
    "萧炎": VoiceConfig("zm_009", "male", "年轻男声"),
    # 药老 - 成熟男声
    "药老": VoiceConfig("zm_010", "male", "成熟男声"),
    # 苏夜 - 青年男声
    "苏夜": VoiceConfig("zm_013", "male", "青年男声"),
    # 林雪 - 年轻女声
    "林雪": VoiceConfig("zf_008", "female", "年轻女声"),
    # 赵天行 - 中年男声
    "赵天行": VoiceConfig("zm_020", "male", "中年男声"),
    # 默认男声
    "male_default": VoiceConfig("zm_012", "male", "默认男声"),
    # 默认女声
    "female_default": VoiceConfig("zf_005", "female", "默认女声"),
}


class KokoroTTSGenerator:
    """
    Kokoro TTS 音频生成器
    
    用法：
        generator = KokoroTTSGenerator()
        audio_bytes = generator.generate_audio(
            text="你好，世界！",
            voice_id="zf_001",
            emotion="joy",
            intensity="moderate"
        )
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._model = None
        self._pipeline = None
        self._voice_cache: Dict[str, torch.Tensor] = {}
        self._initialized = False
    
    def initialize(self):
        """初始化 Kokoro 模型（线程安全）"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing Kokoro TTS model...")
            from kokoro import KPipeline, KModel
            
            model_path = KOKORO_MODEL_DIR / "kokoro-v1_1-zh.pth"
            config_path = KOKORO_MODEL_DIR / "config.json"
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Kokoro model not found at {model_path}. "
                    f"Please download it first."
                )
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Kokoro model on {device}")
            
            self._model = KModel(
                model=str(model_path),
                config=str(config_path),
                repo_id="hexgrad/Kokoro-82M-v1.1-zh"
            ).to(device).eval()
            
            self._pipeline = KPipeline(
                lang_code="z",
                repo_id="hexgrad/Kokoro-82M-v1.1-zh",
                model=self._model
            )
            
            self._device = device
            self._initialized = True
            logger.info("Kokoro TTS model initialized successfully")
    
    def load_voice(self, voice_id: str) -> torch.Tensor:
        """
        加载音色文件（带缓存）
        
        Args:
            voice_id: 音色ID（如 "zf_001", "zm_015"）
        
        Returns:
            音色 tensor
        """
        if voice_id in self._voice_cache:
            return self._voice_cache[voice_id]
        
        voice_path = KOKORO_MODEL_DIR / "voices" / f"{voice_id}.pt"
        if not voice_path.exists():
            raise FileNotFoundError(f"Voice file not found: {voice_path}")
        
        voice_tensor = torch.load(str(voice_path), weights_only=True)
        self._voice_cache[voice_id] = voice_tensor
        return voice_tensor
    
    def generate_audio(
        self,
        text: str,
        voice_id: str,
        emotion: Optional[str] = None,
        intensity: Optional[str] = None,
    ) -> bytes:
        """
        生成音频
        
        Args:
            text: 要合成的文本
            voice_id: 音色ID（如 "zf_001"）
            emotion: 情绪（预留，暂未使用）
            intensity: 强度（预留，暂未使用）
        
        Returns:
            WAV 格式的音频 bytes
        """
        if not self._initialized:
            self.initialize()
        
        voice_tensor = self.load_voice(voice_id)
        
        generator = self._pipeline(text, voice=voice_tensor)
        result = next(generator)
        wav_data = result.audio
        sr = getattr(result, 'sr', 24000)
        
        # 转换为 WAV bytes
        import io
        buffer = io.BytesIO()
        sf.write(buffer, wav_data, sr, format='WAV')
        return buffer.getvalue()
    
    def generate_audio_to_file(
        self,
        text: str,
        voice_id: str,
        output_file: Path,
        emotion: Optional[str] = None,
        intensity: Optional[str] = None,
    ) -> Path:
        """
        生成音频并保存到文件
        
        Args:
            text: 要合成的文本
            voice_id: 音色ID
            output_file: 输出文件路径
            emotion: 情绪（预留）
            intensity: 强度（预留）
        
        Returns:
            输出文件路径
        """
        wav_bytes = self.generate_audio(text, voice_id, emotion, intensity)
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(wav_bytes)
        return output_file
    
    def get_voice_for_speaker(self, speaker: str) -> str:
        """
        根据说话人名称获取音色ID
        
        Args:
            speaker: 说话人名称（如 "萧炎"）
        
        Returns:
            音色ID
        """
        if speaker in ROLE_VOICE_MAP:
            return ROLE_VOICE_MAP[speaker].voice_id
        
        # 默认返回男声
        return ROLE_VOICE_MAP["male_default"].voice_id


def get_kokoro_generator() -> KokoroTTSGenerator:
    """获取全局单例"""
    if KokoroTTSGenerator._instance is None:
        KokoroTTSGenerator._instance = KokoroTTSGenerator()
    return KokoroTTSGenerator._instance


def reset_kokoro_generator():
    """重置全局单例（用于测试）"""
    KokoroTTSGenerator._instance = None


def merge_audio_files(
    file_list: List[Path],
    output_path: Path,
    silence_ms: int = 200,
) -> Path:
    """
    合并多个音频文件
    
    Args:
        file_list: 音频文件列表（按顺序）
        output_path: 输出文件路径
        silence_ms: 音频间静音间隔（毫秒）
    
    Returns:
        输出文件路径
    """
    if not file_list:
        raise ValueError("file_list is empty")
    
    # 尝试检测 ffmpeg 是否可用
    use_ffmpeg = False
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        use_ffmpeg = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        use_ffmpeg = False
    
    if not use_ffmpeg:
        logger.warning("ffmpeg not available, falling back to WAV output")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if use_ffmpeg:
        silence = AudioSegment.silent(duration=silence_ms)
        combined = AudioSegment.empty()
        
        for i, file_path in enumerate(file_list):
            if not Path(file_path).exists():
                logger.warning(f"Skipping missing file: {file_path}")
                continue
            
            audio = AudioSegment.from_file(str(file_path))
            if i > 0:
                combined += silence
            combined += audio
        
        combined.export(str(output_path), format="mp3")
    else:
        # Fallback: read WAV files and concatenate using soundfile
        import numpy as np
        
        all_audio = []
        for file_path in file_list:
            if not Path(file_path).exists():
                logger.warning(f"Skipping missing file: {file_path}")
                continue
            data, sr = sf.read(str(file_path))
            all_audio.append(data)
            # Add silence between files (zeros)
            silence_samples = int(sr * silence_ms / 1000)
            all_audio.append(np.zeros((silence_samples, 2) if data.ndim == 2 else silence_samples))
        
        # Remove last silence
        if len(all_audio) > 1:
            all_audio = all_audio[:-1]
        
        combined_audio = np.concatenate(all_audio, axis=0)
        
        # If output path is .mp3, change to .wav
        if output_path.suffix.lower() == ".mp3":
            output_path = output_path.with_suffix(".wav")
        
        sf.write(str(output_path), combined_audio, sr)
    
    logger.info(f"Merged {len(file_list)} audio files -> {output_path}")
    return output_path
