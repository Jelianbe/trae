"""隔离变量测试"""
import os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

import sys
sys.path.insert(0, '.')
import json
import time
from collections import defaultdict

from pipeline.hybrid_speaker_matcher import HybridSpeakerMatcher
from pipeline.speaker_matcher_interface import DialogueContext
from pipeline.character_manager import CharacterManager, ChapterRoleCache

TEST_DATA = json.load(open('tests/role_emotion_gt_100.json', encoding='utf-8'))

# 仅取 speaker 不为"未知"开头的可解条目（同 baseline 口径）
solvable = [d for d in TEST_DATA if d['speaker'] != '未知' and not d['speaker'].startswith('未知')]

# 按文体分组
by_style = defaultdict(list)
for d in solvable:
    by_style[d['style']].append(d)

print(f"可解条目: {len(solvable)}")
for style, items in by_style.items():
    print(f"  {style}: {len(items)} 条")

# 先创建角色库
char_manager = CharacterManager()
char_manager._current_project_id = "benchmark"

for d in solvable:
    char_manager.add_character(d['speaker'], d['speaker_gender'], "benchmark")
    for m in d.get('mentioned', []):
        char_manager.add_character(m, "male", "benchmark")

# 创建 matcher — 传入 char_manager
matcher = HybridSpeakerMatcher(char_manager, llm_model_name='Qwen/Qwen2.5-1.5B-Instruct')

matcher.current_project_id = "benchmark"

# 填充章节缓存
cache = ChapterRoleCache()
matcher.chapter_cache = cache

print(f"\n角色库: {len(char_manager.get_all_characters('benchmark'))} 个")
print("开始测试...\n")

results = {"total": 0, "correct": 0, "wrong": 0, "llm_used": 0, "llm_correct": 0,
           "rule_only": 0, "rule_correct": 0, "details": []}

t0 = time.time()
for d in solvable:
    ctx = DialogueContext(
        text=d['text'],
        speaker_hint=None,
        prev_speaker=None,
        context_before=d.get('context_before', ''),
        context_after=d.get('context_after', ''),
    )

    result = matcher.match_speaker(ctx)

    results['total'] += 1
    gt = d['speaker']
    is_correct = result and result.character.name == gt
    is_llm = result and result.match_type == 'llm'

    results['details'].append({
        'id': d['id'],
        'gt': gt,
        'predicted': result.character.name if result else 'None',
        'correct': is_correct,
        'type': result.match_type if result else 'none',
        'confidence': result.confidence if result else 0,
    })

    if is_correct:
        results['correct'] += 1
    else:
        results['wrong'] += 1

    if is_llm:
        results['llm_used'] += 1
        if is_correct:
            results['llm_correct'] += 1
    elif result and result.match_type == 'rule':
        results['rule_only'] += 1
        if is_correct:
            results['rule_correct'] += 1

elapsed = time.time() - t0

print(f"\n耗时: {elapsed:.1f}s")
print(f"LLM 调用: {matcher.get_stats()['llm_calls']} 次")
print(f"规则调用: {matcher.get_stats()['rule_matches']} 次")

print(f"\n=== 总体 ===")
print(f"  Total: {results['total']}")
print(f"  Correct: {results['correct']} ({results['correct'] / results['total'] * 100:.1f}%)")
print(f"  Wrong: {results['wrong']} ({results['wrong'] / results['total'] * 100:.1f}%)")

print(f"\n=== 规则 ===")
print(f"  Rule only: {results['rule_only']}")
print(f"  Rule correct: {results['rule_correct']} "
      f"({results['rule_correct'] / max(1, results['rule_only']) * 100:.1f}%)")

print(f"\n=== LLM 兜底 ===")
print(f"  LLM used: {results['llm_used']}")
print(f"  LLM correct: {results['llm_correct']} "
      f"({results['llm_correct'] / max(1, results['llm_used']) * 100:.1f}%)")

print(f"\n=== 错误详情 ===")
errors = [d for d in results['details'] if not d['correct']]
for e in errors:
    print(f"  {e['id']}  GT={e['gt']:10s}  pred={e['predicted']:10s}  "
          f"type={e['type']:5s}  conf={e['confidence']:.2f}")

# 按文体分
print(f"\n=== 按文体 ===")
for style, items in by_style.items():
    s_items = [r for r in results['details'] if r['id'] in {i['id'] for i in items}]
    s_correct = sum(1 for r in s_items if r['correct'])
    print(f"  {style}: {s_correct}/{len(s_items)} = {s_correct / len(s_items) * 100:.1f}%" if s_items else f"  {style}: 0/0")
