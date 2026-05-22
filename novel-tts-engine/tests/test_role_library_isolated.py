# -*- coding: utf-8 -*-
"""L2 真实场景测试：角色库集成测试（项目隔离版 - 测试数据驱动）

用途：模拟真实运行场景，每个项目（文体）独立建库、独立测试
预注册：❌ 否
角色库：✅ 从测试数据 context 构建，按 project_id 隔离

策略：从测试数据的 context_before/context_after 提取角色，构建角色库
     这样角色库中的角色与测试数据完全匹配

分层：
- L2a: 现有晋升机制（≥3次）
- L2b: 临时角色直接视为正式（门槛=1次）
"""

import sys
import os
import json
import time
import tempfile
import re

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.character_manager import CharacterManager
from pipeline.legacy_rule_matcher import LegacyRuleMatcher
from pipeline.speaker_matcher_interface import DialogueContext
from utils.config import PROMOTION_THRESHOLD


# 文体 → project_id 映射（仅短文本，超长文本后续测试）
STYLE_PROJECT_MAP = {
    "都市": "urban_test",
    "修仙": "xiuxian_test",
    # "西幻": "western_fantasy_test",  # 超长文本，后续测试
    # "历史": "history_test",  # 超长文本，后续测试
}


def load_test_data():
    """加载测试数据（GT）"""
    gt_path = os.path.join(PROJECT_ROOT, "tests", "role_emotion_gt_300.json")
    if not os.path.exists(gt_path):
        gt_path = os.path.join(PROJECT_ROOT, "tests", "role_emotion_gt_100.json")
    
    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"加载测试数据: {len(data)} 条")
    return data


def extract_roles_from_test_data(test_data_by_style, style):
    """从测试数据提取角色信息
    
    从 context_before/context_after 中提取出现的人名作为角色
    
    Args:
        test_data_by_style: 按文体分组的测试数据
        style: 文体类型
        
    Returns:
        Dict[role_name, frequency] - 角色名 → 出现频次
    """
    role_freq = {}
    
    if style not in test_data_by_style:
        return role_freq
    
    style_data = test_data_by_style[style]
    
    for item in style_data:
        context_before = item.get('context_before', '') or ''
        context_after = item.get('context_after', '') or ''
        context = context_before + ' ' + context_after
        
        # 提取 speaker 和 listener
        speaker = item.get('speaker', '')
        listener = item.get('listener', '')
        mentioned = item.get('mentioned', [])
        
        # 统计角色出现频次
        for name in [speaker, listener] + mentioned:
            if name and name not in ('未知', 'Unknown', ''):
                role_freq[name] = role_freq.get(name, 0) + 1
    
    return role_freq


def build_role_library_from_test_data(role_freq, project_id, promotion_threshold=None):
    """从测试数据提取的角色频次构建角色库
    
    Args:
        role_freq: Dict[role_name, frequency] - 角色名 → 出现频次
        project_id: 项目 ID
        promotion_threshold: 晋升阈值（None 使用默认值）
        
    Returns:
        (CharacterManager, db_path)
    """
    # 创建临时数据库
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    cm = CharacterManager(db_path)
    
    # 如果有晋升阈值覆盖，需要修改 config
    if promotion_threshold is not None:
        import utils.config as cfg
        original_threshold = cfg.PROMOTION_THRESHOLD
        cfg.PROMOTION_THRESHOLD = promotion_threshold
    
    try:
        # 导入角色到数据库
        for role_name, freq in role_freq.items():
            # 如果频次 >= 晋升阈值，添加为正式角色
            if freq >= (promotion_threshold or 3):
                cm.add_character(
                    name=role_name,
                    project_id=project_id
                )
                # 多次调用 increment_frequency 来设置频次
                for _ in range(freq):
                    cm.increment_frequency(role_name, project_id)
            else:
                # 否则添加为临时角色
                cm.add_temp_character(
                    name=role_name,
                    project_id=project_id
                )
                # 设置临时角色频次
                if project_id not in cm._frequency_map:
                    cm._frequency_map[project_id] = {}
                cm._frequency_map[project_id][role_name] = freq
                if role_name in cm._temp_chars:
                    cm._temp_chars[role_name].mention_count = freq
        
        formal_count = len(cm.get_all_characters(project_id))
        temp_count = len(cm.get_all_temp_characters())
        print(f"  角色库构建完成 [{project_id}]:")
        print(f"    唯一角色数: {len(role_freq)}")
        print(f"    正式角色数: {formal_count}")
        print(f"    临时角色数: {temp_count}")
    finally:
        if promotion_threshold is not None:
            import utils.config as cfg
            cfg.PROMOTION_THRESHOLD = original_threshold
    
    return cm, db_path


