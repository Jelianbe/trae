# -*- coding: utf-8 -*-
"""诊断NER效果，找出遗漏的实体"""
import sys
from pathlib import Path
import os
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '1'

from pipeline.nlp_basics import get_nlp, NLPBasics

# Patch to suppress prints
import pipeline.nlp_basics as nlp_basics
original_analyze = nlp_basics.NLPBasics.analyze
def quiet_analyze(self, text):
    import sys
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        result = original_analyze(self, text)
    finally:
        sys.stdout = old_stdout
    return result
nlp_basics.NLPBasics.analyze = quiet_analyze

# Load urban novel
urban_text = Path("tests/test_novel_urban.txt").read_text(encoding='utf-8')
with open("tests/test_novel_urban_ground_truth.json", encoding='utf-8') as f:
    gt = json.load(f)

gt_persons = set(gt["entities"]["persons"])
gt_orgs = set(gt["entities"]["organizations"])
gt_locations = set(gt["entities"]["locations"])
gt_all = gt_persons | gt_orgs | gt_locations

print("=" * 70)
print("NER 诊断报告 - 都市异能")
print("=" * 70)

# Analyze line by line
nlp = get_nlp()
lines = urban_text.split('\n')

detected_persons = set()
detected_orgs = set()
detected_locs = set()
missed_lines = {}

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Check if this line contains any GT entity
    has_gt = False
    for entity in gt_all:
        if entity in line:
            has_gt = True
            break
    
    if not has_gt:
        continue
    
    result = nlp.analyze(line)
    
    line_persons = set(e.text for e in result.entities if e.type == 'PER')
    line_orgs = set(e.text for e in result.entities if e.type == 'ORG')
    line_locs = set(e.text for e in result.entities if e.type == 'LOC')
    
    detected_persons.update(line_persons)
    detected_orgs.update(line_orgs)
    detected_locs.update(line_locs)
    
    # Check for missed entities
    for entity in gt_all:
        if entity in line and entity not in (line_persons | line_orgs | line_locs):
            if entity not in missed_lines:
                missed_lines[entity] = []
            missed_lines[entity].append(line)

print("\nGround Truth 实体:")
print(f"  人物: {gt_persons}")
print(f"  组织: {gt_orgs}")
print(f"  地点: {gt_locations}")

print("\n检测到的实体:")
print(f"  人物: {detected_persons}")
print(f"  组织: {detected_orgs}")
print(f"  地点: {detected_locs}")

print("\n遗漏的实体:")
missed_persons = gt_persons - detected_persons
missed_orgs = gt_orgs - detected_orgs
missed_locs = gt_locations - detected_locs

if missed_persons:
    print(f"  人物: {missed_persons}")
    for entity in missed_persons:
        print(f"    - '{entity}' 出现在以下行:")
        for line in missed_lines.get(entity, [])[:3]:
            print(f"      ...{line[:80]}...")
if missed_orgs:
    print(f"  组织: {missed_orgs}")
    for entity in missed_orgs:
        print(f"    - '{entity}' 出现在以下行:")
        for line in missed_lines.get(entity, [])[:3]:
            print(f"      ...{line[:80]}...")
if missed_locs:
    print(f"  地点: {missed_locs}")
    for entity in missed_locs:
        print(f"    - '{entity}' 出现在以下行:")
        for line in missed_lines.get(entity, [])[:3]:
            print(f"      ...{line[:80]}...")

# Calculate recall
person_recall = len(detected_persons & gt_persons) / len(gt_persons) if gt_persons else 1.0
org_recall = len(detected_orgs & gt_orgs) / len(gt_orgs) if gt_orgs else 1.0
loc_recall = len(detected_locs & gt_locations) / len(gt_locations) if gt_locations else 1.0
total_recall = len((detected_persons | detected_orgs | detected_locs) & gt_all) / len(gt_all) if gt_all else 1.0

print(f"\n召回率:")
print(f"  人物: {person_recall:.1%}")
print(f"  组织: {org_recall:.1%}")
print(f"  地点: {loc_recall:.1%}")
print(f"  总计: {total_recall:.1%}")

# Analyze false positives
all_detected = detected_persons | detected_orgs | detected_locs
false_positives = all_detected - gt_all
if false_positives:
    print(f"\n误检的实体（不在GT中）:")
    print(f"  {false_positives}")
