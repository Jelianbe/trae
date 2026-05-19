"""标准化基线测试 — 统一入口（E2E 版本）

运行全部4个端到端基线测试并生成汇总报告。

架构说明：
- 所有测试使用公共 API analyze_dialogue
- 完整文本导入 → 自动分割 → 说话人识别
- 期望值来自标准答案文件，不依赖内部实现

用法: python tests/baseline/run_all_baselines.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 导入4个 E2E 测试模块
import test_urban_preset_e2e
import test_fantasy_preset_e2e
import test_urban_no_preset_e2e
import test_fantasy_no_preset_e2e


def main():
    print("=" * 70)
    print("标准化基线测试（E2E）")
    print("=" * 70)
    print()

    results = []

    # Test 1: 都市-有预注册
    print("[1/4] 都市-有预注册...")
    acc, total, correct, unknown, errors = test_urban_preset_e2e.run()
    judgable = total - unknown
    status = "PASS" if acc >= test_urban_preset_e2e.EXPECTED_BASELINE else "FAIL"
    results.append(('都市-有预注册', acc, judgable, correct, status, test_urban_preset_e2e.EXPECTED_BASELINE))
    for err_type, dialogue, expected, predicted in errors:
        print(f"  {err_type}: expected={expected}, got={predicted}  对话: {dialogue}")
    print()

    # Test 2: 西幻-有预注册
    print("[2/4] 西幻-有预注册...")
    acc, total, correct, unknown, errors = test_fantasy_preset_e2e.run()
    judgable = total - unknown
    status = "PASS" if acc >= test_fantasy_preset_e2e.EXPECTED_BASELINE else "FAIL"
    results.append(('西幻-有预注册', acc, judgable, correct, status, test_fantasy_preset_e2e.EXPECTED_BASELINE))
    for err_type, dialogue, expected, predicted in errors:
        print(f"  {err_type}: expected={expected}, got={predicted}  对话: {dialogue}")
    print()

    # Test 3: 都市-无预注册
    print("[3/4] 都市-无预注册...")
    acc, total, correct, unknown, errors = test_urban_no_preset_e2e.run()
    judgable = total - unknown
    status = "PASS" if acc >= test_urban_no_preset_e2e.EXPECTED_BASELINE else "FAIL"
    results.append(('都市-无预注册', acc, judgable, correct, status, test_urban_no_preset_e2e.EXPECTED_BASELINE))
    for err_type, dialogue, expected, predicted in errors:
        print(f"  {err_type}: expected={expected}, got={predicted}  对话: {dialogue}")
    print()

    # Test 4: 西幻-无预注册
    print("[4/4] 西幻-无预注册...")
    acc, total, correct, unknown, errors = test_fantasy_no_preset_e2e.run()
    judgable = total - unknown
    status = "PASS" if acc >= test_fantasy_no_preset_e2e.EXPECTED_BASELINE else "FAIL"
    results.append(('西幻-无预注册', acc, judgable, correct, status, test_fantasy_no_preset_e2e.EXPECTED_BASELINE))
    for err_type, dialogue, expected, predicted in errors:
        print(f"  {err_type}: expected={expected}, got={predicted}  对话: {dialogue}")
    print()

    # Summary
    print("=" * 70)
    print("基线测试汇总")
    print("=" * 70)
    print()
    all_pass = True
    for name, acc, judgable, correct, status, expected in results:
        mark = "PASS" if status == "PASS" else "FAIL"
        if status != "PASS": all_pass = False
        print(f"  {name}: {acc:.1f}% ({correct}/{judgable}, 预期≥{expected:.1f}%) [{mark}]")

    print()
    if all_pass:
        print("总体结果: ALL PASS")
    else:
        print("总体结果: FAIL")

    return all_pass


if __name__ == "__main__":
    main()
