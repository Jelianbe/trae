# -*- coding: utf-8 -*-
"""v2 评估体系：宽松模式判定逻辑。

设计原则：
  1. 命名变体 → 算对（超集匹配、归一化后相同）
  2. 描述性角色 → 视情况算对（当前上下文中唯一指向某角色）
  3. 连续对话无主语 → 继承上一人算对
  4. "未知" → 严格判错（不放宽）

用户不是在做题，是在听书。只要不"张冠李戴"，大部分变体可接受。

用法:
    from tests.eval_utils import is_relaxed_correct, normalize_for_eval

    # 单独判定
    ok = is_relaxed_correct(predicted, expected, prev_predicted, char_aliases)
"""

import re
from typing import Dict, Set, Optional


# TITLE_SUFFIXES_FOR_EVAL
#
# 用途：评估归一化时剥离的头衔后缀
# 来源：与 pattern_extractor.FANTASY_TITLE_SUFFIXES + 现代职位一致
# 边界：仅包含网文/职场中常见的后缀，不包含泛化词
# 上限：约40条，封闭集合
# 更新日期：2026-05-16
# 维护者：v2 评估体系
TITLE_SUFFIXES_FOR_EVAL = [
    # 西幻/中文网文
    '团长', '骑士', '法师', '护卫', '士兵', '剑客', '刺客',
    '杀手', '牧师', '主教', '长老', '掌门', '队长', '掌柜',
    '管家', '丫鬟', '侍女', '侍卫', '铁匠', '商人', '猎人',
    '修士', '老战士', '治疗师',
    # 现代职场
    '总监', '经理', '局长', '处长', '科长', '主任', '老板',
    '老师', '医生', '护士', '司机', '保安', '工程师', '秘书',
    # 尊称/后缀
    '总', '先生', '小姐', '女士', '同志',
]


def normalize_for_eval(name: str) -> str:
    """归一化角色名用于评估比较。
    
    策略：
      1. 去前后空白
      2. 剥离常见头衔后缀（从最长到最短尝试）
      3. 返回核心人名
    
    Args:
        name: 原始角色名
        
    Returns:
        归一化后的名称
    """
    if not name:
        return ''
    
    name = name.strip()
    
    # 按长度降序排序，先匹配长后缀
    sorted_suffixes = sorted(TITLE_SUFFIXES_FOR_EVAL, key=len, reverse=True)
    
    for suffix in sorted_suffixes:
        if name.endswith(suffix) and len(name) > len(suffix):
            core = name[:-len(suffix)]
            cn_count = sum(1 for c in core if '\u4e00' <= c <= '\u9fff')
            if cn_count >= 1:
                return core
    
    return name


def is_name_variant_match(predicted: str, expected: str) -> bool:
    """判定预测名与期望名是否为同一人的变体。
    
    规则：
      1. 精确匹配 → ✅
      2. 预测名包含期望名（超集），如 "亚瑟团长" vs "亚瑟" → ✅
      3. 期望名包含预测名（超集），如 "赵总监" vs "赵总" → 归一化后比较
      4. 归一化后相同 → ✅
    
    Args:
        predicted: 系统预测的角色名
        expected: ground truth 中的期望角色名
        
    Returns:
        是否为同一人的变体
    """
    if predicted == expected:
        return True
    
    # 规则2: 预测名包含期望名（超集）
    if expected in predicted:
        return True
    
    # 规则3: 期望名包含预测名
    if predicted in expected:
        return True
    
    # 规则4: 归一化后相同
    norm_predicted = normalize_for_eval(predicted)
    norm_expected = normalize_for_eval(expected)
    if norm_predicted == norm_expected:
        return True
    
    return False


def is_relaxed_correct(
    predicted: str,
    expected: str,
    prev_predicted: Optional[str] = None,
    char_aliases: Optional[Dict[str, Set[str]]] = None,
) -> bool:
    """宽松模式下的正确性判定。
    
    Args:
        predicted: 系统预测的角色名（'UNKNOWN' 表示未识别）
        expected: ground truth 中的期望角色名
        prev_predicted: 上一句的预测角色名（用于连续对话继承判定）
        char_aliases: 角色别名映射 {canonical_name: {aliases}}
        
    Returns:
        宽松模式下是否算正确
    """
    # 规则4: "未知"严格判错
    if predicted == 'UNKNOWN':
        return False
    
    # 精确匹配
    if predicted == expected:
        return True
    
    # 规则1: 命名变体匹配
    if is_name_variant_match(predicted, expected):
        return True
    
    # 别名匹配
    if char_aliases:
        # 检查预测名是否是期望名的别名
        if expected in char_aliases:
            if predicted in char_aliases[expected]:
                return True
        # 检查期望名是否是预测名的别名
        for canonical, aliases in char_aliases.items():
            if predicted == canonical and expected in aliases:
                return True
            if expected == canonical and predicted in aliases:
                return True
    
    # 规则3: 连续对话继承 — 如果预测等于上一句说话人，且无法确定GT
    # 此规则仅在 prev_predicted 有意义时启用
    # 注意：只有当 GT 也没有明确指向其他人时才适用
    # 这里不做自动继承判定，因为 GT 已经明确标注了说话人
    # 如果预测 != GT，即使继承了上一人也是错的（张冠李戴）
    
    return False


def is_relaxed_correct_with_context(
    predicted: str,
    expected: str,
    prev_predicted: Optional[str] = None,
    prev_expected: Optional[str] = None,
    char_aliases: Optional[Dict[str, Set[str]]] = None,
    is_continuation: bool = False,
) -> bool:
    """宽松模式下带上下文的正确性判定。
    
    在 is_relaxed_correct 基础上增加：
      - 连续对话继承判定：如果当前行无明显说话标记，
        且预测 = 上一句预测 = 上一句GT，算对
    
    Args:
        predicted: 系统预测的角色名
        expected: ground truth 中的期望角色名
        prev_predicted: 上一句的预测角色名
        prev_expected: 上一句的 ground truth 角色名
        char_aliases: 角色别名映射
        is_continuation: 当前对话是否为连续对话（无新旁白）
        
    Returns:
        宽松模式下是否算正确
    """
    # 基础判定
    if is_relaxed_correct(predicted, expected, prev_predicted, char_aliases):
        return True
    
    # 规则3: 连续对话继承
    # 如果当前是连续对话（无新旁白），且：
    #   - 预测 = 上一句GT（或归一化后相同）
    #   - 上一句GT 有明确值
    # 则视为系统正确继承了上一说话人
    if is_continuation and prev_expected and prev_expected != 'UNKNOWN':
        if predicted == prev_expected:
            return True
        if is_name_variant_match(predicted, prev_expected):
            return True
    
    return False
