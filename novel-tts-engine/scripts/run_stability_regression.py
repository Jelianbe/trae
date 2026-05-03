# -*- coding: utf-8 -*-
"""
三轮稳定性回归测试

目的：确认当前 NER 指标的稳定性，确保不是偶然结果。

测试轮次：
1. 第一轮：斗破苍穹 NER 重新运行（5次取平均）
2. 第二轮：跨文体验证（都市/西幻/修真）
3. 第三轮：管道一致性测试（9个单元测试）
"""
import sys
from pathlib import Path
import json
import statistics

# 设置项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analysis_reports.评估脚本.evaluate_generalization_v3 import evaluate_ner
import subprocess

print("=" * 80)
print("三轮稳定性回归测试")
print("=" * 80)

# ============================================================
# 第一轮：斗破苍穹 NER 重新运行（5次取平均）
# ============================================================
print("\n" + "=" * 80)
print("【第一轮】斗破苍穹 NER 稳定性测试（5次运行）")
print("=" * 80)

text_file = project_root / 'tests' / 'test_novel_doupo_ch1-10.txt'
gt_file = project_root / 'tests' / 'test_novel_doupo_ground_truth.json'

text = text_file.read_text(encoding='utf-8')
gt = json.load(gt_file.open(encoding='utf-8'))

scores = []
for i in range(5):
    score = evaluate_ner(text, gt.get("entities", {}))
    scores.append(score)
    print(f"  第{i+1}次运行: NER F1 = {score}")

mean_score = statistics.mean(scores)
median_score = statistics.median(scores)
min_score = min(scores)
max_score = max(scores)
stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0

print(f"\n【第一轮结果】")
print(f"  平均值: {mean_score:.1f}")
print(f"  中位数: {median_score:.1f}")
print(f"  最小值: {min_score}")
print(f"  最大值: {max_score}")
print(f"  标准差: {stdev_score:.2f}")

round1_passed = mean_score >= 95.0 and stdev_score <= 2.0
print(f"  状态: {'✅ 通过' if round1_passed else '❌ 未通过'}")
if not round1_passed:
    print(f"  ⚠️ 平均值{mean_score:.1f} < 95.0 或 标准差{stdev_score:.2f} > 2.0")

# ============================================================
# 第二轮：跨文体验证（都市/西幻/修真）
# ============================================================
print("\n" + "=" * 80)
print("【第二轮】跨文体验证")
print("=" * 80)

# 检查可用的测试文件
test_files = [
    {
        'name': '都市爽文',
        'text': project_root / 'tests' / 'test_novel_urban_ch1-3.txt',
        'gt': project_root / 'tests' / 'test_novel_urban_ground_truth.json',
        'baseline': 90.9,
    },
    {
        'name': '西幻爽文',
        'text': project_root / 'tests' / 'test_novel_western_ch1-3.txt',
        'gt': project_root / 'tests' / 'test_novel_western_ground_truth.json',
        'baseline': 100.0,
    },
    {
        'name': '修真爽文',
        'text': project_root / 'tests' / 'test_novel_cultivation_ch1-3.txt',
        'gt': project_root / 'tests' / 'test_novel_cultivation_ground_truth.json',
        'baseline': 100.0,
    },
]

round2_passed = True
results_round2 = []

for test in test_files:
    if not test['text'].exists():
        print(f"\n  【{test['name']}】⚠️ 测试文件不存在，跳过")
        continue
    
    print(f"\n  【{test['name']}】")
    
    try:
        text = test['text'].read_text(encoding='utf-8')
        gt = json.load(test['gt'].open(encoding='utf-8'))
        
        score = evaluate_ner(text, gt.get("entities", {}))
        results_round2.append((test['name'], score, test['baseline']))
        
        status = "✅" if score >= test['baseline'] else "❌"
        print(f"    NER F1: {score} (基线: {test['baseline']}) {status}")
        
        if score < test['baseline']:
            round2_passed = False
            print(f"    ⚠️ 低于基线 {test['baseline']}")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        round2_passed = False

if results_round2:
    print(f"\n  【第二轮结果】")
    print(f"  状态: {'✅ 通过' if round2_passed else '❌ 未通过'}")

# ============================================================
# 第三轮：管道一致性测试
# ============================================================
print("\n" + "=" * 80)
print("【第三轮】管道一致性测试")
print("=" * 80)

result = subprocess.run(
    [sys.executable, '-m', 'pytest', str(project_root / 'tests' / 'test_pipeline_consistency.py'), '-v'],
    capture_output=True,
    text=True,
    cwd=str(project_root)
)

print(result.stdout)

round3_passed = result.returncode == 0
if result.stderr:
    print(f"\n【错误输出】")
    print(result.stderr)

# ============================================================
# 汇总结果
# ============================================================
print("\n" + "=" * 80)
print("【测试汇总】")
print("=" * 80)

print(f"\n  第一轮（斗破NER稳定性）: {'✅ 通过' if round1_passed else '❌ 未通过'}")
print(f"    平均F1: {mean_score:.1f}, 标准差: {stdev_score:.2f}")
print(f"\n  第二轮（跨文体验证）: {'✅ 通过' if round2_passed else '❌ 未通过'}")
for name, score, baseline in results_round2:
    status = "✅" if score >= baseline else "❌"
    print(f"    {name}: {score} (基线: {baseline}) {status}")
print(f"\n  第三轮（管道一致性）: {'✅ 通过' if round3_passed else '❌ 未通过'}")
print(f"    9个单元测试全部通过" if round3_passed else "    存在失败的测试")

print(f"\n{'=' * 80}")
all_passed = round1_passed and round2_passed and round3_passed
if all_passed:
    print("✅ 三轮稳定性回归测试全部通过")
    print("   当前版本稳定性良好，可以安全地进行后续改动")
else:
    print("❌ 存在未通过的测试轮次")
    print("   建议先调查失败原因，再进行后续开发")
print(f"{'=' * 80}")
