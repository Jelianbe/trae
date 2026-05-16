# -*- coding: utf-8 -*-
"""Phase 3 verification: PipelineRunner integration"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.pipeline_runner import PipelineRunner
from pipeline.hybrid_speaker_matcher import HybridSpeakerMatcher

# Test 1: Legacy mode (default)
print("=== Test 1: Legacy mode ===")
runner_legacy = PipelineRunner(speaker_matcher_type='legacy')
print(f"  Speaker matcher: {type(runner_legacy.speaker_matcher).__name__}")
assert type(runner_legacy.speaker_matcher).__name__ == 'SpeakerMatcher'
print("  PASSED")

# Test 2: Hybrid mode
print("\n=== Test 2: Hybrid mode ===")
runner_hybrid = PipelineRunner(speaker_matcher_type='hybrid')
print(f"  Speaker matcher: {type(runner_hybrid.speaker_matcher).__name__}")
assert isinstance(runner_hybrid.speaker_matcher, HybridSpeakerMatcher)
print("  PASSED")

# Test 3: Chapter cache initialized on hybrid
print("\n=== Test 3: Chapter cache ===")
assert hasattr(runner_hybrid.speaker_matcher, 'chapter_cache')
cache = runner_hybrid.speaker_matcher.chapter_cache
assert len(cache) == 0
print(f"  Cache empty: {len(cache) == 0}")
print("  PASSED")

# Test 4: Legacy mode has no chapter cache
print("\n=== Test 4: Legacy mode no cache ===")
assert not hasattr(runner_legacy.speaker_matcher, 'chapter_cache') or \
       runner_legacy.speaker_matcher is None or \
       not hasattr(runner_legacy.speaker_matcher, 'chapter_cache') or \
       runner_legacy.speaker_matcher.chapter_cache is None or \
       len(runner_legacy.speaker_matcher.chapter_cache) == 0
print("  Legacy has no chapter cache (or empty)")
print("  PASSED")

print("\n=== Phase 3 ALL PASSED ===")
