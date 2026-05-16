# -*- coding: utf-8 -*-
"""《修仙传》全文说话人识别测试 - 完整原文分析"""
import sys, os, tempfile, uuid, re
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
project_id = f'full_test_{uuid.uuid4().hex[:8]}'

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

# 按段落分割（保留原文结构）
paragraphs = content.split('\n\n')
total_dialogues = 0

for para_idx, paragraph in enumerate(paragraphs):
    if not paragraph.strip():
        continue
    
    # 跳过标题
    if paragraph.startswith('第') and '章' in paragraph[:10]:
        print(f"\n{'='*70}")
        print(f"{paragraph.strip()}")
        print(f"{'='*70}")
        sm.reset_activity()
        continue
    
    # 分析段落
    results = sm.analyze_dialogue(paragraph, chapter_id=para_idx)
    
    if results:
        for dialogue, speaker in results:
            total_dialogues += 1
            speaker_name = speaker.name if speaker else '未知'
            
            # 截取对话前后文
            preview = dialogue[:50] + ('...' if len(dialogue) > 50 else '')
            
            print(f"[{total_dialogues:3d}] [{speaker_name:>4s}] {preview}")

print(f"\n{'='*70}")
print(f"全文共识别 {total_dialogues} 个对话")
print(f"{'='*70}")

try:
    os.unlink(db_path)
except:
    pass
