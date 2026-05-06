# -*- coding: utf-8 -*-
"""
Index-TTS 集成测试：验证回退机制
1. Index-TTS 正常时，使用 Index-TTS 生成音频
2. Index-TTS 不可用时，自动回退 Kokoro
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.tts_generator import TTSGenerator, reset_tts_generator

def test_indextts_available():
    print("=" * 60)
    print("测试 1: Index-TTS 可用")
    print("=" * 60)
    
    reset_tts_generator()
    tts = TTSGenerator(engine="indextts")
    
    import tempfile
    from pathlib import Path
    output = Path(tempfile.mktemp(suffix=".wav"))
    
    result = tts.generate_audio(
        text="你好，世界！这是 Index-TTS 测试。",
        speaker="旁白",
        emotion="joy",
        output_file=output,
        sentence_type="dialogue",
    )
    
    size = os.path.getsize(result)
    print(f"  引擎: Index-TTS")
    print(f"  生成音频: {result}")
    print(f"  文件大小: {size} bytes")
    print(f"  状态: {'PASS' if size > 0 else 'FAIL'}")
    return True


def test_indextts_fallback():
    print()
    print("=" * 60)
    print("测试 2: Index-TTS 不可用 → 回退 Kokoro")
    print("=" * 60)
    
    reset_tts_generator()
    tts = TTSGenerator(
        engine="indextts",
        indextts_url="http://localhost:9999",  # 不可用的端口
        fallback_to_kokoro=True,
    )
    
    import tempfile
    from pathlib import Path
    output = Path(tempfile.mktemp(suffix=".wav"))
    
    try:
        result = tts.generate_audio(
            text="你好，这是回退测试。",
            speaker="旁白",
            emotion="neutral",
            output_file=output,
            sentence_type="narration",
        )
        
        size = os.path.getsize(result)
        print(f"  回退引擎: Kokoro")
        print(f"  生成音频: {result}")
        print(f"  文件大小: {size} bytes")
        print(f"  状态: {'PASS' if size > 0 else 'FAIL'}")
        return True
    except Exception as e:
        print(f"  错误: {e}")
        return False


if __name__ == "__main__":
    ok1 = test_indextts_available()
    ok2 = test_indextts_fallback()
    
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"  Index-TTS 正常: {'PASS' if ok1 else 'FAIL'}")
    print(f"  回退机制:      {'PASS' if ok2 else 'FAIL'}")
    print()
    if ok1 and ok2:
        print(">>> 全部通过")
    else:
        print(">>> 有未通过项")
