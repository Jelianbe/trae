# -*- coding: utf-8 -*-
"""L2 真实场景测试：角色库集成测试（小说文件版）

用途：从真实小说文件构建角色库，然后测试该小说的对话匹配效果
策略：
  1. 从小说全文扫描提取角色，构建角色库
  2. 从小说中提取对话作为测试数据（speaker 从上下文中提取）
  3. 测试匹配准确率

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


# 小说文件配置
NOVELS_TO_TEST = [
    {
        "name": "修仙传",
        "file": "修仙传.txt",
        "project_id": "xiuxian_novel",
        "style": "修仙",
    },
    {
        "name": "测试对话_周末计划",
        "file": "测试对话_周末计划.txt",
        "project_id": "urban_weekend",
        "style": "都市",
    },
]


def load_novel_text(novel_file):
    """加载小说全文"""
    novel_path = os.path.join(PROJECT_ROOT, "data", "novels", novel_file)
    if not os.path.exists(novel_path):
        print(f"⚠️ 小说文件不存在: {novel_path}")
        return None
    
    with open(novel_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"加载小说: {novel_file} ({len(text):,} 字符)")
    return text


def extract_roles_from_novel(novel_text, scan_length=150):
    """从小说全文提取角色
    
    Args:
        novel_text: 小说全文
        scan_length: 扫描长度
        
    Returns:
        role_data: 角色提取结果
    """
    from scripts.extract_roles import MinimalRoleExtractor
    
    extractor = MinimalRoleExtractor()
    role_data = extractor.extract_from_novel(novel_text, scan_length=scan_length)
    
    # 如果角色提取器没有找到角色（如周末计划格式），手动提取
    if role_data.get("statistics", {}).get("unique_named_characters", 0) == 0:
        # 手动提取 名字：对话 格式的角色
        import re
        dialogue_pattern_colon = re.compile(r'^([^\s：:]{2,4})[：:]\s*(.+)$')
        paragraphs = novel_text.split('\n')
        role_freq = {}
        
        for para in paragraphs:
            para_stripped = para.strip()
            match = dialogue_pattern_colon.match(para_stripped)
            if match:
                name = match.group(1)
                # 过滤标题和无效名称
                if not any(keyword in name for keyword in ['第', '章', '作者', '简介']):
                    role_freq[name] = role_freq.get(name, 0) + 1
        
        if role_freq:
            # 转换为角色提取器格式：{角色名: [位置列表]}
            # import_from_role_extractor 直接从 role_data 读取 named_characters
            named_characters = {name: [0] * freq for name, freq in role_freq.items()}
            role_data["named_characters"] = named_characters
            role_data["descriptive_references"] = {}
            role_data["statistics"] = {
                "total_quotes": sum(role_freq.values()),
                "unique_named_characters": len(role_freq),
                "unique_descriptive_references": 0,
            }
            print(f"  手动提取到 {len(role_freq)} 个角色: {list(role_freq.keys())}")
    
    stats = role_data.get("statistics", {})
    print(f"  角色提取完成:")
    print(f"    对话总数: {stats.get('total_quotes', 'N/A')}")
    print(f"    唯一角色名: {stats.get('unique_named_characters', 'N/A')}")
    print(f"    唯一描述性称呼: {stats.get('unique_descriptive_references', 'N/A')}")
    
    return role_data


def build_role_library_from_novel(role_data, project_id, promotion_threshold=None):
    """从小说角色数据构建角色库
    
    Args:
        role_data: 角色提取结果
        project_id: 项目 ID
        promotion_threshold: 晋升阈值
        
    Returns:
        (CharacterManager, db_path)
    """
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    cm = CharacterManager(db_path)
    
    if promotion_threshold is not None:
        import utils.config as cfg
        original_threshold = cfg.PROMOTION_THRESHOLD
        cfg.PROMOTION_THRESHOLD = promotion_threshold
    
    try:
        cm.import_from_role_extractor(role_data, project_id)
        
        formal_count = len(cm.get_all_characters(project_id))
        temp_count = len(cm.get_all_temp_characters())
        print(f"  角色库构建完成 [{project_id}]:")
        print(f"    正式角色数: {formal_count}")
        print(f"    临时角色数: {temp_count}")
    finally:
        if promotion_threshold is not None:
            import utils.config as cfg
            cfg.PROMOTION_THRESHOLD = original_threshold
    
    return cm, db_path


def extract_test_dialogues_from_novel(novel_text, novel_name, max_samples=50):
    """从小说中提取测试对话
    
    策略：
    1. 按段落分割
    2. 识别对话格式：「」或 名字：对话
    3. 从上下文提取 speaker
    4. 构建测试数据
    
    Args:
        novel_text: 小说全文
        novel_name: 小说名称
        max_samples: 最大样本数
        
    Returns:
        test_data: 测试数据列表
    """
    paragraphs = novel_text.split('\n')
    
    test_data = []
    
    # 修仙传风格：「对话内容」或 "对话内容"
    dialogue_pattern_quotes = re.compile(r'[\u201c\u201d「"](.+?)[\u201d\u201c」"]')
    
    # 周末计划风格：名字：对话
    dialogue_pattern_colon = re.compile(r'^([^\s：:]{2,4})[：:]\s*(.+)$')
    
    for i, para in enumerate(paragraphs):
        if len(test_data) >= max_samples:
            break
        
        # 跳过空行和标题
        para_stripped = para.strip()
        if not para_stripped or len(para_stripped) < 5:
            continue
        
        speaker = None
        dialogue_text = None
        
        # 先尝试匹配 名字：对话 格式
        colon_match = dialogue_pattern_colon.match(para_stripped)
        if colon_match:
            speaker = colon_match.group(1)
            dialogue_text = colon_match.group(2)
            # 过滤标题和无效名称
            if any(keyword in speaker for keyword in ['第', '章', '作者', '简介']):
                speaker = None
        else:
            # 尝试匹配「」格式
            quotes_match = dialogue_pattern_quotes.search(para_stripped)
            if quotes_match:
                dialogue_text = quotes_match.group(1)
                
                # 从上下文中提取说话人
                context_before = paragraphs[max(0, i-3):i]
                full_context = ' '.join(context_before) + ' ' + para_stripped
                
                # 匹配模式：XXX说道、XXX说、XXX道（修仙传格式：对话后跟说话人）
                # 注意：使用 [\u4e00-\u9fa5] 限制只匹配中文字符，避免匹配到动词
                speaker_patterns = [
                    r'([\u4e00-\u9fa5]{2,4})说道',
                    r'([\u4e00-\u9fa5]{2,4})说[：:，。]',
                    r'([\u4e00-\u9fa5]{2,4})道[：:，。]',
                    r'([\u4e00-\u9fa5]{2,4})问[：:，。]',
                    r'([\u4e00-\u9fa5]{2,4})回答[：:，。]',
                    r'([\u4e00-\u9fa5]{2,4})冷笑',
                    r'([\u4e00-\u9fa5]{2,4})点头',
                    r'([\u4e00-\u9fa5]{2,4})摇头',
                    r'([\u4e00-\u9fa5]{2,4})接过',
                    r'([\u4e00-\u9fa5]{2,4})回头',
                    r'([\u4e00-\u9fa5]{2,4})立刻',
                    r'([\u4e00-\u9fa5]{2,4})推开',
                    r'([\u4e00-\u9fa5]{2,4})不高',
                    r'([\u4e00-\u9fa5]{2,4})不欲',
                ]
                
                for pattern in speaker_patterns:
                    speaker_match = re.search(pattern, full_context)
                    if speaker_match:
                        speaker = speaker_match.group(1)
                        break
        
        # 如果没找到说话人或对话，跳过
        if not speaker or not dialogue_text:
            continue
        
        # 获取上下文
        context_before = paragraphs[max(0, i-2):i]
        context_after = paragraphs[i+1:min(len(paragraphs), i+3)]
        
        context_before_str = ' '.join(context_before)
        context_after_str = ' '.join(context_after)
        
        test_data.append({
            "id": f"{novel_name}_dialogue_{len(test_data):03d}",
            "text": dialogue_text,
            "context_before": context_before_str[:200],
            "context_after": context_after_str[:200],
            "speaker": speaker,
            "style": "修仙" if "修仙" in novel_name else "都市",
        })
    
    print(f"  提取到 {len(test_data)} 条测试对话")
    return test_data


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


def run_test_for_novel(cm, test_data, project_id, label="L2"):
    """运行单小说测试
    
    Args:
        cm: CharacterManager 实例
        test_data: 测试数据列表
        project_id: 项目 ID
        label: 测试标签
        
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
        if not gt_speaker:
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


