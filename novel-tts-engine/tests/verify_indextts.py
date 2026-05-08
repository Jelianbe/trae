#!/usr/bin/env python
"""
Index-TTS 独立验证脚本

验证项目：
1. 服务连通性测试
2. 音质验证（盲测>=4/5）
3. 角色声线区分验证（3+不同说话人）
4. 情感向量参数验证（语气差异可感知）
5. 中文发音准确率验证

用法：
    python tests/verify_indextts.py

注意：
- Index-TTS 服务需要运行在 http://localhost:8300
- 需要准备 3 个不同说话人的参考音频
- 验证结果需要人工听评
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional

import requests
import soundfile as sf
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.tts_indextts import IndexTTSEngine, DEFAULT_INDEX_TTS_AUDIO
from utils.config import MODELS_DIR

# 测试输出目录
OUTPUT_DIR = PROJECT_ROOT / "tests" / "output" / "indextts_verify"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Index-TTS 服务地址
TTS_URL = "http://localhost:8300"

# 测试文本
TEST_TEXTS = {
    "basic": "你好，世界！这是一个基础的音质测试。",
    "narration": "夜幕降临，城市的霓虹灯在雨水中闪烁。他站在窗前，凝视着远方的天际线。",
    "dialogue_joy": "太好了！我们终于成功了！",
    "dialogue_sad": "为什么事情会变成这样……我真的很难过。",
    "dialogue_anger": "你怎么能这样对我！我再也受不了了！",
    "pronunciation": "张三是北京大学的学生，他今天去了上海参加一个会议。",
}

# 参考音频（需要准备 3 个不同说话人的音频）
REFERENCE_AUDIO = {
    "speaker_1": {
        "path": "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_01.wav",
        "name": "说话人1",
    },
    "speaker_2": {
        "path": "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_02.wav",
        "name": "说话人2",
    },
    "speaker_3": {
        "path": "D:/trae/novel-tts-engine/TTS/IndexTTS2-SonicVale/examples/voice_03.wav",
        "name": "说话人3",
    },
}

# 情感向量（8维）
EMOTION_VECTORS = {
    "joy": [0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    "sadness": [0.1, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    "anger": [0.1, 0.1, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1],
    "surprise": [0.1, 0.1, 0.1, 0.8, 0.1, 0.1, 0.1, 0.1],
    "fear": [0.1, 0.1, 0.1, 0.1, 0.8, 0.1, 0.1, 0.1],
    "neutral": [0.2, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05],
}


def test_service_connection():
    """测试1：服务连通性"""
    print("\n" + "="*60)
    print("测试1：服务连通性")
    print("="*60)
    
    try:
        response = requests.get(TTS_URL, timeout=10)
        if response.status_code == 200:
            print("✅ Index-TTS 服务可用")
            return True
        else:
            print(f"❌ 服务返回状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到 Index-TTS 服务: {TTS_URL}")
        print("   请确保服务已启动，命令示例：")
        print("   cd TTS/IndexTTS2-SonicVale && python app.py --port 8300")
        return False
    except requests.exceptions.Timeout:
        print("❌ 连接超时")
        return False


def test_audio_quality(engine: IndexTTSEngine):
    """测试2：音质验证（盲测>=4/5）"""
    print("\n" + "="*60)
    print("测试2：音质验证")
    print("="*60)
    
    results = []
    
    for test_name, text in TEST_TEXTS.items():
        if test_name.startswith("pronunciation"):
            continue
            
        print(f"\n生成测试音频: {test_name}")
        
        try:
            output_file = OUTPUT_DIR / f"quality_{test_name}.wav"
            engine.generate_audio_to_file(
                text=text,
                output_file=output_file,
                audio_path=REFERENCE_AUDIO["speaker_1"]["path"],
            )
            
            # 验证文件是否生成
            if output_file.exists():
                data, sr = sf.read(output_file)
                duration = len(data) / sr
                print(f"  ✅ 成功生成音频 ({duration:.2f}s)")
                results.append({
                    "test": test_name,
                    "status": "success",
                    "file": str(output_file),
                    "duration": duration,
                })
            else:
                print(f"  ❌ 文件未生成")
                results.append({"test": test_name, "status": "failed"})
                
        except Exception as e:
            print(f"  ❌ 生成失败: {e}")
            results.append({"test": test_name, "status": "error", "error": str(e)})
    
    # 生成听评报告
    print("\n" + "-"*60)
    print("盲听听评指引：")
    print("请依次试听以下音频，按 1-5 分评分：")
    print("  5分：非常自然，接近真人")
    print("  4分：比较自然，有少量机械感")
    print("  3分：基本可懂，机械感明显")
    print("  2分：难以接受，严重失真")
    print("  1分：完全不可用")
    print("-"*60)
    
    for r in results:
        if r["status"] == "success":
            print(f"  {r['test']}: {r['file']}  评分: ___/5")
    
    return results


def test_speaker_distinction(engine: IndexTTSEngine):
    """测试3：角色声线区分验证（3+不同说话人）"""
    print("\n" + "="*60)
    print("测试3：角色声线区分")
    print("="*60)
    
    test_text = "你好，我是小说中的角色，这是我的台词。"
    results = []
    
    for speaker_id, speaker_info in REFERENCE_AUDIO.items():
        audio_path = speaker_info["path"]
        
        if not Path(audio_path).exists():
            print(f"  ⚠️ 参考音频不存在: {audio_path}")
            print(f"     请准备 {speaker_info['name']} 的参考音频（5-30秒 WAV 格式）")
            results.append({
                "speaker": speaker_id,
                "status": "skipped",
                "reason": "audio not found",
            })
            continue
        
        print(f"\n生成 {speaker_info['name']} 的音频...")
        
        try:
            output_file = OUTPUT_DIR / f"speaker_{speaker_id}.wav"
            engine.generate_audio_to_file(
                text=test_text,
                output_file=output_file,
                audio_path=audio_path,
            )
            
            if output_file.exists():
                data, sr = sf.read(output_file)
                duration = len(data) / sr
                print(f"  ✅ 成功生成 ({duration:.2f}s)")
                results.append({
                    "speaker": speaker_id,
                    "status": "success",
                    "file": str(output_file),
                })
            else:
                print(f"  ❌ 文件未生成")
                results.append({"speaker": speaker_id, "status": "failed"})
                
        except Exception as e:
            print(f"  ❌ 生成失败: {e}")
            results.append({"speaker": speaker_id, "status": "error", "error": str(e)})
    
    # 生成听评报告
    successful = [r for r in results if r["status"] == "success"]
    print("\n" + "-"*60)
    print("声线区分听评指引：")
    print("请依次试听以下音频，判断是否能明显区分不同声线：")
    
    for r in results:
        if r["status"] == "success":
            print(f"  {REFERENCE_AUDIO[r['speaker']]['name']}: {r['file']}")
    
    print(f"\n成功生成 {len(successful)}/3 个声线")
    if len(successful) >= 3:
        print("✅ 通过：3个以上不同声线已生成")
    else:
        print("⚠️ 需要至少 3 个不同参考音频")
    print("-"*60)
    
    return results


def test_emotion_vector(engine: IndexTTSEngine):
    """测试4：情感向量参数验证"""
    print("\n" + "="*60)
    print("测试4：情感向量验证")
    print("="*60)
    
    test_text = "你来了，我一直在等你。"
    results = []
    
    for emotion_name, emo_vector in EMOTION_VECTORS.items():
        print(f"\n生成情感: {emotion_name}")
        
        try:
            output_file = OUTPUT_DIR / f"emotion_{emotion_name}.wav"
            engine.generate_audio_to_file(
                text=test_text,
                output_file=output_file,
                audio_path=REFERENCE_AUDIO["speaker_1"]["path"],
                emo_vector=emo_vector,
            )
            
            if output_file.exists():
                data, sr = sf.read(output_file)
                duration = len(data) / sr
                print(f"  ✅ 成功生成 ({duration:.2f}s)")
                results.append({
                    "emotion": emotion_name,
                    "status": "success",
                    "file": str(output_file),
                })
            else:
                print(f"  ❌ 文件未生成")
                results.append({"emotion": emotion_name, "status": "failed"})
                
        except Exception as e:
            print(f"  ❌ 生成失败: {e}")
            results.append({"emotion": emotion_name, "status": "error", "error": str(e)})
    
    # 生成听评报告
    print("\n" + "-"*60)
    print("情感区分听评指引：")
    print("请依次试听以下音频，判断语气差异是否可感知：")
    
    for r in results:
        if r["status"] == "success":
            print(f"  {r['emotion']}: {r['file']}  差异明显: □是 □否")
    
    print("-"*60)
    
    return results


def test_pronunciation(engine: IndexTTSEngine):
    """测试5：中文发音准确率验证"""
    print("\n" + "="*60)
    print("测试5：中文发音准确率")
    print("="*60)
    
    pronunciation_tests = [
        ("专有名词", "张三和李四是北京大学计算机系的学生。"),
        ("多音字", "他高兴地说：'这个问题我得重（chóng）新考虑一下。'"),
        ("数字", "他今年25岁，体重65公斤，身高175厘米。"),
        ("英文混合", "这个API的URL是 https://example.com"),
        ("标点停顿", "他走了。她哭了。他们都很难过。"),
    ]
    
    results = []
    
    for test_name, text in pronunciation_tests:
        print(f"\n生成测试: {test_name}")
        print(f"  文本: {text}")
        
        try:
            output_file = OUTPUT_DIR / f"pronunciation_{test_name}.wav"
            engine.generate_audio_to_file(
                text=text,
                output_file=output_file,
                audio_path=REFERENCE_AUDIO["speaker_1"]["path"],
            )
            
            if output_file.exists():
                data, sr = sf.read(output_file)
                duration = len(data) / sr
                print(f"  ✅ 成功生成 ({duration:.2f}s)")
                results.append({
                    "test": test_name,
                    "status": "success",
                    "file": str(output_file),
                })
            else:
                print(f"  ❌ 文件未生成")
                results.append({"test": test_name, "status": "failed"})
                
        except Exception as e:
            print(f"  ❌ 生成失败: {e}")
            results.append({"test": test_name, "status": "error", "error": str(e)})
    
    # 生成听评报告
    print("\n" + "-"*60)
    print("发音准确率听评指引：")
    print("请依次试听以下音频，检查发音是否准确：")
    
    for r in results:
        if r["status"] == "success":
            print(f"  {r['test']}: {r['file']}  准确率: ___%")
    
    print("-"*60)
    
    return results


def generate_report(all_results: Dict):
    """生成验证报告"""
    report_file = OUTPUT_DIR / "verification_report.json"
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": all_results,
        "summary": {
            "total_tests": sum(len(v) for v in all_results.values()),
            "success_count": sum(
                1 for tests in all_results.values() 
                for t in tests 
                if t.get("status") == "success"
            ),
        }
    }
    
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n验证报告已保存: {report_file}")
    
    return report


def main():
    """主函数"""
    print("Index-TTS 独立验证脚本")
    print("="*60)
    
    all_results = {}
    
    # 测试1：服务连通性
    connected = test_service_connection()
    if not connected:
        print("\n❌ 服务不可用，后续测试无法进行")
        print("请启动 Index-TTS 服务后重试")
        return
    
    # 初始化引擎
    print("\n初始化 Index-TTS 引擎...")
    engine = IndexTTSEngine(base_url=TTS_URL)
    engine.initialize()
    
    # 测试2：音质验证
    all_results["audio_quality"] = test_audio_quality(engine)
    
    # 测试3：角色声线区分
    all_results["speaker_distinction"] = test_speaker_distinction(engine)
    
    # 测试4：情感向量验证
    all_results["emotion_vector"] = test_emotion_vector(engine)
    
    # 测试5：中文发音准确率
    all_results["pronunciation"] = test_pronunciation(engine)
    
    # 生成报告
    report = generate_report(all_results)
    
    print("\n" + "="*60)
    print("验证完成")
    print("="*60)
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"成功: {report['summary']['success_count']}")
    print(f"\n请根据听评指引完成人工评估")
    print(f"所有音频输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
