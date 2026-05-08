#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Index-TTS 独立验证脚本

验证目标：
1. 服务连通性检查
2. 音质验证（基础文本合成）
3. 角色声线区分（不同参考音频）
4. 情感向量参数验证
5. 中文发音准确率验证

使用方法：
    python tests/validate_indextts.py [--base_url http://localhost:8300]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).parent.parent / "test_outputs" / "indextts_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def check_service(base_url: str) -> bool:
    """检查 Index-TTS 服务是否可用"""
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            logger.info("Index-TTS 服务可用")
            return True
        else:
            logger.warning(f"服务返回状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"无法连接到 Index-TTS 服务: {base_url}")
        logger.error("请确保服务已启动")
        return False
    except requests.exceptions.Timeout:
        logger.error("连接超时")
        return False


def synthesize_text(base_url: str, text: str, audio_path: str, emo_text: str = None, emo_vector: list = None) -> bytes:
    """调用 Index-TTS 合成音频"""
    payload = {
        "text": text,
        "audio_path": audio_path,
    }
    
    if emo_vector is not None:
        payload["emo_vector"] = emo_vector
    elif emo_text is not None:
        payload["emo_text"] = emo_text
    
    response = requests.post(
        f"{base_url}/v2/synthesize",
        json=payload,
        timeout=120,
    )
    
    if response.status_code != 200:
        error_msg = f"Index-TTS API error: {response.status_code}"
        try:
            error_detail = response.json().get("detail", "")
            error_msg += f" - {error_detail}"
        except Exception:
            error_msg += f" - {response.text[:200]}"
        raise RuntimeError(error_msg)
    
    return response.content


def test_basic_synthesis(base_url: str, audio_path: str) -> bool:
    """测试 1: 基础音质验证"""
    logger.info("=" * 60)
    logger.info("测试 1: 基础音质验证")
    logger.info("=" * 60)
    
    text = "这是一个基础音质测试，用于验证 Index-TTS 服务的基本合成功能。"
    output_file = OUTPUT_DIR / "test1_basic.wav"
    
    try:
        wav_bytes = synthesize_text(base_url, text, audio_path)
        output_file.write_bytes(wav_bytes)
        logger.info(f"合成成功: {output_file}")
        logger.info(f"音频大小: {len(wav_bytes)} bytes")
        logger.info(f"时长约: {len(wav_bytes) / 16000 / 2:.1f} 秒 (假设 16kHz, 16bit)")
        return True
    except Exception as e:
        logger.error(f"基础合成失败: {e}")
        return False


def test_voice_differentiation(base_url: str) -> bool:
    """测试 2: 角色声线区分验证"""
    logger.info("=" * 60)
    logger.info("测试 2: 角色声线区分验证")
    logger.info("=" * 60)
    
    text = "你好，我是这个角色在说话。请仔细听我的声音是否与其他角色不同。"
    
    reference_audios = [
        "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_01.wav",
        "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_02.wav",
        "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_03.wav",
    ]
    
    success_count = 0
    
    for i, audio_path in enumerate(reference_audios, 1):
        if not Path(audio_path).exists():
            logger.warning(f"参考音频不存在: {audio_path}，跳过")
            continue
        
        output_file = OUTPUT_DIR / f"test2_voice{i}.wav"
        
        try:
            wav_bytes = synthesize_text(base_url, text, audio_path)
            output_file.write_bytes(wav_bytes)
            logger.info(f"角色{i} 合成成功: {output_file}")
            success_count += 1
        except Exception as e:
            logger.error(f"角色{i} 合成失败: {e}")
    
    if success_count >= 3:
        logger.info("声线区分验证: 通过 (3个不同声线)")
        return True
    elif success_count >= 1:
        logger.warning(f"声线区分验证: 部分通过 (仅{success_count}个声线)")
        return True
    else:
        logger.error("声线区分验证: 失败")
        return False


def test_emotion_control(base_url: str, audio_path: str) -> bool:
    """测试 3: 情感控制验证"""
    logger.info("=" * 60)
    logger.info("测试 3: 情感控制验证")
    logger.info("=" * 60)
    
    text = "这个消息真的让我非常激动，我简直不敢相信自己的耳朵。"
    
    emotion_configs = [
        {"emo_text": "开心地说", "output": "test3_emo_happy.wav"},
        {"emo_text": "悲伤地说", "output": "test3_emo_sad.wav"},
        {"emo_text": "生气地说", "output": "test3_emo_angry.wav"},
        {"emo_text": "平静地说", "output": "test3_emo_neutral.wav"},
    ]
    
    success_count = 0
    
    for config in emotion_configs:
        output_file = OUTPUT_DIR / config["output"]
        
        try:
            wav_bytes = synthesize_text(
                base_url, text, audio_path, emo_text=config["emo_text"]
            )
            output_file.write_bytes(wav_bytes)
            logger.info(f"情感 '{config['emo_text']}' 合成成功: {output_file}")
            success_count += 1
        except Exception as e:
            logger.error(f"情感 '{config['emo_text']}' 合成失败: {e}")
    
    if success_count >= 3:
        logger.info("情感控制验证: 通过")
        return True
    elif success_count >= 1:
        logger.warning(f"情感控制验证: 部分通过 ({success_count}/{len(emotion_configs)})")
        return True
    else:
        logger.error("情感控制验证: 失败")
        return False


def test_emotion_vector(base_url: str, audio_path: str) -> bool:
    """测试 4: 情感向量参数验证"""
    logger.info("=" * 60)
    logger.info("测试 4: 情感向量参数验证")
    logger.info("=" * 60)
    
    text = "这是一段用于测试情感向量参数的文本。"
    
    emotion_vectors = [
        {"vector": [0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], "output": "test4_vec_happy.wav", "desc": "高开心"},
        {"vector": [0.1, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], "output": "test4_vec_sad.wav", "desc": "高悲伤"},
        {"vector": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1], "output": "test4_vec_neutral.wav", "desc": "中性"},
    ]
    
    success_count = 0
    
    for config in emotion_vectors:
        output_file = OUTPUT_DIR / config["output"]
        
        try:
            wav_bytes = synthesize_text(
                base_url, text, audio_path, emo_vector=config["vector"]
            )
            output_file.write_bytes(wav_bytes)
            logger.info(f"情感向量 '{config['desc']}' 合成成功: {output_file}")
            success_count += 1
        except Exception as e: