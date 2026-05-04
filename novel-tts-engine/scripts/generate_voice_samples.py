#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成多个音色对比音频供用户识别"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.tts_kokoro import KokoroTTSGenerator, get_kokoro_generator, ROLE_VOICE_MAP, NARRATOR_VOICE

# 测试文本 - 涵盖不同场景
TEST_SAMPLES = [
    {"label": "旁白-女", "voice": NARRATOR_VOICE, "text": "萧炎缓缓站起身来，目光坚定地望向远方。天空中乌云密布，似乎预示着一场风暴即将来临。"},
    {"label": "萧炎-男", "voice": ROLE_VOICE_MAP["萧炎"].voice_id, "text": "药老，我一定会变强的！不管前方有什么困难，我都不会退缩。"},
    {"label": "药老-男", "voice": ROLE_VOICE_MAP["药老"].voice_id, "text": "不错，你的悟性确实不错。但要记住，修炼之路，急不得。"},
    {"label": "苏夜-男", "voice": ROLE_VOICE_MAP["苏夜"].voice_id, "text": "这道电流的波动很奇怪，不像是自然产生的。"},
    {"label": "林雪-女", "voice": ROLE_VOICE_MAP["林雪"].voice_id, "text": "苏夜，你没事吧？刚才那道闪电太危险了！"},
    {"label": "赵天行-男", "voice": ROLE_VOICE_MAP["赵天行"].voice_id, "text": "年轻人，你的天赋很不错。加入联盟，我们一起守护这个世界。"},
    {"label": "默认男声", "voice": ROLE_VOICE_MAP["male_default"].voice_id, "text": "这是一个默认男声的测试，用来对比不同音色的区别。"},
    {"label": "默认女声", "voice": ROLE_VOICE_MAP["female_default"].voice_id, "text": "这是一个默认女声的测试，声音柔和，适合旁白和女性角色。"},
]

# 额外的女声对比
EXTRA_VOICES = ["zf_002", "zf_003", "zf_004", "zf_005", "zf_006", "zf_007"]

def main():
    output_dir = PROJECT_ROOT / "output" / "voice_identification"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    kokoro = get_kokoro_generator()
    
    print("=" * 60)
    print("音色识别测试音频生成")
    print("=" * 60)
    
    # Generate main samples
    for i, sample in enumerate(TEST_SAMPLES):
        filename = f"{i+1:02d}_{sample['label']}.wav"
        output_path = output_dir / filename
        
        print(f"\n生成 {i+1}: [{sample['label']}] {sample['voice']}")
        print(f"  文本: {sample['text'][:40]}...")
        
        start = time.time()
        kokoro.generate_audio_to_file(
            text=sample['text'],
            voice_id=sample['voice'],
            output_file=output_path,
        )
        elapsed = time.time() - start
        
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  输出: {output_path}")
    
    # Generate extra female voice comparison
    extra_text = "这是一个音色对比测试，请仔细听不同声音之间的区别。"
    
    print(f"\n{'=' * 40}")
    print("额外女声对比...")
    
    for voice_id in EXTRA_VOICES:
        filename = f"女声对比_{voice_id}.wav"
        output_path = output_dir / filename
        
        print(f"  生成 {voice_id}...")
        kokoro.generate_audio_to_file(
            text=extra_text,
            voice_id=voice_id,
            output_file=output_path,
        )
        print(f"  完成: {output_path}")
    
    print(f"\n{'=' * 60}")
    print("生成完成！")
    print(f"输出目录: {output_dir}")
    print(f"共生成 {len(TEST_SAMPLES) + len(EXTRA_VOICES)} 个音频文件")
    print(f"请在文件管理器中打开试听")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
