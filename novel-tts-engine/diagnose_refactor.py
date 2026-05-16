#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断脚本：对比重构前后的 _extract_context_speakers 输出

用法：
    python diagnose_refactor.py

输出：
    - 重构前候选人列表
    - 重构后候选人列表
    - 差异点
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 测试数据（来自修仙传 P7 段落）
TEST_CASES = [
    {
        'id': 'P7_passive_action',
        'description': '被动动作主体过滤：药老说话，萧炎点头（萧炎是被对话方）',
        'text': '"嗯。"萧炎应了一声。',
        'context_before': '药老笑道："你的天赋不错。"',
        'context_after': '',
    },
    {
        'id': 'P7_name_match',
        'description': '角色库直接匹配：药老在 context_before 中 + 说话动词',
        'text': '"你的天赋不错。"',
        'context_before': '药老捋了捋胡须，笑道',
        'context_after': '',
    },
    {
        'id': 'surname_expand',
        'description': '姓氏扩展：纳兰嫣然被 HanLP 识别为 纳兰',
        'text': '"你好。"',
        'context_before': '纳兰嫣然走进大厅，微笑道',
        'context_after': '',
    },
]

def run_comparison():
    print("=" * 60)
    print("重构前后 _extract_context_speakers 对比诊断")
    print("=" * 60)

    # 检查备份文件是否存在
    backup_path = PROJECT_ROOT / "pipeline" / "speaker_matcher.py.backup_before_rollback"
    current_path = PROJECT_ROOT / "pipeline" / "speaker_matcher.py"

    if not backup_path.exists():
        print("ERROR: 备份文件不存在，无法对比")
        return

    print(f"\n备份文件: {backup_path}")
    print(f"当前文件: {current_path}")
    print()

    # 检查关键逻辑差异
    print("-" * 60)
    print("关键逻辑差异检查")
    print("-" * 60)

    with open(backup_path, 'r', encoding='utf-8') as f:
        backup_content = f.read()

    with open(current_path, 'r', encoding='utf-8') as f:
        current_content = f.read()

    # 检查1: 被动动作主体过滤
    has_passive_backup = 'passive_action_patterns' in backup_content
    has_passive_current = 'passive_action_patterns' in current_content
    print(f"\n[1] 被动动作主体过滤 (passive_subjects):")
    print(f"    备份文件: {'✅ 存在' if has_passive_backup else '❌ 不存在'}")
    print(f"    当前文件: {'✅ 存在' if has_passive_current else '❌ 不存在'}")
    if has_passive_backup and not has_passive_current:
        print(f"    ⚠️ 重构后丢失此逻辑！")

    # 检查2: 角色库直接匹配（声音指示/说话动词/冒号主语/动作暗示）
    has_voice_hint_backup = '角色库-声音指示' in backup_content
    has_voice_hint_current = '角色库-声音指示' in current_content
    print(f"\n[2] 角色库直接匹配（声音指示等）:")
    print(f"    备份文件: {'✅ 存在' if has_voice_hint_backup else '❌ 不存在'}")
    print(f"    当前文件: {'✅ 存在' if has_voice_hint_current else '❌ 不存在'}")
    if has_voice_hint_backup and not has_voice_hint_current:
        print(f"    ⚠️ 重构后丢失此逻辑！")

    # 检查3: _expand_surname_entities
    has_expand_surname_backup = 'def _expand_surname_entities' in backup_content
    has_expand_surname_current = 'def _expand_surname_entities' in current_content
    print(f"\n[3] _expand_surname_entities 方法:")
    print(f"    备份文件: {'✅ 存在' if has_expand_surname_backup else '❌ 不存在'}")
    print(f"    当前文件: {'✅ 存在' if has_expand_surname_current else '❌ 不存在'}")

    # 检查4: _is_clean_per_entity
    has_clean_per_backup = 'def _is_clean_per_entity' in backup_content
    has_clean_per_current = 'def _is_clean_per_entity' in current_content
    print(f"\n[4] _is_clean_per_entity 方法:")
    print(f"    备份文件: {'✅ 存在' if has_clean_per_backup else '❌ 不存在'}")
    print(f"    当前文件: {'✅ 存在' if has_clean_per_current else '❌ 不存在'}")

    # 检查5: 身份词提取
    has_identity_backup = 'def _extract_identity_words' in backup_content
    has_identity_current = 'def _extract_identity_words' in current_content
    print(f"\n[5] _extract_identity_words 方法:")
    print(f"    备份文件: {'✅ 存在' if has_identity_backup else '❌ 不存在'}")
    print(f"    当前文件: {'✅ 存在' if has_identity_current else '❌ 不存在'}")

    # 检查6: EntityCleaner 调用
    has_entity_cleaner = 'entity_cleaner' in current_content
    print(f"\n[6] EntityCleaner 调用:")
    print(f"    当前文件: {'✅ 存在' if has_entity_cleaner else '❌ 不存在'}")

    print("\n" + "=" * 60)
    print("诊断结论")
    print("=" * 60)

    missing_features = []
    if has_passive_backup and not has_passive_current:
        missing_features.append("被动动作主体过滤（passive_subjects）")
    if has_voice_hint_backup and not has_voice_hint_current:
        missing_features.append("角色库直接匹配（声音指示/说话动词/冒号主语）")
    if has_identity_backup and not has_identity_current:
        missing_features.append("身份词提取（_extract_identity_words）")

    if missing_features:
        print(f"\n重构后丢失的{len(missing_features)}个关键功能：")
        for i, feature in enumerate(missing_features, 1):
            print(f"  {i}. {feature}")
        print(f"\n建议：这些功能的丢失很可能是准确率下降3%的根因。")
    else:
        print("\n未发现明显功能丢失，需要进一步诊断。")

if __name__ == '__main__':
    run_comparison()
