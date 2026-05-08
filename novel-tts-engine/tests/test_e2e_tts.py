#!/usr/bin/env python
"""E2E TTS 音频生成测试"""
import asyncio
import sys
sys.path.insert(0, 'd:/trae/novel-tts-engine')

from pipeline.tts_generator import TTSGenerator
from pathlib import Path

async def test_tts():
    print('=== TTS 音频生成测试 ===')
    print('Initializing TTS Generator...')
    tts = TTSGenerator(engine='indextts')
    print('TTS Generator initialized')

    test_text = '苏夜走进房间，看到老陈坐在沙发上。'
    output_file = Path('d:/trae/novel-tts-engine/tests/output/e2e_test_tts.wav')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f'Generating TTS: {test_text}')
    result = await tts.generate_audio_async(
        text=test_text,
        speaker='苏夜',
        emotion='neutral',
        output_file=output_file,
        sentence_type='dialogue',
    )

    print(f'Result: {result}')
    print(f'File exists: {result.exists()}')
    
    if result.exists():
        import soundfile as sf
        data, sr = sf.read(result)
        print(f'Duration: {len(data)/sr:.2f}s, Sample rate: {sr}')
        print('✅ TTS 音频生成成功')
    else:
        print('❌ TTS 音频生成失败')

if __name__ == '__main__':
    asyncio.run(test_tts())
