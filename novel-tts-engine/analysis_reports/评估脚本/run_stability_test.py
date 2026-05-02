# -*- coding: utf-8 -*-
"""稳定性测试脚本：对每个测试文本运行N轮评估，记录平均值和标准差"""

import sys
import json
import statistics
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

sys.path.insert(0, str(Path(__file__).parent))

from evaluate_generalization_v3 import evaluate_novel

TEST_CASES = [
    ("tests/test_novel_urban.txt", "tests/test_novel_urban_ground_truth.json", "都市异能"),
    ("tests/test_novel_western.txt", "tests/test_novel_western_ground_truth.json", "西幻"),
    ("tests/test_novel.txt", "tests/test_novel_ground_truth.json", "修仙"),
]

NUM_RUNS = 3

MODULES = ["章节划分", "对话分类", "拟声词检测", "命名实体识别", "说话人匹配"]


def run_stability_test():
    print(f"\n{'='*60}")
    print(f"稳定性测试 v1.0 | 轮次={NUM_RUNS} | 文本={len(TEST_CASES)}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    all_results = {}
    
    for novel_path, gt_path, style_name in TEST_CASES:
        print(f"\n{'─'*60}")
        print(f"测试文本: {style_name} ({novel_path})")
        print(f"{'─'*60}\n")
        
        run_results = []
        for i in range(NUM_RUNS):
            print(f"  第 {i+1} 轮 / {NUM_RUNS} ...", end=" ", flush=True)
            scores = evaluate_novel(novel_path, gt_path)
            run_results.append(scores)
            print(f"完成 [章节={scores['章节划分']:.1f}, 对话={scores['对话分类']:.1f}, "
                  f"SFX={scores['拟声词检测']:.1f}, NER={scores['命名实体识别']:.1f}, "
                  f"说话人={scores['说话人匹配']:.1f}]")
        
        stats = compute_statistics(run_results)
        all_results[style_name] = {
            "runs": run_results,
            "stats": stats,
        }
    
    print_stability_report(all_results)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f"analysis_reports/测试报告/稳定性测试报告_{timestamp}.md"
    save_stability_report(all_results, report_path)
    
    print(f"\n报告已保存至: {report_path}")


def compute_statistics(run_results):
    stats = {}
    for module in MODULES:
        values = [r[module] for r in run_results]
        stats[module] = {
            "mean": statistics.mean(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "values": values,
        }
    
    mean_values = [r["平均得分"] for r in run_results]
    stats["平均得分"] = {
        "mean": statistics.mean(mean_values),
        "stdev": statistics.stdev(mean_values) if len(mean_values) > 1 else 0.0,
        "min": min(mean_values),
        "max": max(mean_values),
        "values": mean_values,
    }
    
    return stats


def print_stability_report(all_results):
    print(f"\n{'='*60}")
    print(f"稳定性测试报告")
    print(f"{'='*60}\n")
    
    for style_name, data in all_results.items():
        stats = data["stats"]
        runs = data["runs"]
        
        print(f"\n{'─'*40}")
        print(f"  {style_name}")
        print(f"{'─'*40}")
        print(f"\n  {'模块':<10} {'平均值':>8} {'标准差':>8} {'波动范围':>12} {'状态':>8}")
        print(f"  {'─'*50}")
        
        for module in MODULES + ["平均得分"]:
            s = stats[module]
            stdev_str = f"±{s['stdev']:.2f}"
            range_str = f"{s['min']:.1f} ~ {s['max']:.1f}"
            status = "✅ 稳定" if s["stdev"] < 2.0 else "⚠️ 波动" if s["stdev"] < 5.0 else "❌ 不稳定"
            print(f"  {module:<10} {s['mean']:>8.1f} {stdev_str:>8} {range_str:>12} {status:>8}")
        
        print(f"\n  逐轮详情:")
        for i, run in enumerate(runs):
            print(f"    轮次{i+1}: 章节={run['章节划分']:.1f}, 对话={run['对话分类']:.1f}, "
                  f"SFX={run['拟声词检测']:.1f}, NER={run['命名实体识别']:.1f}, "
                  f"说话人={run['说话人匹配']:.1f}, 平均={run['平均得分']:.1f}")


def save_stability_report(all_results, report_path):
    lines = []
    lines.append(f"# 稳定性测试报告\n\n")
    lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**测试轮次**: {NUM_RUNS}\n")
    lines.append(f"**测试文本**: {', '.join(s for _, _, s in TEST_CASES)}\n\n")
    lines.append("---\n\n")
    
    for style_name, data in all_results.items():
        stats = data["stats"]
        runs = data["runs"]
        
        lines.append(f"## {style_name}\n\n")
        lines.append(f"### 统计结果\n\n")
        lines.append(f"| 模块 | 平均值 | 标准差 | 波动范围 | 状态 |")
        lines.append(f"|------|--------|--------|----------|------|")
        
        for module in MODULES + ["平均得分"]:
            s = stats[module]
            stdev_str = f"±{s['stdev']:.2f}"
            range_str = f"{s['min']:.1f} ~ {s['max']:.1f}"
            status = "✅ 稳定" if s["stdev"] < 2.0 else "⚠️ 波动" if s["stdev"] < 5.0 else "❌ 不稳定"
            lines.append(f"| {module} | {s['mean']:.1f} | {stdev_str} | {range_str} | {status} |")
        
        lines.append(f"\n### 逐轮详情\n\n")
        for i, run in enumerate(runs):
            lines.append(f"- **轮次{i+1}**: 章节={run['章节划分']:.1f}, 对话={run['对话分类']:.1f}, "
                        f"SFX={run['拟声词检测']:.1f}, NER={run['命名实体识别']:.1f}, "
                        f"说话人={run['说话人匹配']:.1f}, 平均={run['平均得分']:.1f}")
        lines.append("\n---\n\n")
    
    lines.append("## 差异分析\n\n")
    lines.append("以下模块标准差 ≥ 2.0，需要进一步分析：\n\n")
    
    has_diff = False
    for style_name, data in all_results.items():
        for module in MODULES:
            s = data["stats"][module]
            if s["stdev"] >= 2.0:
                has_diff = True
                lines.append(f"### {style_name} - {module} (标准差: {s['stdev']:.2f})\n\n")
                lines.append(f"- 轮次1: {s['values'][0]:.1f}\n")
                lines.append(f"- 轮次2: {s['values'][1]:.1f}\n")
                lines.append(f"- 轮次3: {s['values'][2]:.1f}\n")
                lines.append(f"- 波动范围: {s['min']:.1f} ~ {s['max']:.1f}\n\n")
    
    if not has_diff:
        lines.append("**无差异模块**：所有模块标准差均 < 2.0，测试结果稳定。\n\n")
    
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


if __name__ == "__main__":
    run_stability_test()
