# -*- coding: utf-8 -*-
"""稳定性测试脚本：对每个测试文本运行N轮评估，记录平均值和标准差
支持新旧两套评估体系对比

命令行参数:
  --quick        快速模式：跳过聚类，只运行核心评估
  --runs N       测试轮数（默认3）
  --text NAME    单文本测试（urban/western/cultivation/all）
"""

import sys
import json
import statistics
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

sys.path.insert(0, str(Path(__file__).parent))

from evaluate_generalization_v3 import evaluate_novel

TEST_CASES = {
    "urban": ("tests/test_novel_urban.txt", "tests/test_novel_urban_ground_truth.json", "都市异能"),
    "western": ("tests/test_novel_western.txt", "tests/test_novel_western_ground_truth.json", "西幻"),
    "cultivation": ("tests/test_novel.txt", "tests/test_novel_ground_truth.json", "修仙"),
}

# 旧版五项模块
OLD_MODULES = ["章节划分", "对话分类", "拟声词检测", "命名实体识别", "说话人匹配"]

# 新版六项模块
NEW_MODULES = ["基础结构完整性", "拟声词检测", "说话角色识别", "对话-角色匹配", "端到端正确率"]


def compute_stability_penalty(run_results, metric_key):
    """计算稳定性罚分：基于标准差，最多扣5分"""
    values = [r[metric_key] for r in run_results]
    if len(values) < 2:
        return 0.0
    stdev = statistics.stdev(values)
    return min(5.0, stdev * 2)


def compute_new_composite_with_penalty(run_results):
    """计算带罚分的新版综合分"""
    penalties = {}
    stdev_sum = 0.0
    
    for module in NEW_MODULES:
        values = [r[module] for r in run_results]
        if len(values) >= 2:
            stdev = statistics.stdev(values)
            stdev_sum += stdev
    
    penalty = min(5.0, stdev_sum * 2)
    return penalty


