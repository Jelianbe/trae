# -*- coding: utf-8 -*-
"""调试：SpeakerRoleFilter 的 _dialogue_entities 到底是什么"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from pipeline.nlp_basics import get_nlp, NLPBasics

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "tests", "test_novel_guimi_ch1-10.txt")

with open(SRC, "r", encoding="utf-8") as f:
    text = f.read()

sample = text[:3000]

print("=== 对话上下文提取 ===")

# 模式1：引号前15字
pattern1 = re.compile(r'["\u201c].*?["\u201d]')
for match in pattern1.finditer(sample):
    start = match.start()
    ctx = sample[max(0, start-15):start].strip()
    if ctx:
        print(f"  模式1: [{ctx}] -> 引号内: [{match.group()[:30]}...]")

# 模式2：引号后 XX说道
pattern2 = re.compile(r'["\u201d]\s*([^，。！？\n]{2,10}?)(?:说道|问道|喊道|笑道|道|说)')
for match in pattern2.finditer(sample):
    speaker = match.group(1).strip()
    if speaker:
        print(f"  模式2: 说话人候选=[{speaker}]")

# 模式4：是XX的声音
pattern4 = re.compile(r'["\u201d]([^。！？\n]{1,30}?)的(?:声音|话)')
for match in pattern4.finditer(sample):
    ctx = match.group(1).strip()
    if '是' in ctx:
        print(f"  模式4: [{ctx}]")

print("\n=== _extract_dialogue_entities 结果 ===")

nlp = get_nlp()
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker

semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
f = SpeakerRoleFilter(semantic_ranker=semantic_ranker)

# 手动调用
f._dialogue_entities = f._extract_dialogue_entities(sample, nlp)
print(f"_dialogue_entities = {f._dialogue_entities}")
print(f"_entity_scene_count = {f._entity_scene_count}")
