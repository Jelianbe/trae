# -*- coding: utf-8 -*-
"""Debug: why is "远超" being matched as speaker?"""
import sys
sys.path.insert(0, '.')

# First check if DialogueBoundaryDetector is over-filtering
from pipeline.dialogue_boundary_detector import DialogueBoundaryDetector

text = open(r'C:\Users\月笙如歌\Desktop\修仙传(1).txt', encoding='utf-8').read()

detector = DialogueBoundaryDetector()
results = detector.detect_all(text[:3000])

print("=== DialogueBoundaryDetector 过滤结果（前3000字） ===")
for r in results:
    qi = r.quote_info
    print(f"  对话: {qi.text[:40]}")
    print(f"    is_dialogue: {r.is_dialogue}, conf: {r.confidence:.2f}")
    print(f"    reasons: {r.reasons}")
    print(f"    suppressions: {r.suppression_reasons}")
    print()
