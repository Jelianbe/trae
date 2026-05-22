# -*- coding: utf-8 -*-
"""L2 真实场景测试：角色库集成测试

用途：模拟真实运行场景（先全文扫描构建角色库，再逐条测试）
预注册：❌ 否
角色库：✅ 从全文扫描构建

分层：
- L2a: 现有晋升机制（≥3次）
- L2b: 临时角色直接视为正式（门槛=1次）

对比 L2a vs L2b，精确量化"晋升机制本身"对结果的贡献。
"""

import sys
import os
import json
import time
import tempfile

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.character_manager import CharacterManager
from pipeline.legacy_rule_matcher import LegacyRuleMatcher
from pipeline.speaker_matcher_interface import DialogueContext
from utils.config import PROMOTION_THRESHOLD


def load_test_data():
    """加载测试数据（GT）"""
    gt_path = os.path.join(PROJECT_ROOT, "tests", "role_emotion_gt_300.json")
    if not os.path.exists(gt_path):
        gt_path = os.path.join(PROJECT_ROOT, "tests", "role_emotion_gt_100.json")
    
    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"加载测试数据: {len(data)} 条")
    return data


def load_novel_text(novel_name="修仙传"):
    """加载小说全文"""
    novel_path = os.path.join(PROJECT_ROOT, "data", "novels", f"{novel_name}.txt")
    if not os.path.exists(novel_path):
        print(f"⚠️ 小说文件不存在: {novel_path}")
        return None
    
    with open(novel_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"加载小说全文: {novel_name} ({len(text):,} 字符)")
    return text


