# -*- coding: utf-8 -*-
"""
算法污染检测工具 (Purity Check)

功能：
- 检测代码中是否存在针对特定测试文本的硬编码
- 检测参数阈值是否针对特定测试文本特化
- 检测规则中是否包含仅在单一测试文本中出现的特殊模式

检测项目：
1. 硬编码GT实体名
2. 按文本类型特化参数
3. 规则中包含特定实体名

执行时机：每次运行评估脚本前自动调用
"""

import os
import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


# ============================================================
# 允许列表：通用词库中的字符串不算污染
# ============================================================

ALLOWED_PATTERNS = [
    # 通用说话人提示词
    '说道', '问道', '回答', '说', '道', '喊道', '叫道', '喊',
    '冷笑', '沉声道', '点头', '摇头', '皱眉', '微笑', '大笑',
    '叹气', '挥手', '抬手', '转身', '站起', '坐下', '握拳',
    '抱拳', '拱手', '目光', '眼神', '脸色', '神情', '语气',

    # 通用称谓词（TITLE_WORDS 中的内容）
    '管家', '老爷', '夫人', '少爷', '小姐', '公子', '姑娘',
    '掌柜', '老板', '掌门', '长老', '堂主', '舵主',
    '将军', '大人', '王爷', '皇上', '皇后', '贵妃',
    '师父', '师叔', '师兄', '师弟', '师姐', '师妹',
    '博士', '教授', '医生', '护士', '律师', '记者',
    '经理', '总裁', '总监', '部长', '局长', '队长',
    '导师', '学长', '执事',

    # 通用拟声词（常见拟声词不应算作污染）
    '轰', '咔', '呼', '呼哧', '轰隆', '咔嚓',
    '嗖', '嗒', '噼', '啪', '乒', '乓', '叮', '当',
    '哗', '滴', '淅', '沥', '铃', '嘶', '咯', '吱',
    '咚', '轰隆', '嘶嘶', '叮当', '哗啦', '咚咚',
    '嗖嗖', '叮铃', '咯吱', '嘶嘶嘶', '叮叮叮',
    '咚咚咚', '轰隆隆', '哗啦啦', '叮铃铃', '咯吱咯吱',
    '叮叮当当', '乒乒乓乓', '噼里啪啦', '轰隆隆隆',
    '叮铃叮铃', '叮叮咚咚', '咯吱吱', '嗖嗖嗖',

    # 通用称谓/身份词
    '大师兄', '大师姐', '二师兄', '二师姐', '小师弟', '小师妹',

    # 通用西方名字前缀（WESTERN_NAME_PREFIXES 中的内容）
    '艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯',

    # 通用西方称呼
    '骑士', '法师', '牧师', '圣骑士', '游侠', '德鲁伊',

    # 位置/方向词
    '东', '南', '西', '北', '上', '下', '左', '右', '前', '后',

    # 常见标点符号和特殊字符
    '·', '—', '……',

    # 测试框架相关
    'test_', 'Test', 'assert', 'pytest', 'unittest',

    # 配置/工具相关
    'DEBUG', 'INFO', 'WARNING', 'ERROR', 'logging',
]

# 允许的文件：这些文件包含GT实体是合理的（GT生成脚本、GT文件本身）
ALLOWED_FILES = [
    'process_doupo.py',  # 斗破GT生成脚本
    'process_urban.py',  # 都市GT生成脚本
    'process_western.py',  # 西幻GT生成脚本
    'process_cultivation.py',  # 修仙GT生成脚本
    '_ground_truth.json',  # GT文件本身
]

# 允许的模块：这些模块中的实体列表是通用词库，不是污染
ALLOWED_MODULES = [
    'sfx_detector.py',  # 拟声词词库
    'speaker_matcher.py',  # 说话人提示词库
]

# 测试文本名称黑名单（检测代码中是否出现特定测试文本名称）
TEST_FILE_NAMES = [
    'test_novel_urban',
    'test_novel_western',
    'test_novel_cultivation',
    'test_novel_doupo',
    'urban',
    'western',
    'cultivation',
    'doupo',
]


@dataclass
class PurityIssue:
    """污染问题"""
    severity: str  # 'P0', 'P1', 'P2'
    category: str  # 'hardcoded_entity', 'specialized_param', 'specialized_rule'
    file_path: str
    line_number: int
    description: str
    code_snippet: str


