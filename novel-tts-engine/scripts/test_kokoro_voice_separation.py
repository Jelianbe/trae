#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS Kokoro 声线分离 + 音频合并验证

测试内容：
1. 旁白和对话使用不同音色
2. 不同角色使用不同音色
3. 音频合并功能
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.tts_kokoro import KokoroTTSGenerator, get_kokoro_generator, merge_audio_files, NARRATOR_VOICE, ROLE_VOICE_MAP

def test_voice_separation():
    print("=" * 60)
    print("声线分离验证测试")
    print("=" * 60)
    
    output_dir = PROJECT_ROOT / "output" / "kokoro_voice_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    kokoro = get_kokoro_generator()
    
    # Test samples
    samples = [
        {"text": "萧炎缓缓站起身来，走向门口。", "speaker": "narrator", "voice_id": NARRATOR_VOICE, "type": "旁白"},
        {"text": '"太好了，我终于突破了！"', "speaker": "萧炎", "voice_id": ROLE_VOICE_MAP["萧炎"].voice_id, "type": "对话-萧炎"},
        {"text": "药老微微一笑，点头表示赞许。", "speaker": "narrator", "voice_id": NARRATOR_VOICE, "type": "旁白"},
        {"text": '"不错，你的进步很快。"', "speaker": "药老", "voice_id": ROLE_VOICE_MAP["药老"].voice_id, "type": "对话-药老"},
        {"text": "林雪走过来，眼中满是喜悦。", "speaker": "narrator", "voice_id": NARRATOR_VOICE, "type": "旁白"},
        {"text": '"苏夜，你太棒了！"', "speaker": "林雪", "voice_id": ROLE_VOICE_MAP["林雪"].voice_id, "type": "对话-林雪"},
    ]
    
    wav_files = []
    timings = []
    
    for i, sample in enumerate(samples):
        filename = f"sample_{i+1}_{sample['type']}.wav"
        output_path = output_dir / filename
        
        print(f"\n生成 {i+1}: [{sample['type']}] {sample['text']}")
        print(f"  音色: {sample['voice_id']}")
        
        start = time.time()
        kokoro.generate_audio_to_file(
            text=sample['text'],
            voice_id=sample['voice_id'],
            output_file=output_path,
        )
        elapsed = time.time() - start
        timings.append(elapsed)
        
        wav_files.append(output_path)
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  输出: {output_path}")
    
    # Merge test
    print(f"\n{'=' * 40}")
    print("合并音频...")
    merged_path = output_dir / "merged_chapter.mp3"
    
    start = time.time()
    result = merge_audio_files(wav_files, merged_path, silence_ms=300)
    merge_time = time.time() - start
    
    print(f"合并耗时: {merge_time:.2f}s")
    print(f"合并文件: {result}")
    print(f"文件大小: {result.stat().st_size / 1024:.1f} KB")
    
    # Summary
    avg_timing = sum(timings) / len(timings)
    print(f"\n{'=' * 60}")
    print(f"测试完成")
    print(f"  平均生成时间: {avg_timing:.2f}s/句")
    print(f"  旁白音色: {NARRATOR_VOICE}")
    print(f"  角色音色: {list(ROLE_VOICE_MAP.keys())}")
    print(f"  合并文件: {merged_path}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    test_voice_separation()