def create_dialogue_context(item):
    """从测试数据创建 DialogueContext"""
    text = item.get('text', '')
    context_before = item.get('context_before', '') or ''
    context_after = item.get('context_after', '') or ''
    
    return DialogueContext(
        text=text,
        context_before=context_before,
        context_after=context_after,
        chapter_id=1,
        speaker_hint=None,
        prev_speaker=None,
        mentioned_characters=item.get('mentioned', []),
    )


def run_test_for_style(cm, test_data, project_id, style_label="L2"):
    """使用项目角色库运行测试
    
    Args:
        cm: CharacterManager 实例
        test_data: 测试数据列表（已按文体过滤）
        project_id: 项目 ID
        style_label: 测试标签
        
    Returns:
        (correct, total, errors, accuracy)
    """
    sm = LegacyRuleMatcher(cm)
    sm.current_project_id = project_id
    
    correct = 0
    total = 0
    errors = []
    
    for i, item in enumerate(test_data):
        gt_speaker = item.get('speaker', '')
        # 过滤 speaker 为"未知"的条目
        if gt_speaker in ('未知', 'Unknown', None, ''):
            continue
        
        ctx = create_dialogue_context(item)
        
        result = sm.match_speaker(ctx)
        pred = result.character.name if result else None
        
        is_correct = (pred == gt_speaker)
        if is_correct:
            correct += 1
        else:
            errors.append({
                "id": item.get("id", f"test_{i}"),
                "gt": gt_speaker,
                "pred": pred,
                "text": item.get("text", "")[:50],
            })
        
        total += 1
    
    accuracy = correct / total if total > 0 else 0
    return correct, total, errors, accuracy


def run_style_test(style, test_data_by_style, promotion_threshold, label):
    """运行单文体测试
    
    Args:
        style: 文体类型
        test_data_by_style: 按文体分组的测试数据
        promotion_threshold: 晋升阈值
        label: 测试标签（L2a/L2b）
        
    Returns:
        (style, correct, total, accuracy)
    """
    if style not in test_data_by_style:
        print(f"\n{label} [{style}]: 无测试数据")
        return (style, 0, 0, 0.0)
    
    style_data = test_data_by_style[style]
    project_id = STYLE_PROJECT_MAP[style]
    
    print(f"\n{'='*60}")
    print(f"{label} [{style}] - 项目: {project_id}")
    print(f"{'='*60}")
    
    # 从测试数据提取角色频次
    role_freq = extract_roles_from_test_data(test_data_by_style, style)
    print(f"  提取到 {len(role_freq)} 个角色")
    
    # 构建角色库
    cm, db_path = build_role_library_from_test_data(
        role_freq, project_id, promotion_threshold
    )
    
    try:
        # 运行测试
        correct, total, errors, accuracy = run_test_for_style(
            cm, style_data, project_id, style_label=label
        )
        
        print(f"\n{label} [{style}] 结果:")
        print(f"  总准确率: {accuracy:.1%} ({correct}/{total})")
        
        if errors:
            print(f"\n  错误 case ({len(errors)}):")
            for err in errors[:5]:  # 只显示前5个
                print(f"    [{err['id']}] GT={err['gt']:10s} pred={err['pred']}")
        
        return (style, correct, total, accuracy)
    finally:
        os.unlink(db_path)


def run_l2a_isolated(test_data_by_style):
    """L2a: 现有晋升机制（≥3次），按项目隔离"""
    print("\n" + "#"*60)
    print("# L2a: 现有晋升机制（≥3次）- 项目隔离测试")
    print("#"*60)
    
    results = {}
    for style in STYLE_PROJECT_MAP.keys():
        result = run_style_test(style, test_data_by_style, promotion_threshold=3, label="L2a")
        results[style] = result
    
    return results


