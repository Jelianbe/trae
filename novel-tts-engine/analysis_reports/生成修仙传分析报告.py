# -*- coding: utf-8 -*-
"""生成修仙传错误案例分析报告"""
import sys
sys.path.insert(0, '.')

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.chapter_splitter import ChapterSplitter
import re, os

NOVEL_PATH = r'C:\Users\月笙如歌\Desktop\修仙传(1).txt'
with open(NOVEL_PATH, 'r', encoding='utf-8') as f:
    full_text = f.read()

splitter = ChapterSplitter()
chapters = splitter.split(full_text)

cm = CharacterManager()
sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
sm._current_project_id = 'test_real_novel'

results = sm.analyze_dialogue(full_text, chapter_id='ch_all')

# Find dialogue positions with context
lines = []
lines.append('# 修仙传(1).txt 说话人识别 - 错误案例 + 修改代码对照')
lines.append('')
lines.append('## 一、修改对照表')
lines.append('')
lines.append('### P0-1: speech_verb_detector.py 统一说话动词')
lines.append('')
lines.append('**修改前** (speaker_matcher.py:224-229)：')
lines.append('```')
lines.append('SPEECH_ACTION_PATTERNS = [')
lines.append('    r"[\\u4e00-\\u9fa5]{2,4}(?:道|说道|问|答道|喊|叫|笑道|沉声道)",')
lines.append(']')
lines.append('```')
lines.append('')
lines.append('**修改后** (speech_verb_detector.py)：')
lines.append('```python')
lines.append('SIMPLE_SPEECH_VERBS = [道,说,问,喊,叫,答,应,喝,嚷,骂,斥,吼]')
lines.append('EMOTION_MODIFIED_SPEECH = [笑道,叹道,怒道,沉声道,冷冷道,淡淡道,...]')
lines.append('```')
lines.append('')
lines.append('### P0-7: 移除 _recent_speakers.clear()')
lines.append('')
lines.append('**修改前** (speaker_matcher.py:1105)：')
lines.append('```python')
lines.append('def analyze_dialogue(self, text, chapter_id):')
lines.append('    self._recent_speakers.clear()')
lines.append('    self._recent_mentions.clear()')
lines.append('    self._character_activity.clear()')
lines.append('```')
lines.append('')
lines.append('**修改后** (speaker_matcher.py)：')
lines.append('```python')
lines.append('def analyze_dialogue(self, text, chapter_id):')
lines.append('    # 注意：不清空 _recent_speakers（原则8：跨段落保持活跃度）')
lines.append('')
lines.append('def reset_activity(self):  # 新增方法')
lines.append('    self._recent_speakers.clear()')
lines.append('    self._recent_mentions.clear()')
lines.append('    self._character_activity.clear()')
lines.append('```')
lines.append('')
lines.append('### P0-8: _infer_from_address 逻辑反转修复')
lines.append('')
lines.append('**修改前** (speaker_matcher.py:975-1034)：')
lines.append('```python')
lines.append('def _infer_from_address(self, context):')
lines.append('    addressed_char = find_addressed_character(text)')
lines.append('    # 找到被称呼的人后，从其他角色中猜说话人')
lines.append('    for char in all_chars:')
lines.append('        if char.id != addressed_char.id:')
lines.append('            candidates.append((char, 0.6 + activity*0.05, activity))')
lines.append('    return best_candidate')
lines.append('```')
lines.append('')
lines.append('**修改后** (speaker_matcher.py)：')
lines.append('```python')
lines.append('def _infer_from_address(self, context):')
lines.append('    # 已知谁被称呼 != 知道谁在说话，不猜测')
lines.append('    return None')
lines.append('```')
lines.append('')
lines.append('### 评估脚本修改: names_equivalent 宽松判断')
lines.append('')
lines.append('**新增** (evaluate_v6_improvements.py)：')
lines.append('```python')
lines.append('def names_equivalent(actual, expected):')
lines.append('    """允许修饰词差异：老者 ≈ 白发老者"""')
lines.append('    shorter, longer = sorted([actual, expected], key=len)')
lines.append('    if shorter in longer:')
lines.append('        diff = longer.replace(shorter, "")')
lines.append('        if all(c in "怒冷冷淡淡低高轻沉" for c in diff):')
lines.append('            return False')
lines.append('        return True')
lines.append('```')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 二、错误案例明细')
lines.append('')
lines.append('| 序号 | 对话内容 | 识别说话人 | 前文150字 | 后文150字 | 匹配原因 |')
lines.append('|------|---------|-----------|-----------|-----------|---------|')

for i, (dialogue, speaker_obj) in enumerate(results):
    name = speaker_obj.name if speaker_obj else '未知_无法推断'
    
    # Find position in text - try multiple quote variants
    cleaned = dialogue.strip()
    pos = -1
    # Search for the dialogue text directly (with or without quotes)
    p = full_text.find(cleaned)
    if p >= 0:
        # Verify it's inside quotes
        before_char = full_text[p-1] if p > 0 else ''
        after_char = full_text[p+len(cleaned)] if p+len(cleaned) < len(full_text) else ''
        if before_char in '"\u201c\u201d' or after_char in '"\u201d\u201c' or before_char in ['\u2018', '\u2019']:
            pos = p
        else:
            # Still use it even if not in quotes (the dialogue extraction found it)
            pos = p
    else:
        # Try without trailing punctuation
        for suffix in ['\u2026\u2026', '\u2026', '！', '。', '？', '!', '?', '\n']:
            if cleaned.endswith(suffix):
                p2 = full_text.find(cleaned[:-len(suffix)])
                if p2 >= 0:
                    pos = p2
                    cleaned = cleaned[:-len(suffix)]
                    break
    
    if pos >= 0:
        context_before = full_text[max(0,pos-150):pos]
        context_after = full_text[pos+len(cleaned):pos+len(cleaned)+150]
    else:
        context_before = '(未找到位置)'
        context_after = '(未找到位置)'
    
    short_before = context_before.replace('\n', ' ').replace('|', '｜').replace('"', '"').replace('"', '"')
    short_after = context_after.replace('\n', ' ').replace('|', '｜').replace('"', '"').replace('"', '"')
    short_dialogue = dialogue.replace('|', '｜')
    
    if speaker_obj:
        match_reason = '角色库匹配'
    elif '未知' in name:
        match_reason = '无匹配'
    else:
        match_reason = 'fallback'
    
    lines.append(f'| {i+1} | {short_dialogue[:40]} | {name} | ...{short_before[-60:]} | {short_after[:60]}... | {match_reason} |')

lines.append('')
lines.append('---')
lines.append('')
lines.append('## 三、角色库统计')
lines.append('')
chars = cm.get_all_characters()
lines.append(f'- 共创建 {len(chars)} 个角色')
lines.append('')
lines.append('| 角色名 | 性别 | 说明 |')
lines.append('|--------|------|------|')
for c in chars:
    gender = c.gender or '未知'
    lines.append(f'| {c.name} | {gender} | {"疑似角色" if c.gender else "疑似非角色"} |')

report_path = 'analysis_reports/修仙传错误案例+代码对照_20260513.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'报告已保存: {report_path}')
print(f'共 {len(results)} 条案例')
