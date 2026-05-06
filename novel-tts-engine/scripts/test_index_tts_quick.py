# -*- coding: utf-8 -*-
"""
Index-TTS 快速连通性测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from pathlib import Path

TEST_OUTPUT = Path(__file__).parent.parent / "output" / "index_tts_test"
TEST_OUTPUT.mkdir(parents=True, exist_ok=True)

AUDIO_PATH = "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_01.wav"

def test_basic():
    print("=" * 60)
    print("Index-TTS 连通性测试")
    print("=" * 60)
    
    url = "http://localhost:7860/v2/synthesize"
    payload = {
        "text": "你好，世界！这是一个基本的测试。",
        "audio_path": AUDIO_PATH
    }
    
    print(f"请求地址: {url}")
    print(f"参考音频: {AUDIO_PATH}")
    print(f"测试文本: {payload['text']}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        print(f"HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("TTS 合成成功!")
            output_file = TEST_OUTPUT / "test_basic.wav"
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"音频已保存至: {output_file}")
            print(f"音频大小: {len(response.content)} bytes")
            return True
        else:
            print(f"错误: {response.text[:300]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"连接失败: {e}")
        return False
    except requests.exceptions.Timeout:
        print("请求超时")
        return False


def test_emotion():
    print()
    print("=" * 60)
    print("情感控制测试")
    print("=" * 60)
    
    url = "http://localhost:7860/v2/synthesize"
    
    emotions = {
        "neutral": "平静地说",
        "joy": "开心地说",
        "anger": "生气地说",
        "sadness": "悲伤地说",
        "surprise": "惊讶地说",
        "fear": "害怕地说",
    }
    
    text = "你今天看起来很高兴的样子！"
    
    for emotion, emo_text in emotions.items():
        payload = {
            "text": text,
            "audio_path": AUDIO_PATH,
            "emo_text": emo_text
        }
        
        print(f"\n测试情感: {emotion} ({emo_text})")
        try:
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                output_file = TEST_OUTPUT / f"test_{emotion}.wav"
                with open(output_file, "wb") as f:
                    f.write(response.content)
                print(f"  成功 - 音频大小: {len(response.content)} bytes")
            else:
                print(f"  失败 - HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"  错误: {e}")


if __name__ == "__main__":
    basic_ok = test_basic()
    if basic_ok:
        test_emotion()
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
