# -*- coding: utf-8 -*-
"""
Index-TTS 集成测试脚本

测试内容：
1. 连接 Index-TTS 服务
2. 测试基本文本合成
3. 测试情感控制（emo_text）
4. 对比 Kokoro vs Index-TTS 生成结果

用法：
    python scripts/test_index_tts_integration.py
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.tts_indextts import IndexTTSEngine, reset_index_tts_engine
from pipeline.tts_kokoro import KokoroTTSGenerator
import soundfile as sf

# 测试输出目录
TEST_OUTPUT = Path(__file__).parent.parent / "output" / "index_tts_test"
TEST_OUTPUT.mkdir(parents=True, exist_ok=True)

# 测试文本
TEST_TEXTS = [
    "你好，世界！这是一个基本的测试。",
    "你今天看起来很高兴的样子！",
    "他生气地拍了一下桌子。",
    "她悲伤地低下了头。",
    "什么？这怎么可能！",
    "别过来，我好害怕。",
]

# 测试情感标签
TEST_EMOTIONS = ["neutral", "joy", "anger", "sadness", "surprise", "fear"]


def test_index_tts_connection():
    """测试 1: 连接 Index-TTS 服务"""
    print("\n" + "=" * 60)
    print("测试 1: 连接 Index-TTS 服务")
    print("=" * 60)
    
    engine = IndexTTSEngine()
    try:
        engine.initialize()
        print("✅ Index-TTS 服务连接成功")
        return True
    except Exception as e:
        print(f"❌ Index-TTS 服务连接失败: {e}")
        return False


def test_basic_synthesis():
    """测试 2: 基本文本合成"""
    print("\n" + "=" * 60)
    print("测试 2: 基本文本合成（无情感控制）")
    print("=" * 60)
    
    engine = IndexTTSEngine()
    engine.initialize()
    
    success_count = 0
    for i, text in enumerate(TEST_TEXTS[:2]):  # 只测试前 2 个
        try:
            output_file = TEST_OUTPUT / f"basic_{i}.wav"
            engine.generate_audio_to_file(
                text=text,
                output_file=output_file,
            )
            
            # 读取音频信息
            data, sr = sf.read(output_file)
            duration = len(data) / sr
            print(f"✅ 基本合成 {i+1}: {text[:30]}... ({duration:.2f}s)")
            success_count += 1
        except Exception as e:
            print(f"❌ 基本合成 {i+1} 失败: {e}")
    
    return success_count == 2


def test_emotion_control():
    """测试 3: 情感控制（emo_text）"""
    print("\n" + "=" * 60)
    print("测试 3: 情感控制（emo_text）")
    print("=" * 60)
    
    engine = IndexTTSEngine()
    engine.initialize()
    
    test_text = "你真的要这样做吗？"
    success_count = 0
    
    for emotion in TEST_EMOTIONS:
        try:
            output_file = TEST_OUTPUT / f"emotion_{emotion}.wav"
            engine.generate_audio_to_file(
                text=test_text,
                output_file=output_file,
                emotion=emotion,
            )
            
            data, sr = sf.read(output_file)
            duration = len(data) / sr
            print(f"✅ 情感控制 [{emotion}]: ({duration:.2f}s)")
            success_count += 1
        except Exception as e:
            print(f"❌ 情感控制 [{emotion}] 失败: {e}")
    
    return success_count == len(TEST_EMOTIONS)


def test_kokoro_vs_indextts():
    """测试 4: 对比 Kokoro vs Index-TTS"""
    print("\n" + "=" * 60)
    print("测试 4: 对比 Kokoro vs Index-TTS")
    print("=" * 60)
    
    test_text = "这是一段对比测试的文本。"
    
    # Index-TTS
    print("\n[Index-TTS]")
    indextts_start = time.time()
    indextts_engine = IndexTTSEngine()
    indextts_engine.initialize()
    indextts_output = TEST_OUTPUT / "indextts_comparison.wav"
    try:
        indextts_engine.generate_audio_to_file(
            text=test_text,
            output_file=indextts_output,
        )
        indextts_time = time.time() - indextts_start
        data, sr = sf.read(indextts_output)
        indextts_duration = len(data) / sr
        print(f"  ✅ 生成时间: {indextts_time:.2f}s")
        print(f"  ✅ 音频时长: {indextts_duration:.2f}s")
        print(f"  ✅ 输出文件: {indextts_output}")
    except Exception as e:
        print(f"  ❌ Index-TTS 失败: {e}")
        indextts_time = None
    
    # Kokoro
    print("\n[Kokoro]")
    kokoro_start = time.time()
    kokoro = KokoroTTSGenerator()
    kokoro.initialize()
    kokoro_output = TEST_OUTPUT / "kokoro_comparison.wav"
    try:
        kokoro.generate_audio_to_file(
            text=test_text,
            voice_id="zf_001",  # 旁白音色
            output_file=kokoro_output,
            emotion="neutral",
        )
        kokoro_time = time.time() - kokoro_start
        data, sr = sf.read(kokoro_output)
        kokoro_duration = len(data) / sr
        print(f"  ✅ 生成时间: {kokoro_time:.2f}s")
        print(f"  ✅ 音频时长: {kokoro_duration:.2f}s")
        print(f"  ✅ 输出文件: {kokoro_output}")
    except Exception as e:
        print(f"  ❌ Kokoro 失败: {e}")
        kokoro_time = None
    
    # 对比
    print("\n[对比结果]")
    if indextts_time and kokoro_time:
        print(f"  速度比: Kokoro {kokoro_time:.2f}s / Index-TTS {indextts_time:.2f}s = {kokoro_time/indextts_time:.2f}x")
    elif indextts_time:
        print("  ⚠️ 仅 Index-TTS 成功")
    elif kokoro_time:
        print("  ⚠️ 仅 Kokoro 成功")


def test_long_text():
    """测试 5: 长文本合成"""
    print("\n" + "=" * 60)
    print("测试 5: 长文本合成（>100 字）")
    print("=" * 60)
    
    long_text = (
        "他站在悬崖边上，望着下面深不见底的峡谷，心中充满了复杂的情感。"
        "回想起过去的点点滴滴，他不禁感叹命运的无常。曾经的誓言，曾经的承诺，"
        "如今都化为了过眼云烟。他知道，自己已经走上了另一条路，一条充满未知和危险的路。"
        "但是，他并不后悔，因为他相信，只有这样，才能找到真正的自我。"
    )
    
    engine = IndexTTSEngine()
    engine.initialize()
    
    try:
        start_time = time.time()
        output_file = TEST_OUTPUT / "long_text.wav"
        engine.generate_audio_to_file(
            text=long_text,
            output_file=output_file,
            emotion="sadness",
        )
        elapsed = time.time() - start_time
        
        data, sr = sf.read(output_file)
        duration = len(data) / sr
        
        print(f"✅ 长文本合成成功")
        print(f"  文本长度: {len(long_text)} 字")
        print(f"  生成时间: {elapsed:.2f}s")
        print(f"  音频时长: {duration:.2f}s")
        print(f"  输出文件: {output_file}")
        return True
    except Exception as e:
        print(f"❌ 长文本合成失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Index-TTS 集成测试")
    print("=" * 60)
    print(f"测试输出目录: {TEST_OUTPUT}")
    
    # 重置引擎状态
    reset_index_tts_engine()
    
    # 运行测试
    results = {}
    
    # 测试 1: 连接
    results["连接测试"] = test_index_tts_connection()
    if not results["连接测试"]:
        print("\n❌ 连接测试失败，后续测试无法进行")
        return
    
    # 测试 2: 基本合成
    results["基本合成"] = test_basic_synthesis()
    
    # 测试 3: 情感控制
    results["情感控制"] = test_emotion_control()
    
    # 测试 4: 对比 Kokoro vs Index-TTS
    test_kokoro_vs_indextts()
    
    # 测试 5: 长文本
    results["长文本"] = test_long_text()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！Index-TTS 集成成功！")
    else:
        print("⚠️ 部分测试失败，请检查 Index-TTS 服务状态")


if __name__ == "__main__":
    main()
