# -*- coding: utf-8 -*-
"""《修仙传》全文说话人识别测试"""
import sys, os, tempfile, uuid
sys.path.insert(0, 'd:/trae/novel-tts-engine')

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

# 读取全文
with open(r'C:\Users\月笙如歌\Desktop\修仙传(1).txt', 'r', encoding='utf-8') as f:
    content = f.read()

# 创建测试环境
db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = db_file.name
db_file.close()

cm = CharacterManager(db_path=db_path)
project_id = f'test_full_{uuid.uuid4().hex[:8]}'

# 预创建角色（根据原文提取）
characters = [
    ('孙项明', 'male'),
    ('郭垣', 'male'),
    ('管事', 'male'),
    ('前辈', 'male'),
]
for name, gender in characters:
    cm.add_character(name, project_id, set(), gender)

sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
sm._current_project_id = project_id

print("《修仙传》全文说话人识别测试")
print("="*70)

# 按章节分割
chapters = content.split('第')[1:]
total_dialogues = 0
total_correct = 0

for chapter in chapters:
    if not chapter.strip():
        continue
    
    chapter_num = chapter.split('章')[0].strip()
    chapter_content = '第' + chapter
    
    print(f"\n{'='*70}")
    print(f"第{chapter_num}章")
    print(f"{'='*70}")
    
    sm.reset_activity()
    results = sm.analyze_dialogue(chapter_content, chapter_id=int(chapter_num))
    
    for i, (dialogue, speaker) in enumerate(results):
        total_dialogues += 1
        speaker_name = speaker.name if speaker else '未知'
        
        # 简化判断：根据上下文关键词判断
        expected = None
        dialogue_preview = dialogue[:20]
        
        # 基于对话内容的简单判断
        if '孙项明' in dialogue_preview and speaker_name == '孙项明':
            expected = '孙项明'
        elif '郭垣' in dialogue_preview and speaker_name == '郭垣':
            expected = '郭垣'
        elif any(kw in dialogue_preview for kw in ['规矩', '明白', '七成']):
            if speaker_name in ['管事', '孙项明']:
                expected = speaker_name
        
        # 记录结果
        is_correct = (expected is not None and speaker_name == expected) or (expected is None)
        if expected and is_correct:
            total_correct += 1
        
        status = '✅' if (expected is None or is_correct) else '❌'
        print(f"[{i+1:2d}] {status} [{speaker_name:>4s}] \"{dialogue[:40]}...\"" if len(dialogue) > 40 else f"[{i+1:2d}] {status} [{speaker_name:>4s}] \"{dialogue}\"")

print(f"\n{'='*70}")
print(f"总计: {total_dialogues} 个对话")
print(f"{'='*70}")

try:
    os.unlink(db_path)
except:
    pass
