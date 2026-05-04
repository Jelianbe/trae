# -*- coding: utf-8 -*-
"""诡秘之主前10章预标注"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.pipeline_runner import PipelineRunner

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests", "test_novel_guimi_ch1-10.txt")

with open(SRC, "r", encoding="utf-8") as f:
    text = f.read()

print(f"加载文本: {len(text)} 字符, {len(text)/1024:.1f}KB")
print("=" * 60)

runner = PipelineRunner()
results = runner.analyze_chapters(text)

print(f"\n共分析 {len(results)} 章\n")

all_persons = set()

for r in results:
    print(f"--- 第{r.chapter_id}章: {r.title} ---")
    stats = r.statistics
    print(f"  句子数: {stats.get('total_sentences', 0)}")
    print(f"  对话数: {stats.get('dialogue_count', 0)}")
    print(f"  拟声词: {stats.get('sfx_count', 0)}")
    print(f"  实体数: {stats.get('entity_count', 0)}")
    
    # 收集所有实体
    chapter_persons = set()
    for s in r.sentences:
        for e in s.entities:
            if e.get('type') == 'PER':
                name = e.get('standard_name', '') or e.get('text', '')
                chapter_persons.add(name)
                all_persons.add(name)
    
    # 显示对话+说话人匹配结果（前15条）
    dialogue_sentences = [s for s in r.sentences if s.type == "dialogue"]
    print(f"\n  对话列表 (前15条):")
    for s in dialogue_sentences[:15]:
        speaker_info = ""
        if s.speaker:
            speaker_info = f" [说话人: {s.speaker} (q={s.quotation_type})]"
        text_preview = s.text[:50] + ("..." if len(s.text) > 50 else "")
        print(f"    - {text_preview}")
        print(f"      情绪: {s.emotion}, 引号类型: {s.quotation_type}{speaker_info}")
    
    # 显示实体
    print(f"\n  PER 实体 ({len(chapter_persons)}):")
    for name in sorted(chapter_persons):
        print(f"    - {name}")
    
    # 情绪统计
    emotions = {}
    for s in r.sentences:
        emotions[s.emotion] = emotions.get(s.emotion, 0) + 1
    print(f"\n  情绪分布: {dict(sorted(emotions.items(), key=lambda x: -x[1]))}")
    print()

print(f"\n=== 全10章汇总 ===")
print(f"所有检测到的 PER 实体: {sorted(all_persons)}")
print(f"实体总数: {len(all_persons)}")

# 导出完整JSON
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests", "test_novel_guimi_ch1-10_result.json")
json_str = runner.export_json(results)
with open(DST, "w", encoding="utf-8") as f:
    f.write(json_str)
print(f"\n完整结果已导出到: {DST}")
