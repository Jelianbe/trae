# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from pipeline.pipeline_runner import PipelineRunner

runner = PipelineRunner(speaker_matcher_type='hybrid')
text = open(r'C:\Users\月笙如歌\Desktop\修仙传(1).txt', encoding='utf-8').read()

results = runner.analyze_chapters(text)

print(f'=== 处理完成 ===')
print(f'总章节数: {len(results)}')

total_dialogue = 0
total_speaker_found = 0
total_unknown = 0

for r in results:
    for s in r.sentences:
        total_dialogue += 1
        has_speaker = bool(s.speaker and '未知' not in s.speaker)
        if has_speaker:
            total_speaker_found += 1
        else:
            total_unknown += 1
    
    print(f'\n第{r.chapter_id}章: {r.title}')
    print(f'  总句数: {len(r.sentences)}')
    print(f'  有说话人: {total_speaker_found}')
    print(f'  未知/旁白: {total_unknown}')
    
    # 显示前8条已标注的对话
    shown = 0
    for s in r.sentences:
        if s.speaker and '未知' not in s.speaker:
            text_preview = s.text[:60]
            print(f'  [{s.speaker}] {text_preview}')
            shown += 1
            if shown >= 8:
                break
    
    # 显示未标注的对话（有引号但没说话人）
    unknown_dialogues = []
    for s in r.sentences:
        if not s.speaker or '未知' in s.speaker:
            if '\u201c' in s.text or '\u300c' in s.text or '\u300e' in s.text:
                unknown_dialogues.append(s.text[:60])
    
    if unknown_dialogues:
        print(f'\n  --- 未标注的对话 ({len(unknown_dialogues)} 条) ---')
        for ud in unknown_dialogues[:5]:
            print(f'  [??] {ud}')
        if len(unknown_dialogues) > 5:
            print(f'  ... 还有 {len(unknown_dialogues) - 5} 条')
