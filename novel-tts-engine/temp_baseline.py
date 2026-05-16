# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from pipeline.pipeline_runner import PipelineRunner

runner = PipelineRunner(speaker_matcher_type='legacy')
text = open(r'C:\Users\月笙如歌\Desktop\修仙传(1).txt', encoding='utf-8').read()
results = runner.analyze_chapters(text)

print('=== Bug 1 修复前基线 ===')
for r in results:
    print(f'\n第{r.chapter_id}章: {r.title}')
    for s in r.sentences:
        if s.speaker and '未知' not in s.speaker:
            text_preview = s.text[:80]
            print(f'  [{s.speaker}] {text_preview}')
