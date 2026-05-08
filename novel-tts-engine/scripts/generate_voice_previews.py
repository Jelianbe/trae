# -*- coding: utf-8 -*-
"""生成6个音色的试听音频文件（一次性脚本）"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from pipeline.tts_kokoro import get_kokoro_generator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PREVIEW_TEXT = "你好，欢迎使用小说语音合成引擎。这是一段试听音频。"

VOICES = [
    {"name": "云深", "voice": "zm_010"},
    {"name": "凌风", "voice": "zm_011"},
    {"name": "若水", "voice": "zf_001"},
    {"name": "铁马", "voice": "zm_012"},
    {"name": "素心", "voice": "zf_002"},
    {"name": "墨言", "voice": "zm_013"},
]

def main():
    output_dir = PROJECT_ROOT / "frontend" / "audio" / "previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"输出目录: {output_dir}")
    
    kokoro = get_kokoro_generator()
    
    for voice in VOICES:
        name = voice["name"]
        voice_id = voice["voice"]
        output_file = output_dir / f"{name}.wav"
        
        if output_file.exists() and output_file.stat().st_size > 1000:
            logger.info(f"✓ {name} - 已存在，跳过")
            continue
        
        logger.info(f"生成 {name} ({voice_id})...")
        
        try:
            kokoro.generate_audio_to_file(
                text=PREVIEW_TEXT,
                voice_id=voice_id,
                output_file=output_file,
            )
            
            if output_file.exists() and output_file.stat().st_size > 1000:
                logger.info(f"✓ {name} - 成功 ({output_file.stat().st_size} bytes)")
            else:
                logger.error(f"✗ {name} - 失败")
        except Exception as e:
            logger.error(f"✗ {name} - {e}")
    
    logger.info("完成！")

if __name__ == "__main__":
    main()