def build_role_library(novel_text, promotion_threshold=None):
    """从小说全文构建角色库
    
    Args:
        novel_text: 小说全文
        promotion_threshold: 晋升阈值（None 使用默认值）
        
    Returns:
        CharacterManager 实例
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
        # 运行角色提取器
        from scripts.extract_roles import MinimalRoleExtractor
        extractor = MinimalRoleExtractor()
        role_data = extractor.extract_from_novel(novel_text, scan_length=150)
        
        # 导入角色库
        cm.import_from_role_extractor(role_data, "test_project")
        
        stats = role_data.get("statistics", {})
        print(f"  角色库构建完成:")
        print(f"    对话总数: {stats.get('total_quotes', 'N/A')}")
        print(f"    唯一角色名: {stats.get('unique_named_characters', 'N/A')}")
        print(f"    唯一描述性称呼: {stats.get('unique_descriptive_references', 'N/A')}")
        print(f"    正式角色数: {len(cm.get_all_characters('test_project'))}")
        print(f"    临时角色数: {len(cm.get_all_temp_characters())}")
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
        mentioned_characters=[],
    )


def run_test_with_role_library(cm, test_data, label="L2"):
    """使用角色库运行测试
    
    Args:
        cm: CharacterManager 实例
        test_data: 测试数据列表
        label: 测试标签
        
    Returns:
        (correct, total, errors, style_stats)
    """
    sm = LegacyRuleMatcher(cm)
    sm.current_project_id = "test_project"
    
    correct = 0
    total = 0
    errors = []
    style_stats = {}
    
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
                "context_before": item.get("context_before", "")[:80],
                "text": item.get("text", "")[:50],
            })
        
        # 按文体统计
        style = item.get('style', '未知')
        if style not in style_stats:
            style_stats[style] = {"correct": 0, "total": 0}
        style_stats[style]["total"] += 1
        if is_correct:
            style_stats[style]["correct"] += 1
        
        total += 1
    
    accuracy = correct / total if total > 0 else 0
    return correct, total, errors, style_stats, accuracy


def run_l2a_test(test_data, novel_text):
    """L2a: 现有晋升机制（≥3次）"""
    print("\n" + "="*60)
    print("L2a: 现有晋升机制（≥3次）")
    print("="*60)
    
    cm, db_path = build_role_library(novel_text, promotion_threshold=3)
    
    try:
        correct, total, errors, style_stats, accuracy = run_test_with_role_library(
            cm, test_data, label="L2a"
        )
        
        print(f"\nL2a 结果:")
        print(f"  总准确率: {accuracy:.1%} ({correct}/{total})")
        print(f"  按文体细分:")
        for style, stats in style_stats.items():
            style_acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            print(f"    {style}: {stats['correct']}/{stats['total']} = {style_acc:.1%}")
        
        if errors:
            print(f"\n  错误 case ({len(errors)}):")
            for err in errors[:5]:  # 只显示前5个
                print(f"    [{err['id']}] GT={err['gt']:10s} pred={err['pred']}")
        
        return ("L2a", correct, total, accuracy)
    finally:
        os.unlink(db_path)


def run_l2b_test(test_data, novel_text):
    """L2b: 临时角色直接视为正式（门槛=1次）"""
    print("\n" + "="*60)
    print("L2b: 临时角色直接视为正式（门槛=1次）")
    print("="*60)
    
    cm, db_path = build_role_library(novel_text, promotion_threshold=1)
    
    try:
        correct, total, errors, style_stats, accuracy = run_test_with_role_library(
            cm, test_data, label="L2b"
        )
        
        print(f"\nL2b 结果:")
        print(f"  总准确率: {accuracy:.1%} ({correct}/{total})")
        print(f"  按文体细分:")
        for style, stats in style_stats.items():
            style_acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            print(f"    {style}: {stats['correct']}/{stats['total']} = {style_acc:.1%}")
        
        if errors:
            print(f"\n  错误 case ({len(errors)}):")
            for err in errors[:5]:  # 只显示前5个
                print(f"    [{err['id']}] GT={err['gt']:10s} pred={err['pred']}")
        
        return ("L2b", correct, total, accuracy)
    finally:
        os.unlink(db_path)


def run_l25_test(test_data):
    """L2.5: 极端下限测试（零知识模式，无角色库）"""
    print("\n" + "="*60)
    print("L2.5: 极端下限测试（零知识模式）")
    print("="*60)
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    cm = CharacterManager(db_path)
    
    try:
        correct, total, errors, style_stats, accuracy = run_test_with_role_library(
            cm, test_data, label="L2.5"
        )
        
        print(f"\nL2.5 结果:")
        print(f"  总准确率: {accuracy:.1%} ({correct}/{total})")
        print(f"  按文体细分:")
        for style, stats in style_stats.items():
            style_acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            print(f"    {style}: {stats['correct']}/{stats['total']} = {style_acc:.1%}")
        
        if errors:
            print(f"\n  错误 case ({len(errors)}):")
            for err in errors[:5]:
                print(f"    [{err['id']}] GT={err['gt']:10s} pred={err['pred']}")
        
        return ("L2.5", correct, total, accuracy)
    finally:
        os.unlink(db_path)


def print_comparison_report(l1_result, l2a_result, l2b_result, l25_result):
    """打印对比报告"""
    print("\n" + "="*60)
    print("测试对比报告")
    print("="*60)
    
    l1_name, l1_correct, l1_total, l1_acc = l1_result
    l2a_name, l2a_correct, l2a_total, l2a_acc = l2a_result
    l2b_name, l2b_correct, l2b_total, l2b_acc = l2b_result
    l25_name, l25_correct, l25_total, l25_acc = l25_result
    
    print(f"\n{'层级':<8} {'准确率':>8} {'正确/总数':>12} {'与L1差距':>10}")
    print("-" * 50)
    print(f"{'L1':<8} {l1_acc:>7.1%} {l1_correct:>4}/{l1_total:<6} {'基准':>10}")
    print(f"{'L2a':<8} {l2a_acc:>7.1%} {l2a_correct:>4}/{l2a_total:<6} {l2a_acc - l1_acc:>+7.1%}")
    print(f"{'L2b':<8} {l2b_acc:>7.1%} {l2b_correct:>4}/{l2b_total:<6} {l2b_acc - l1_acc:>+7.1%}")
    print(f"{'L2.5':<8} {l25_acc:>7.1%} {l25_correct:>4}/{l25_total:<6} {l25_acc - l1_acc:>+7.1%}")


def main():
    print("="*60)
    print("L2 真实场景测试：角色库集成测试")
    print("="*60)
    
    # 1. 加载测试数据
    test_data = load_test_data()
    
    # 2. 加载小说全文
    novel_text = load_novel_text("修仙传")
    if not novel_text:
        print("❌ 无法加载小说全文，测试终止")
        return
    
    # 3. 运行 L2a 测试（现有晋升机制 ≥3次）
    l2a_result = run_l2a_test(test_data, novel_text)
    
    # 4. 运行 L2b 测试（门槛=1次）
    l2b_result = run_l2b_test(test_data, novel_text)
    
    # 5. 运行 L2.5 测试（零知识模式）
    l25_result = run_l25_test(test_data)
    
    # 6. 打印对比报告
    l1_result = ("L1", 197, 243, 0.811)  # 已知基准
    print_comparison_report(l1_result, l2a_result, l2b_result, l25_result)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
