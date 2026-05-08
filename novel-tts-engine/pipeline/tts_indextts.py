# -*- coding: utf-8 -*-
"""
Index-TTS 音频生成器

通过 HTTP API 调用 IndexTTS2 服务进行语音合成。

功能：
1. 通过 REST API 调用 Index-TTS 服务
2. 支持参考音频克隆音色
3. 支持情感文本控制（emo_text）
4. 与 KokoroTTSGenerator 接口兼容

依赖：
- Index-TTS 服务运行在 http://localhost:7860
- 参考音频文件（WAV 格式，5-30 秒）

用法：
    generator = IndexTTSEngine(
        base_url="http://localhost:7860",
        default_audio_path="D:/TTS/IndexTTS2-SonicVale/examples/voice_01.wav"
    )
    audio_bytes = generator.generate_audio(
        text="你好，世界！",
        emotion="joy"
    )
"""

import os
import logging
import tempfile
import threading
import io
from pathlib import Path
from typing import Dict, List, Optional

import requests
import soundfile as sf

logger = logging.getLogger(__name__)


# 默认参考音频路径（可配置）
DEFAULT_INDEX_TTS_AUDIO = "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_01.wav"

# 情感映射：将系统情感标签映射为 Index-TTS 的情感描述文本
EMOTION_TO_TEXT = {
    "joy": "开心地说",
    "anger": "生气地说",
    "sadness": "悲伤地说",
    "surprise": "惊讶地说",
    "fear": "害怕地说",
    "neutral": "平静地说",
}


class IndexTTSEngine:
    """
    Index-TTS 音频生成器（HTTP API 适配器）
    
    用法：
        engine = IndexTTSEngine()
        audio_bytes = engine.generate_audio(
            text="你好，世界！",
            audio_path="reference.wav",
            emotion="joy"
        )
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(
        self,
        base_url: str = "http://localhost:8300",
        default_audio_path: str = DEFAULT_INDEX_TTS_AUDIO,
        timeout: int = 120,
    ):
        """
        Args:
            base_url: Index-TTS 服务地址
            default_audio_path: 默认参考音频路径
            timeout: HTTP 请求超时时间（秒），默认 5 秒，超时后快速回退到 Kokoro
        """
        self.base_url = base_url.rstrip("/")
        self.default_audio_path = default_audio_path
        self.timeout = timeout
        self._initialized = False
        self._session = requests.Session()
    
    def initialize(self):
        """初始化：检查服务是否可用"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            logger.info(f"Connecting to Index-TTS service at {self.base_url}...")
            
            # 检查服务是否可用
            try:
                response = self._session.get(self.base_url, timeout=10)
                if response.status_code == 200:
                    logger.info("Index-TTS service is available")
                else:
                    logger.warning(f"Index-TTS health check returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Cannot reach Index-TTS service: {e}. Will retry on first request.")
            
            # 检查默认参考音频是否存在
            if not os.path.isfile(self.default_audio_path):
                logger.warning(
                    f"Default reference audio not found: {self.default_audio_path}\n"
                    f"Please provide audio_path parameter when calling generate_audio()"
                )
            
            self._initialized = True
            logger.info("Index-TTS engine initialized")
    
    def generate_audio(
        self,
        text: str,
        audio_path: Optional[str] = None,
        emotion: Optional[str] = None,
        emo_vector: Optional[List[float]] = None,
    ) -> bytes:
        """
        生成音频
        
        Args:
            text: 要合成的文本
            audio_path: 参考音频路径（可选，默认使用 default_audio_path）
            emotion: 情感标签（joy/anger/sadness/surprise/fear/neutral）
            emo_vector: 8维情感向量（与 emotion 二选一）
        
        Returns:
            WAV 格式的音频 bytes
        
        Raises:
            requests.exceptions.RequestException: HTTP 请求失败
            ValueError: 参数错误
        """
        if not self._initialized:
            self.initialize()
        
        if not text or not text.strip():
            raise ValueError("文本内容不能为空")
        
        # 确定参考音频路径
        if audio_path is None:
            audio_path = self.default_audio_path
        
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Reference audio not found: {audio_path}")
        
        # 构建请求体
        payload = {
            "text": text,
            "audio_path": audio_path,
        }
        
        # 添加情感控制参数
        if emo_vector is not None:
            if len(emo_vector) != 8:
                raise ValueError("emo_vector must have exactly 8 elements")
            payload["emo_vector"] = emo_vector
        elif emotion is not None:
            emo_text = EMOTION_TO_TEXT.get(emotion, emotion)
            payload["emo_text"] = emo_text
        
        # 发送请求
        try:
            logger.debug(
                f"Requesting Index-TTS: text='{text[:50]}...', "
                f"audio='{os.path.basename(audio_path)}', emotion='{emotion}'"
            )
            
            response = self._session.post(
                f"{self.base_url}/v2/synthesize",
                json=payload,
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                error_msg = f"Index-TTS API error: {response.status_code}"
                try:
                    error_detail = response.json().get("detail", "")
                    error_msg += f" - {error_detail}"
                except Exception:
                    error_msg += f" - {response.text[:200]}"
                raise RuntimeError(error_msg)
            
            # 返回 WAV bytes
            return response.content
            
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Index-TTS request timeout ({self.timeout}s). "
                f"The text may be too long or the service is overloaded."
            )
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Cannot connect to Index-TTS service at {self.base_url}. "
                f"Please ensure the service is running. Error: {e}"
            )
    
    def generate_audio_to_file(
        self,
        text: str,
        output_file: Path,
        audio_path: Optional[str] = None,
        emotion: Optional[str] = None,
        emo_vector: Optional[List[float]] = None,
    ) -> Path:
        """
        生成音频并保存到文件
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径
            audio_path: 参考音频路径
            emotion: 情感标签
            emo_vector: 8维情感向量
        
        Returns:
            输出文件路径
        """
        wav_bytes = self.generate_audio(text, audio_path, emotion, emo_vector)
        
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(wav_bytes)
        
        logger.debug(f"Audio saved to: {output_file}")
        return output_file
    
    def get_voice_for_speaker(self, speaker: str) -> str:
        """
        Index-TTS 不使用 voice_id，而是使用参考音频路径。
        此方法返回默认参考音频路径，以保持与 KokoroTTSGenerator 的接口兼容。
        
        后续可以为每个角色配置不同的参考音频。
        
        Args:
            speaker: 说话人名称（暂未使用）
        
        Returns:
            参考音频路径
        """
        return self.default_audio_path
    
    def close(self):
        """关闭 HTTP session"""
        if self._session:
            self._session.close()
            self._session = None
            self._initialized = False


def get_index_tts_engine(
    base_url: str = "http://localhost:8300",
    default_audio_path: str = DEFAULT_INDEX_TTS_AUDIO,
) -> IndexTTSEngine:
    """获取全局单例"""
    if IndexTTSEngine._instance is None:
        with IndexTTSEngine._lock:
            if IndexTTSEngine._instance is None:
                IndexTTSEngine._instance = IndexTTSEngine(
                    base_url=base_url,
                    default_audio_path=default_audio_path,
                )
    return IndexTTSEngine._instance


def reset_index_tts_engine():
    """重置全局单例（用于测试）"""
    with IndexTTSEngine._lock:
        if IndexTTSEngine._instance is not None:
            IndexTTSEngine._instance.close()
            IndexTTSEngine._instance = None
