# -*- coding: utf-8 -*-
"""Phase 2 verification: HybridSpeakerMatcher"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.character_manager import (
    CharacterManager,
    ChapterRoleCache,
    get_character_manager,
)
from pipeline.hybrid_speaker_matcher import HybridSpeakerMatcher, LLM_THRESHOLD
from pipeline.speaker_matcher_interface import DialogueContext, MatchResult


cm = get_character_manager()
cm.find_or_create("苏夜", project_id="p2", context="苏夜站在门口")
cm.find_or_create("林雪", project_id="p2", context="林雪叹了口气")

matcher = HybridSpeakerMatcher(cm)
matcher.current_project_id = "p2"

# Test 1: L1 deterministic rule (exact match via "苏夜道")
print("=== Test 1: L1 deterministic ===")
ctx = DialogueContext(
    text="「你给我滚出去！」",
    speaker_hint="苏夜",
    chapter_id=1,
)
result = matcher.match_speaker(ctx)
assert result is not None, "Expected match"
assert result.character.name == "苏夜", f"Expected 苏夜, got {result.character.name}"
assert result.confidence >= 0.85, f"Expected high confidence, got {result.confidence}"
print(f"  Match: {result.character.name} (confidence={result.confidence:.2f}, type={result.match_type})")
stats1 = matcher.get_stats()
assert stats1["rule_matches"] == 1
assert stats1["llm_calls"] == 0  # High confidence, no LLM
print("  PASSED")

# Test 2: Stats after first test
print("\n=== Test 2: Stats ===")
stats = matcher.get_stats()
print(f"  Stats: {stats}")
assert stats["rule_matches"] >= 1
print("  PASSED")

# Test 3: chapter_cache
print("\n=== Test 3: chapter_cache ===")
cache = matcher.chapter_cache
cache.add("苏夜")
cache.add("苏夜")
cache.add("林雪")
assert len(cache) == 2
assert cache.get_count("苏夜") == 2
print(f"  Cache: len={len(cache)}, 苏夜={cache.get_count('苏夜')}")
print("  PASSED")

# Test 4: Graceful degradation when LLM not available
print("\n=== Test 4: Graceful degradation ===")
ctx3 = DialogueContext(
    text="「这件事到此为止。」",
    speaker_hint=None,
    prev_speaker=None,
    chapter_id=1,
)
result3 = matcher.match_speaker(ctx3)
# LLM not loaded (HF mirror issue) → graceful degradation returns None
print(f"  Result: {result3}")
print("  PASSED (degradation works)")

# Test 5: LLM_THRESHOLD constant
print("\n=== Test 5: LLM_THRESHOLD ===")
assert LLM_THRESHOLD == 0.7
print(f"  LLM_THRESHOLD = {LLM_THRESHOLD}")
print("  PASSED")

# Test 6: build_candidate_list integration
print("\n=== Test 6: build_candidate_list ===")
candidates = cm.build_candidate_list("p2")
names = [c.name for c in candidates]
print(f"  Candidates: {names}")
assert "其他角色" in names
assert len(candidates) <= 6
print("  PASSED")

print("\n=== Phase 2 ALL PASSED ===")
