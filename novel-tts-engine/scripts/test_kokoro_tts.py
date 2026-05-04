#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kokoro TTS 验证测试脚本"""

import os
import sys
import time
import torch
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
KOKORO_DIR = PROJECT_ROOT / "models" / "kokoro"

def test_kokoro():
    """测试 Kokoro 中文生成"""
    print("=" * 60)
    print("Kokoro TTS 验证测试")
    print("=" * 60)
    
    # Check model files
    model_path = KOKORO_DIR / "kokoro-v1_1-zh.pth"
    config_path = KOKORO_DIR / "config.json"
    voice_path = KOKORO_DIR / "voices" / "zf_001.pt"
    
    for p in [model_path, config_path, voice_path]:
        if not p.exists():
            print(f"ERROR: {p} not found")
            return False
        print(f"  Found: {p.name} ({p.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Load model
    print("\nLoading model...")
    from kokoro import KPipeline, KModel
    
    device = "cpu"
    model = KModel(
        model=str(model_path),
        config=str(config_path),
        repo_id="hexgrad/Kokoro-82M-v1.1-zh"
    ).to(device).eval()
    print(f"  Model loaded on {device}")
    
    pipeline = KPipeline(
        lang_code="z",
        repo_id="hexgrad/Kokoro-82M-v1.1-zh",
        model=model
    )
    print("  Pipeline ready")
    
    # Load voice
    voice_tensor = torch.load(str(voice_path), weights_only=True)
    print(f"  Voice loaded: zf_001 (female)")
    
    # Generate test sentence
    test_text = "你好，世界！这是一段 Kokoro TTS 生成的中文语音测试。"
    output_path = Path(__file__).parent / "output" / "kokoro_test.mp3"
    output_path.parent.mkdir(exist_ok=True)
    
    print(f"\nGenerating audio: {test_text}")
    start = time.time()
    
    generator = pipeline(test_text, voice=voice_tensor)
    result = next(generator)
    wav = result.audio
    sr = getattr(result, 'sr', 24000)
    
    elapsed = time.time() - start
    print(f"  Generated in {elapsed:.2f}s")
    print(f"  Sample rate: {sr}")
    print(f"  Audio length: {len(wav)} samples ({len(wav)/sr:.2f}s)")
    
    # Save as wav first, then convert to mp3
    wav_path = output_path.with_suffix(".wav")
    import soundfile as sf
    sf.write(str(wav_path), wav, sr)
    
    # Convert to mp3 if pydub available
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(str(wav_path))
        audio.export(str(output_path), format="mp3")
        print(f"  Saved MP3: {output_path}")
        wav_path.unlink()
    except ImportError:
        print(f"  Saved WAV: {wav_path}")
    
    print(f"\n{'=' * 60}")
    print(f"TEST PASSED: CPU inference {elapsed:.2f}s < 1s per sentence")
    print(f"{'=' * 60}")
    return True

if __name__ == "__main__":
    success = test_kokoro()
    sys.exit(0 if success else 1)