def run_l2b_isolated(test_data_by_style):
    """L2b: 临时角色直接视为正式（门槛=1次），按项目隔离"""
    print("\n" + "#"*60)
    print("# L2b: 临时角色直接视为正式（门槛=1次）- 项目隔离测试")
    print("#"*60)
    
    results = {}
    for style in STYLE_PROJECT_MAP.keys():
        result = run_style_test(style, test_data_by_style, promotion_threshold=1, label="L2b")
        results[style] = result
    
    return results


def print_isolated_comparison_report(l2a_results, l2b_results):
    """打印项目隔离对比报告"""
    print("\n" + "="*70)
    print("L2 项目隔离测试对比报告")
    print("="*70)
    
    print(f"\n{'文体':<8} {'L2a准确率':>10} {'L2a正确/总数':>14} {'L2b准确率':>10} {'L2b正确/总数':>14} {'差距':>8}")
    print("-" * 70)
    
    total_correct_a = 0
    total_total_a = 0
    total_correct_b = 0
    total_total_b = 0
    
    for style in STYLE_PROJECT_MAP.keys():
        l2a_style, l2a_correct, l2a_total, l2a_acc = l2a_results[style]
        l2b_style, l2b_correct, l2b_total, l2b_acc = l2b_results[style]
        
        total_correct_a += l2a_correct
        total_total_a += l2a_total
        total_correct_b += l2b_correct
        total_total_b += l2b_total
        
        gap = l2b_acc - l2a_acc if l2a_total > 0 else 0
        l2a_str = f"{l2a_correct}/{l2a_total}" if l2a_total > 0 else "N/A"
        l2b_str = f"{l2b_correct}/{l2b_total}" if l2b_total > 0 else "N/A"
        
        print(f"{style:<8} {l2a_acc:>9.1%} {l2a_str:>14} {l2b_acc:>9.1%} {l2b_str:>14} {gap:>+7.1%}")
    
    # 汇总
    total_acc_a = total_correct_a / total_total_a if total_total_a > 0 else 0
    total_acc_b = total_correct_b / total_total_b if total_total_b > 0 else 0
    total_gap = total_acc_b - total_acc_a
    
    print("-" * 70)
    print(f"{'汇总':<8} {total_acc_a:>9.1%} {total_correct_a:>4}/{total_total_a:<10} {total_acc_b:>9.1%} {total_correct_b:>4}/{total_total_b:<10} {total_gap:>+7.1%}")
    
    print("\n" + "-" * 70)
    print("判断标准:")
    print(f"  汇总准确率 ≥ 66.1% → 角色库/匹配器基本合格: {'✅' if total_acc_a >= 0.661 else '❌'}")
    print(f"  L2b - L2a > 10% → 晋升门槛太高: {'❌' if total_gap > 0.10 else '✅'}")
    
    print("\n" + "-" * 70)
    print("结论:")
    if total_acc_a >= 0.661:
        print(f"  ✅ 汇总准确率 ({total_acc_a:.1%}) 达到目标 (≥ 66.1%)")
    else:
        print(f"  ❌ 汇总准确率 ({total_acc_a:.1%}) 未达到目标 (≥ 66.1%)")
    
    if total_gap > 0.10:
        print(f"  ⚠️ L2b - L2a = {total_gap:.1%} > 10%，晋升门槛可能太高")
    else:
        print(f"  ✅ L2b - L2a = {total_gap:.1%} ≤ 10%，晋升门槛合理")


def group_test_data_by_style(test_data):
    """按文体分组测试数据"""
    grouped = {}
    for item in test_data:
        style = item.get('style', '未知')
        if style not in grouped:
            grouped[style] = []
        grouped[style].append(item)
    
    print(f"\n测试数据分布:")
    for style, items in grouped.items():
        print(f"  {style}: {len(items)} 条")
    
    return grouped


def main():
    print("="*60)
    print("L2 真实场景测试：角色库集成测试（项目隔离版 - 测试数据驱动）")
    print("="*60)
    
    # 1. 加载测试数据
    test_data = load_test_data()
    
    # 2. 按文体分组
    test_data_by_style = group_test_data_by_style(test_data)
    
    # 3. 运行 L2a 测试（现有晋升机制 ≥3次）
    l2a_results = run_l2a_isolated(test_data_by_style)
    
    # 4. 运行 L2b 测试（门槛=1次）
    l2b_results = run_l2b_isolated(test_data_by_style)
    
    # 5. 打印对比报告
    print_isolated_comparison_report(l2a_results, l2b_results)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()