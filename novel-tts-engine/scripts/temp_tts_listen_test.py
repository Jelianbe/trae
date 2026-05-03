#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 端到端听感测试脚本

用途：
1. 对 10 个样本（5 正确 + 5 错误）生成音频
2. 根据当前标注情绪+强度生成 MP3
3. 生成 index.html 用于人工听评

使用方法：
    python scripts/temp_tts_listen_test.py

输出文件夹：output/tts_listen_test/
"""

import os
import json
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Dict, List

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.tts_generator import TTSGenerator, get_tts_generator, reset_tts_generator
from pipeline.pipeline_runner import SentenceData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "output" / "tts_listen_test"
MAX_RETRIES = 3

# 模拟 10 个样本（5 正确 + 5 错误标注）
SAMPLES = [
    {
        "id": 1,
        "text": "苏夜惊讶地看着药老：\"这异火竟如此神奇\"",
        "gt_emotion": "surprise",
        "predicted_emotion": "surprise",
        "intensity": "mild",
        "is_correct": True,
        "speaker": "苏夜",
    },
    {
        "id": 2,
        "text": "\"放肆！你敢背叛我？\"萧炎怒喝道",
        "gt_emotion": "anger",
        "predicted_emotion": "joy",
        "intensity": "moderate",
        "is_correct": False,
        "speaker": "萧炎",
    },
    {
        "id": 3,
        "text": "萧炎缓缓站起身来，走向门口",
        "gt_emotion": "neutral",
        "predicted_emotion": "neutral",
        "intensity": "mild",
        "is_correct": True,
        "speaker": "",
    },
    {
        "id": 4,
        "text": "萧炎笑道：\"太好了，我终于突破了！\"",
        "gt_emotion": "joy",
        "predicted_emotion": "joy",
        "intensity": "moderate",
        "is_correct": True,
        "speaker": "萧炎",
    },
    {
        "id": 5,
        "text": "\"太可怕了，我们快逃！\"萧炎心中一阵恐慌",
        "gt_emotion": "fear",
        "predicted_emotion": "fear",
        "intensity": "strong",
        "is_correct": True,
        "speaker": "萧炎",
    },
    {
        "id": 6,
        "text": "\"走吧，我们该出发了。\"",
        "gt_emotion": "neutral",
        "predicted_emotion": "anger",
        "intensity": "mild",
        "is_correct": False,
        "speaker": "",
    },
    {
        "id": 7,
        "text": "萧炎低声叹息：\"她还是走了。\"",
        "gt_emotion": "sadness",
        "predicted_emotion": "sadness",
        "intensity": "moderate",
        "is_correct": True,
        "speaker": "萧炎",
    },
    {
        "id": 8,
        "text": "\"这怎么可能？\"萧炎惊讶地看着眼前的一切",
        "gt_emotion": "surprise",
        "predicted_emotion": "surprise",
        "intensity": "moderate",
        "is_correct": True,
        "speaker": "萧炎",
    },
    {
        "id": 9,
        "text": "萧炎微微一笑：\"多谢前辈指点。\"",
        "gt_emotion": "joy",
        "predicted_emotion": "neutral",
        "intensity": "mild",
        "is_correct": False,
        "speaker": "萧炎",
    },
    {
        "id": 10,
        "text": "\"混蛋！我绝不会放过你！\"萧炎气得浑身发抖",
        "gt_emotion": "anger",
        "predicted_emotion": "anger",
        "intensity": "strong",
        "is_correct": True,
        "speaker": "萧炎",
    },
]


async def generate_audio_with_retry(
    tts: TTSGenerator,
    text: str,
    speaker: str,
    emotion: str,
    output_file: Path,
    max_retries: int = MAX_RETRIES,
) -> bool:
    """
    带重试机制的音频生成
    
    Returns:
        True if successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            await tts.generate_audio_async(
                text=text,
                speaker=speaker or "default",
                emotion=emotion,
                output_file=output_file,
            )
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_retries} failed for sample: {e}")
            if attempt == max_retries:
                logger.error(f"All {max_retries} attempts failed for sample")
                return False
            await asyncio.sleep(1)
    return False