def extract_gt_entities(gt_dir: Path) -> Set[str]:
    """从所有GT文件中提取实体名和别名"""
    entities: Set[str] = set()

    for gt_file in gt_dir.glob('*_ground_truth.json'):
        try:
            with open(gt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取人物
            for person in data.get('entities', {}).get('persons', []):
                entities.add(person)

            # 提取组织
            for org in data.get('entities', {}).get('organizations', []):
                entities.add(org)

            # 提取地点
            for loc in data.get('entities', {}).get('locations', []):
                entities.add(loc)

            # 提取别名
            for aliases in data.get('entities', {}).get('aliases', {}).values():
                for alias in aliases:
                    entities.add(alias)

            # 提取对话说话人
            for dl in data.get('dialogue_speakers', []):
                entities.add(dl.get('speaker', ''))

            # 提取拟声词
            for sfx in data.get('sfx', {}).get('sfx_words', []):
                entities.add(sfx)

        except Exception as e:
            print(f"[WARN] 无法解析GT文件 {gt_file}: {e}")

    return entities


def scan_hardcoded_entities(project_dir: Path, gt_entities: Set[str]) -> List[PurityIssue]:
    """检测代码中是否存在硬编码的GT实体名"""
    issues: List[PurityIssue] = []

    # 过滤掉允许列表中的实体和太短的实体
    test_entities = [e for e in gt_entities if e not in ALLOWED_PATTERNS and len(e) >= 3]

    # 预编译正则表达式，加速匹配
    import re
    patterns = []
    for entity in test_entities:
        # 匹配 "实体名" 或 '实体名' 或 "实体名"
        pattern = re.compile(rf'["\'"]{re.escape(entity)}["\'"]')
        patterns.append((entity, pattern))

    # 扫描Python文件（跳过测试文件和评估脚本）
    for py_file in project_dir.glob('**/*.py'):
        # 跳过允许的文件
        if any(py_file.name == af for af in ALLOWED_FILES):
            continue
        # 跳过测试/评估/调试文件
        skip_names = ['test_', 'evaluate', 'analyze', 'purity_check', 'debug_', 'diagnose', 'check_']
        if any(skip in py_file.name for skip in skip_names):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # 跳过注释和文档字符串
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue

                # 检测是否包含GT实体名
                for entity, pattern in patterns:
                    if pattern.search(line):
                        issues.append(PurityIssue(
                            severity='P0',
                            category='hardcoded_entity',
                            file_path=str(py_file.relative_to(project_dir)),
                            line_number=line_num,
                            description=f"代码中硬编码GT实体名: '{entity}'",
                            code_snippet=stripped[:100]
                        ))
        except Exception:
            pass

    return issues


def scan_specialized_params(project_dir: Path) -> List[PurityIssue]:
    """检测按文本类型特化的参数"""
    issues: List[PurityIssue] = []

    # 可疑模式：if style == "xxx" 或 if "xxx" in text_name
    suspicious_patterns = [
        r'if\s+style\s*==\s*["\'](\w+)["\']',
        r'if\s+["\'](\w+)["\']\s+in\s+text_name',
        r'if\s+["\'](\w+)["\']\s+in\s+text_type',
        r'(\w+)_threshold\s*=',
        r'(\w+)_window\s*=',
    ]

    for py_file in project_dir.glob('**/*.py'):
        # 跳过测试文件
        if 'test_' in py_file.name or 'evaluate' in py_file.name or 'purity_check' in py_file.name:
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue

                for pattern in suspicious_patterns:
                    match = re.search(pattern, line)
                    if match:
                        value = match.group(1)
                        if value.lower() in [t.lower() for t in TEST_FILE_NAMES]:
                            issues.append(PurityIssue(
                                severity='P0',
                                category='specialized_param',
                                file_path=str(py_file.relative_to(project_dir)),
                                line_number=line_num,
                                description=f"检测到按文本类型特化的参数: '{value}'",
                                code_snippet=stripped[:100]
                            ))
        except Exception:
            pass

    return issues


def scan_specialized_rules(project_dir: Path, gt_entities: Set[str]) -> List[PurityIssue]:
    """检测规则中是否包含特定实体名"""
    issues: List[PurityIssue] = []

    # 过滤掉允许列表中的实体
    test_entities = gt_entities - set(ALLOWED_PATTERNS)

    for py_file in project_dir.glob('**/*.py'):
        if 'test_' in py_file.name or 'evaluate' in py_file.name or 'purity_check' in py_file.name:
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue

                # 检测正则表达式中包含特定实体名
                if 're.compile' in line or 'regex' in line.lower():
                    for entity in test_entities:
                        if len(entity) < 3:
                            continue
                        if entity in line:
                            issues.append(PurityIssue(
                                severity='P0',
                                category='specialized_rule',
                                file_path=str(py_file.relative_to(project_dir)),
                                line_number=line_num,
                                description=f"正则表达式中包含特定实体名: '{entity}'",
                                code_snippet=stripped[:100]
                            ))

                # 检测列表/集合中包含特定测试文本的角色列表
                if any(entity in line for entity in test_entities if len(entity) >= 3):
                    if 're.compile' not in line:
                        # 检查是否是角色列表定义
                        if '[' in line and ']' in line:
                            entities_in_line = [e for e in test_entities if e in line and len(e) >= 3]
                            if len(entities_in_line) >= 3:
                                issues.append(PurityIssue(
                                    severity='P1',
                                    category='specialized_rule',
                                    file_path=str(py_file.relative_to(project_dir)),
                                    line_number=line_num,
                                    description=f"列表中包含多个特定测试文本的实体: {entities_in_line[:3]}",
                                    code_snippet=stripped[:100]
                                ))
        except Exception:
            pass

    return issues


def run_purity_check(project_dir: Path = None) -> Tuple[bool, List[PurityIssue]]:
    """
    执行完整的污染检测

    Returns:
        (is_clean, issues) 元组
        - is_clean: True表示无P0级污染，False表示有P0级污染
        - issues: 所有检测到的问题列表
    """
    if project_dir is None:
        project_dir = Path(__file__).parent.parent

    gt_dir = project_dir / 'tests'
    if not gt_dir.exists():
        print("[WARN] 测试目录不存在，跳过GT实体检测")
        return True, []

    # 步骤1: 提取GT实体
    print("[1/4] 提取GT实体...")
    gt_entities = extract_gt_entities(gt_dir)
    print(f"  提取到 {len(gt_entities)} 个实体")

    # 步骤2: 检测硬编码GT实体名
    print("[2/4] 检测硬编码GT实体名...")
    hardcoded_issues = scan_hardcoded_entities(project_dir, gt_entities)
    print(f"  发现 {len(hardcoded_issues)} 个问题")

    # 步骤3: 检测参数特化
    print("[3/4] 检测参数特化...")
    param_issues = scan_specialized_params(project_dir)
    print(f"  发现 {len(param_issues)} 个问题")

    # 步骤4: 检测规则特化
    print("[4/4] 检测规则特化...")
    rule_issues = scan_specialized_rules(project_dir, gt_entities)
    print(f"  发现 {len(rule_issues)} 个问题")

    # 汇总结果
    all_issues = hardcoded_issues + param_issues + rule_issues

    # 按严重程度排序
    all_issues.sort(key=lambda x: x.severity)

    # 输出报告
    print("\n" + "="*60)
    print("污染检测报告")
    print("="*60)

    if not all_issues:
        print("\n✅ 未检测到污染问题")
        return True, []

    p0_count = sum(1 for i in all_issues if i.severity == 'P0')
    p1_count = sum(1 for i in all_issues if i.severity == 'P1')
    p2_count = sum(1 for i in all_issues if i.severity == 'P2')

    print(f"\nP0级问题: {p0_count} 个")
    print(f"P1级问题: {p1_count} 个")
    print(f"P2级问题: {p2_count} 个")
    print(f"总问题数: {len(all_issues)} 个")

    if p0_count > 0:
        print("\n⛔ 检测到P0级污染，测试将被阻止")
        print("\n问题详情:")
        for issue in all_issues:
            if issue.severity == 'P0':
                print(f"\n  [{issue.severity}] {issue.category}")
                print(f"    文件: {issue.file_path}:{issue.line_number}")
                print(f"    描述: {issue.description}")
                print(f"    代码: {issue.code_snippet}")
    else:
        print("\n✅ 无P0级污染，测试可继续")
        if p1_count > 0 or p2_count > 0:
            print("\n低级别问题:")
            for issue in all_issues:
                if issue.severity != 'P0':
                    print(f"  [{issue.severity}] {issue.description} ({issue.file_path}:{issue.line_number})")

    is_clean = p0_count == 0
    return is_clean, all_issues


if __name__ == '__main__':
    is_clean, issues = run_purity_check()

    if not is_clean:
        print("\n⛔ 污染检测未通过，测试已阻止")
        sys.exit(1)
    else:
        print("\n✅ 污染检测通过")
        sys.exit(0)
