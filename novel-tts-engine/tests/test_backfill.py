# -*- coding: utf-8 -*-
"""
回填机制测试：用完整小说文本验证未知角色回填效果

流程：
1. 用完整小说运行pipeline，触发冷启动（3000字阈值）
2. 冷启动后，自动回填未知说话人
3. 统计回填前后的角色分布
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pipeline_runner import get_pipeline_runner, reset_pipeline_runner

def test_backfill_on_novel():
    test_files = [
        ("tests/test_novel.txt", "修仙"),
        ("tests/test_novel_western.txt", "西幻"),
        ("tests/test_novel_urban.txt", "都市"),
    ]
    
    for filepath, genre in test_files:
        filepath = Path(__file__).parent.parent / filepath
        if not filepath.exists():
            print(f"跳过: {filepath} 不存在")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"\n{'='*70}")
        print(f"测试文件: {filepath.name} ({genre}) - {len(text)} 字")
        print(f"{'='*70}")
        
        reset_pipeline_runner()
        
        runner = get_pipeline_runner()
        results = runner.analyze_chapters(text)
        
        total_dialogue = 0
        unknown_count = 0
        specific_speakers = {}
        
        for chapter in results:
            for sentence in chapter.sentences:
                if sentence.type == "dialogue":
                    total_dialogue += 1
                    speaker = sentence.speaker
                    if speaker.startswith("未知"):
                        unknown_count += 1
                    elif speaker and speaker not in ("", "Narrator"):
                        specific_speakers[speaker] = specific_speakers.get(speaker, 0) + 1
        
        print(f"\n  对话总数: {total_dialogue}")
        print(f"  具体角色: {total_dialogue - unknown_count}")
        print(f"  未知角色: {unknown_count}")
        
        if specific_speakers:
            print(f"\n  角色分布:")
            for name, count in sorted(specific_speakers.items(), key=lambda x: -x[1]):
                print(f"    {name:>12}: {count}次")
        
        if total_dialogue > 0:
            specific_rate = (total_dialogue - unknown_count) / total_dialogue
            print(f"\n  角色识别率: {specific_rate:.1%}")


if __name__ == "__main__":
    test_backfill_on_novel()