def generate_html_report(results: List[dict]) -> str:
    """生成 HTML 听评报告"""
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTS 端到端听感测试</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .sample { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .sample-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .sample-id { font-size: 1.2em; font-weight: bold; color: #4CAF50; }
        .sample-status { padding: 4px 12px; border-radius: 4px; font-size: 0.9em; }
        .correct { background: #e8f5e9; color: #2e7d32; }
        .incorrect { background: #ffebee; color: #c62828; }
        .sample-text { font-size: 1.1em; padding: 10px; background: #f9f9f9; border-radius: 4px; margin: 10px 0; }
        .emotion-info { display: flex; gap: 20px; margin: 10px 0; }
        .emotion-tag { padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        .gt { background: #e3f2fd; color: #1565c0; }
        .predicted { background: #fff3e0; color: #e65100; }
        .evaluation { margin-top: 15px; padding: 10px; background: #fafafa; border-radius: 4px; }
        .evaluation label { display: block; margin: 8px 0; }
        audio { width: 100%; margin: 10px 0; }
        .summary { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>🎧 TTS 端到端听感测试</h1>
    <p><strong>测试日期</strong>: """ + __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M") + """</p>
    <p><strong>测试目标</strong>: 验证情绪标注对 TTS 听感的实际影响</p>
"""

    # Summary table
    html += """
    <div class="summary">
        <h2>测试样本摘要</h2>
        <table>
            <tr><th>ID</th><th>状态</th><th>GT 情绪</th><th>预测情绪</th><th>强度</th><th>音频</th></tr>
"""
    for r in results:
        status = "正确" if r["is_correct"] else "错误"
        status_class = "correct" if r["is_correct"] else "incorrect"
        html += f"""<tr>
            <td>{r['id']}</td>
            <td><span class="sample-status {status_class}">{status}</span></td>
            <td>{r['gt_emotion']}</td>
            <td>{r['predicted_emotion']}</td>
            <td>{r['intensity']}</td>
            <td>{'✅' if r['success'] else '❌ 生成失败'}</td>
        </tr>
"""
    html += """</table></div>
"""

    # Individual samples
    for r in results:
        if not r['success']:
            continue
        
        status = "正确标注" if r['is_correct'] else "错误标注"
        status_class = "correct" if r['is_correct'] else "incorrect"
        
        html += f"""
    <div class="sample">
        <div class="sample-header">
            <span class="sample-id">样本 {r['id']}</span>
            <span class="sample-status {status_class}">{status}</span>
        </div>
        <div class="sample-text">{r['text']}</div>
        <div class="emotion-info">
            <span class="emotion-tag gt">GT: {r['gt_emotion']}</span>
            <span class="emotion-tag predicted">预测: {r['predicted_emotion']}</span>
            <span class="emotion-tag">强度: {r['intensity']}</span>
        </div>
        <audio controls>
            <source src="{r['filename']}" type="audio/mpeg">
            您的浏览器不支持音频播放
        </audio>
        <div class="evaluation">
            <strong>人工评价</strong>:
            <label><input type="radio" name="natural_{r['id']}" value="yes"> 自然
                   <input type="radio" name="natural_{r['id']}" value="no"> 不自然
                   <input type="radio" name="natural_{r['id']}" value="ok"> 一般</label>
            <label><input type="radio" name="match_{r['id']}" value="yes"> 情绪匹配
                   <input type="radio" name="match_{r['id']}" value="no"> 不匹配
                   <input type="radio" name="match_{r['id']}" value="partial"> 部分匹配</label>
        </div>
    </div>
"""

    html += """
    <div class="summary">
        <h2>评价说明</h2>
        <p><strong>问题1</strong>: 这段音频听起来自然吗？</p>
        <ul><li>是 - 语速、音调听起来舒适</li><li>否 - 有明显的不自然感</li><li>一般 - 介于两者之间</li></ul>
        <p><strong>问题2</strong>: 情绪表达是否与文本内容匹配？</p>
        <ul><li>是 - 情绪与文本内容一致</li><li>否 - 情绪与文本内容矛盾</li><li>部分匹配 - 部分符合</li></ul>
    </div>
</body>
</html>
"""
    return html


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    tts = get_tts_generator()
    results = []
    
    print(f"\n{'='*60}")
    print("TTS 端到端听感测试")
    print(f"{'='*60}\n")
    
    for sample in SAMPLES:
        label = "正确" if sample["is_correct"] else "错误"
        filename = f"{label}_{sample['id']}.mp3"
        output_file = OUTPUT_DIR / filename
        
        print(f"生成样本 {sample['id']} ({label})...")
        print(f"  文本: {sample['text'][:50]}...")
        print(f"  GT={sample['gt_emotion']}, 预测={sample['predicted_emotion']}, 强度={sample['intensity']}")
        
        success = asyncio.run(generate_audio_with_retry(
            tts=tts,
            text=sample["text"],
            speaker=sample.get("speaker", "default"),
            emotion=sample["predicted_emotion"],
            output_file=output_file,
        ))
        
        results.append({
            "id": sample["id"],
            "text": sample["text"],
            "gt_emotion": sample["gt_emotion"],
            "predicted_emotion": sample["predicted_emotion"],
            "intensity": sample["intensity"],
            "is_correct": sample["is_correct"],
            "filename": filename,
            "success": success,
        })
        
        if success:
            print(f"  ✅ 成功: {output_file}")
        else:
            print(f"  ❌ 失败: {output_file}")
        print()
    
    # Generate HTML report
    html_content = generate_html_report(results)
    html_path = OUTPUT_DIR / "index.html"
    html_path.write_text(html_content, encoding="utf-8")
    
    # Generate summary
    success_count = sum(1 for r in results if r['success'])
    print(f"\n{'='*60}")
    print(f"测试完成")
    print(f"{'='*60}")
    print(f"总样本: {len(results)}")
    print(f"成功: {success_count}")
    print(f"失败: {len(results) - success_count}")
    print(f"\nHTML 报告: {html_path}")
    print(f"请在浏览器中打开 {html_path} 进行听评")


if __name__ == '__main__':
    main()