def test_novel_isolated(novel_config, promotion_threshold, label):
    """测试单部小说（项目隔离）
    
    Args:
        novel_config: 小说配置
        promotion_threshold: 晋升阈值
        label: 测试标签
        
    Returns:
        (novel_name, correct, total, accuracy)
    """
    novel_name = novel_config["name"]
    novel_file = novel_config["file"]
    project_id = novel_config["project_id"]
    
    print(f"\n{'='*60}")
    print(f"{label} [{novel_name}] - 项目: {project_id}")
    print(f"{'='*60}")
    
    # 加载小说
    novel_text = load_novel_text(novel_file)
    if not novel_text:
        print(f"  ⚠️ 无法加载小说，跳过")
        return (novel_name, 0, 0, 0.0)
    
    # 提取角色
    role_data = extract_roles_from_novel(novel_text)
    
    # 构建角色库
    cm, db_path = build_role_library_from_novel(
        role_data, project_id, promotion_threshold
    )
    
    try:
        # 提取测试对话
        test_data = extract_test_dialogues_from_novel(novel_text, novel_name)
        
        if not test_data:
            print(f"  ⚠️ 无法提取测试对话，跳过")
            return (novel_name, 0, 0, 0.0)
        
        # 运行测试
        correct, total, errors, accuracy = run_test_for_novel(
            cm, test_data, project_id, label=label
        )
        
        print(f"\n{label} [{novel_name}] 结果:")
        print(f"  总准确率: {accuracy:.1%} ({correct}/{total})")
        
        if errors:
            print(f"\n  错误 case ({len(errors)}):")
            for err in errors[:5]:
                print(f"    [{err['id']}] GT={err['gt']:10s} pred={err['pred']}")
        
        return (novel_name, correct, total, accuracy)
    finally:
        os.unlink(db_path)