def run_stability_test(quick_mode=False, num_runs=3, test_cases=None):
    """运行稳定性测试
    
    Args:
        quick_mode: 快速模式，跳过 EntityClusterer
        num_runs: 测试轮数
        test_cases: 测试用例列表，默认为所有测试文本
    """
    if test_cases is None:
        test_cases = list(TEST_CASES.values())
    
    quick_label = '是' if quick_mode else '否'
    print(f"\n{'='*60}")
    print(f"稳定性测试 v2.1 | 轮次={num_runs} | 文本={len(test_cases)} | 快速模式={quick_label}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    all_results = {}
    
    for novel_path, gt_path, style_name in test_cases:
        print(f"\n{'─'*60}")
        print(f"测试文本: {style_name} ({novel_path})")
        print(f"{'─'*60}\n")
        
        run_results = []
        for i in range(num_runs):
            print(f"  第 {i+1} 轮 / {num_runs} ...", end=" ", flush=True)
            scores = evaluate_novel(novel_path, gt_path)
            run_results.append(scores)
            print(f"完成 [旧版平均={scores['平均得分']:.1f}, 新版综合={scores['综合分']:.1f}]")
        
        old_stats = compute_statistics(run_results, OLD_MODULES)
        new_stats = compute_statistics(run_results, NEW_MODULES + ["综合分"])
        
        # 计算稳定性罚分
        stability_penalty = compute_new_composite_with_penalty(run_results)
        
        all_results[style_name] = {
            "runs": run_results,
            "old_stats": old_stats,
            "new_stats": new_stats,
            "stability_penalty": round(stability_penalty, 2),
        }
    
    print_stability_report(all_results)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f"analysis_reports/测试报告/稳定性测试报告_{timestamp}.md"
    save_stability_report(all_results, report_path, num_runs=num_runs, test_cases=test_cases)
    
    print(f"\n报告已保存至: {report_path}")


def compute_statistics(run_results, modules, include_average=True):
    stats = {}
    for module in modules:
        values = [r[module] for r in run_results]
        stats[module] = {
            "mean": statistics.mean(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "values": values,
        }

    if include_average and "平均得分" not in stats:
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
    print(f"稳定性测试报告（新旧对比）")
    print(f"{'='*60}\n")
    
    for style_name, data in all_results.items():
        old_stats = data["old_stats"]
        new_stats = data["new_stats"]
        runs = data["runs"]
        penalty = data["stability_penalty"]
        
        # 旧版报告
        print(f"\n{'─'*40}")
        print(f"  {style_name} - 旧版五项")
        print(f"{'─'*40}")
        print(f"\n  {'模块':<10} {'平均值':>8} {'标准差':>8} {'波动范围':>12} {'状态':>8}")
        print(f"  {'─'*50}")
        
        for module in OLD_MODULES + ["平均得分"]:
            s = old_stats[module]
            stdev_str = f"±{s['stdev']:.2f}"
            range_str = f"{s['min']:.1f} ~ {s['max']:.1f}"
            status = "✅ 稳定" if s["stdev"] < 2.0 else "⚠️ 波动" if s["stdev"] < 5.0 else "❌ 不稳定"
            print(f"  {module:<10} {s['mean']:>8.1f} {stdev_str:>8} {range_str:>12} {status:>8}")
        
        # 新版报告
        print(f"\n{'─'*40}")
        print(f"  {style_name} - 新版六项")
        print(f"{'─'*40}")
        print(f"\n  {'模块':<10} {'权重':>6} {'平均值':>8} {'标准差':>8} {'状态':>8}")
        print(f"  {'─'*48}")
        
        weights = {
            "基础结构完整性": "10%",
            "拟声词检测": "15%",
            "说话角色识别": "30%",
            "对话-角色匹配": "30%",
            "端到端正确率": "10%",
        }
        
        for module in NEW_MODULES:
            s = new_stats[module]
            stdev_str = f"±{s['stdev']:.2f}"
            status = "✅ 稳定" if s["stdev"] < 2.0 else "⚠️ 波动" if s["stdev"] < 5.0 else "❌ 不稳定"
            print(f"  {module:<10} {weights.get(module, '  '):>6} {s['mean']:>8.1f} {stdev_str:>8} {status:>8}")
        
        print(f"\n  稳定性罚分: -{penalty:.2f}")
        s = new_stats["综合分"]
        print(f"  综合分（含罚分）: {s['mean']:.1f} - {penalty:.2f} = {s['mean'] - penalty:.1f}")
        
        print(f"\n  逐轮详情:")
        for i, run in enumerate(runs):
            print(f"    轮次{i+1}: 旧版平均={run['平均得分']:.1f}, 新版综合={run['综合分']:.1f}")
            print(f"             基础={run['基础结构完整性']:.1f}, 拟声={run['拟声词检测']:.1f}, "
                  f"角色识别={run['说话角色识别']:.1f}, 角色匹配={run['对话-角色匹配']:.1f}, "
                  f"端到端={run['端到端正确率']:.1f}")


def save_stability_report(all_results, report_path, num_runs=3, test_cases=None):
    """保存稳定性测试报告
    
    Args:
        all_results: 测试结果字典
        report_path: 报告文件路径
        num_runs: 测试轮数
        test_cases: 测试用例列表
    """
    if test_cases is None:
        test_cases = list(TEST_CASES.values())
    
    weights = {
        "基础结构完整性": "10%",
        "拟声词检测": "15%",
        "说话角色识别": "30%",
        "对话-角色匹配": "30%",
        "端到端正确率": "10%",
    }
    
    lines = []
    lines.append(f"# 稳定性测试报告（评估体系重构版）\n\n")
    lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**测试轮次**: {num_runs}\n")
    lines.append(f"**测试文本**: {', '.join(s for _, _, s in test_cases)}\n\n")
    lines.append("---\n\n")
    
    # 新旧评估体系对比
    lines.append(f"## 新旧评估体系对比\n\n")
    lines.append(f"| 指标 | 权重 | 说明 |\n")
    lines.append(f"|------|------|------|\n")
    lines.append(f"| 基础结构完整性 | 10% | 原章节划分+对话分类合并 |\n")
    lines.append(f"| 拟声词检测 | 15% | 保持独立，权重不变 |\n")
    lines.append(f"| 说话角色识别 | 30% | 原NER重命名 |\n")
    lines.append(f"| 对话-角色匹配 | 30% | 原说话人匹配 |\n")
    lines.append(f"| 端到端正确率 | 10% | 新增：对话被正确识别且匹配到正确说话人的比例 |\n")
    lines.append(f"| 系统稳定性罚分 | 最多-5分 | 基于标准差，公式: min(5.0, stdev_sum × 2) |\n\n")
    lines.append("---\n\n")
    
    for style_name, data in all_results.items():
        old_stats = data["old_stats"]
        new_stats = data["new_stats"]
        runs = data["runs"]
        penalty = data["stability_penalty"]
        
        lines.append(f"## {style_name}\n\n")
        
        # 旧版统计
        lines.append(f"### 旧版五项指标\n\n")
        lines.append(f"| 模块 | 平均值 | 标准差 | 波动范围 | 状态 |")
        lines.append(f"|------|--------|--------|----------|------|")
        
        for module in OLD_MODULES + ["平均得分"]:
            s = old_stats[module]
            stdev_str = f"±{s['stdev']:.2f}"
            range_str = f"{s['min']:.1f} ~ {s['max']:.1f}"
            status = "✅ 稳定" if s["stdev"] < 2.0 else "⚠️ 波动" if s["stdev"] < 5.0 else "❌ 不稳定"
            lines.append(f"| {module} | {s['mean']:.1f} | {stdev_str} | {range_str} | {status} |")
        
        # 新版统计
        lines.append(f"\n### 新版六项指标\n\n")
        lines.append(f"| 模块 | 权重 | 平均值 | 标准差 | 状态 |")
        lines.append(f"|------|------|--------|--------|------|")
        
        for module in NEW_MODULES:
            s = new_stats[module]
            stdev_str = f"±{s['stdev']:.2f}"
            status = "✅ 稳定" if s["stdev"] < 2.0 else "⚠️ 波动" if s["stdev"] < 5.0 else "❌ 不稳定"
            lines.append(f"| {module} | {weights.get(module, '')} | {s['mean']:.1f} | {stdev_str} | {status} |")
        
        s = new_stats["综合分"]
        lines.append(f"\n**稳定性罚分**: -{penalty:.2f}\n")
        lines.append(f"**综合分（含罚分）**: {s['mean']:.1f} - {penalty:.2f} = **{s['mean'] - penalty:.1f}**\n")
        
        lines.append(f"\n### 逐轮详情\n\n")
        for i, run in enumerate(runs):
            lines.append(f"- **轮次{i+1}**: 旧版平均={run['平均得分']:.1f}, 新版综合={run['综合分']:.1f}")
            lines.append(f"  - 基础={run['基础结构完整性']:.1f}, 拟声={run['拟声词检测']:.1f}, "
                        f"角色识别={run['说话角色识别']:.1f}, 角色匹配={run['对话-角色匹配']:.1f}, "
                        f"端到端={run['端到端正确率']:.1f}")
        lines.append("\n---\n\n")
    
    # 差异分析
    lines.append("## 差异分析\n\n")
    lines.append("以下模块标准差 ≥ 2.0，需要进一步分析：\n\n")
    
    has_diff = False
    for style_name, data in all_results.items():
        for module in OLD_MODULES:
            s = data["old_stats"][module]
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
    parser = argparse.ArgumentParser(description='稳定性测试脚本')
    parser.add_argument('--quick', action='store_true', help='快速模式：跳过EntityClusterer，只运行核心评估')
    parser.add_argument('--runs', type=int, default=3, help='测试轮数（默认3）')
    parser.add_argument('--text', choices=['urban', 'western', 'cultivation', 'all'], default='all', help='测试文本类型')
    
    args = parser.parse_args()
    
    # 选择测试文本
    if args.text == 'all':
        test_cases = list(TEST_CASES.values())
    else:
        test_cases = [TEST_CASES[args.text]]
    
    run_stability_test(
        quick_mode=args.quick,
        num_runs=args.runs,
        test_cases=test_cases
    )
