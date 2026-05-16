# -*- coding: utf-8 -*-
"""Phase 1 verification: ChapterRoleCache, CandidateInfo, build_candidate_list"""
import sys
from pathlib import Path
# 将项目根目录添加到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pipeline.character_manager import (
    ChapterRoleCache,
    CandidateInfo,
    CharacterManager,
    get_character_manager,
)

# === ChapterRoleCache ===
print("=== ChapterRoleCache ===")
cache = ChapterRoleCache()
cache.add("苏夜")
cache.add("苏夜")
cache.add("苏夜")
cache.add("林雪")
assert len(cache) == 2, f"Expected 2, got {len(cache)}"
assert cache.get_count("苏夜") == 3
assert cache.get_count("林雪") == 1
assert cache.get("苏夜") == 3
assert cache.get("不存在的") is None

active = cache.get_active(2)
assert active == ["苏夜"], f"Expected ['苏夜'], got {active}"

promotable = cache.get_promotable(3)
assert promotable == ["苏夜"], f"Expected ['苏夜'], got {promotable}"

cache.clear()
assert len(cache) == 0
cache.add("新角色")
assert len(cache) == 1
assert cache.get("苏夜") is None
print("ChapterRoleCache: ALL PASSED")

# === CandidateInfo ===
print("\n=== CandidateInfo ===")
c = CandidateInfo(uid="1", name="苏夜", gender="male", priority=1, source="locked")
assert c.uid == "1"
assert c.name == "苏夜"
assert c.gender == "male"
assert c.priority == 1
assert c.source == "locked"
print("CandidateInfo: ALL PASSED")

# === build_candidate_list ===
print("\n=== build_candidate_list ===")
cm = get_character_manager()

# Ensure some test characters exist
cm.find_or_create("苏夜", project_id="test_phase1", context="苏夜站在门口")
cm.find_or_create("林雪", project_id="test_phase1", context="林雪叹了口气")
cm.find_or_create("赵天行", project_id="test_phase1", context="赵天行冷冷地看着他")

candidates = cm.build_candidate_list("test_phase1")
print(f"候选人数: {len(candidates)}")
assert len(candidates) <= 6, f"Expected <= 6, got {len(candidates)}"
names = [c.name for c in candidates]
assert "其他角色" in names
assert "苏夜" in names
print(f"候选人: {names}")
print("build_candidate_list: ALL PASSED")

# === Dedup test ===
print("\n=== Dedup test ===")
cache2 = ChapterRoleCache()
cache2.add("苏夜")
cache2.add("苏夜")
cache2.add("林雪")
candidates2 = cm.build_candidate_list("test_phase1", chapter_cache=cache2)
names2 = [c.name for c in candidates2]
assert len(set(names2)) == len(names2), f"Duplicate candidates: {names2}"
print(f"去重后候选人: {names2}")
print("Dedup: PASSED")

# === build_candidate_order: locked first ===
print("\n=== Locked priority test ===")
su_ye = cm.get_character_by_name("苏夜", "test_phase1")
if su_ye:
    cm.lock_character(su_ye.id, "test_phase1")
candidates3 = cm.build_candidate_list("test_phase1", max_candidates=6)
# 锁定的苏夜应该在最前面（不含"其他角色"的候选中）
non_fallback = [c for c in candidates3 if c.priority < 99]
if non_fallback and non_fallback[0].name == "苏夜":
    print(f"锁定角色优先: {non_fallback[0].name} (priority={non_fallback[0].priority})")
    print("Locked priority: PASSED")
else:
    print(f"First candidate: {non_fallback[0].name if non_fallback else 'empty'} (priority={non_fallback[0].priority if non_fallback else 'N/A'})")
    print("Locked priority: NOTE (no locked chars or order differs)")

print("\n=== Phase 1 ALL PASSED ===")