def run_l2a_novel_test():
    """L2a: 现有晋升机制（≥3次）"""
    print("\n" + "#"*60)
    print("# L2a: 现有晋升机制（≥3次）- 小说文件测试")
    print("#"*60)
    
    results = {}
    for novel_config in NOVELS_TO_TEST:
        result = test_novel_isolated(novel_config, promotion_threshold=3, label="L2a")
        results[novel_config["name"]] = result
    
    return results


def run_l2b_novel_test():
    """L2b: 临时角色直接视为正式（门槛=1次）"""
    print("\n" + "#"*60)
    print("# L2b: 临时角色直接视为正式（门槛=1次）- 小说文件测试")
    print("#"*60)
    
    results = {}
    for novel_config in NOVELS_TO_TEST:
        result = test_novel_isolated(novel_config, promotion_threshold=1, label="L2b")
        results[novel_config["name"]] = result
    
    return results


def print_novel_comparison_report(l2a_results, l2b_results):
    """打印小说对比报告"""
    print("\n" + "="*70)
    print("L2 小说文件测试对比报告")
    print("="*70)
    
    print(f"\n{'小说':<15} {'L2a准确率':>10} {'L2a正确/总数':>14} {'L2b准确率':>10} {'L2b正确/总数':>14} {'差距':>8}")
    print("-" * 70)
    
    total_correct_a = 0
    total_total_a = 0
    total_correct_b = 0
    total_total_b = 0
    
    for novel_config in NOVELS_TO_TEST:
        name = novel_config["name"]
        l2a_name, l2a_correct, l2a_total, l2a_acc = l2a_results[name]
        l2b_name, l2b_correct, l2b_total, l2b_acc = l2b_results[name]
        
        total_correct_a += l2a_correct
        total_total_a += l2a_total
        total_correct_b += l2b_correct
        total_total_b += l2b_total
        
        gap = l2b_acc - l2a_acc if l2a_total > 0 else 0
        l2a_str = f"{l2a_correct}/{l2a_total}" if l2a_total > 0 else "N/A"
        l2b_str = f"{l2b_correct}/{l2b_total}" if l2b_total > 0 else "N/A"
        
        print(f"{name:<15} {l2a_acc:>9.1%} {l2a_str:>14} {l2b_acc:>9.1%} {l2b_str:>14} {gap:>+7.1%}")
    
    # 汇总
    total_acc_a = total_correct_a / total_total_a if total_total_a > 0 else 0
    total_acc_b = total_correct_b / total_total_b if total_total_b > 0 else 0
    total_gap = total_acc_b - total_acc_a
    
    print("-" * 70)
    print(f"{'汇总':<15} {total_acc_a:>9.1%} {total_correct_a:>4}/{total_total_a:<10} {total_acc_b:>9.1%} {total_correct_b:>4}/{total_total_b:<10} {total_gap:>+7.1%}")
    
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


def main():
    print("="*60)
    print("L2 真实场景测试：角色库集成测试（小说文件版）")
    print("="*60)
    
    # 1. 运行 L2a 测试
    l2a_results = run_l2a_novel_test()
    
    # 2. 运行 L2b 测试
    l2b_results = run_l2b_novel_test()
    
    # 3. 打印对比报告
    print_novel_comparison_report(l2a_results, l2b_results)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()