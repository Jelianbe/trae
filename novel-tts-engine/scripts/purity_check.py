#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯度检查脚本 (Purity Check)

用途：在假设验证前检查代码中是否存在硬编码污染。
检测目标：
1. 黑名单/白名单词表
2. 硬编码的规则列表
3. 未文档化的魔法数字

使用方式：
    python scripts/purity_check.py

输出：
    - 如果发现硬编码，输出警告并列出位置
    - 如果没有发现，输出"✅ 代码纯度检查通过"
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 检查的文件范围
CHECK_DIRS = [
    PROJECT_ROOT / 'pipeline',
    PROJECT_ROOT / 'scripts',
]

# 已知的合理硬编码（这些是架构设计需要的，不应标记为污染）
ALLOWED_PATTERNS = [
    # 对话引导词检测（v2.2方案，用于误合并检测）
    r"DIALOGUE_WORDS\s*=\s*\{",
    # 文件后缀、协议等基础设施常量
    r"ALLOWED_EXTENSIONS\s*=",
    r"SUPPORTED_PROTOCOLS\s*=",
]

# 硬编码污染模式
CONTAMINATION_PATTERNS = [
    # 黑名单/白名单
    (r"(BLACKLIST|WHITELIST|FORBIDDEN|PROHIBITED)\s*=\s*[\[\{]", "黑名单/白名单词表"),
    # 硬编码动词后缀/表情词表
    (r"(VERB_SUFFIXES|EMOTION_CHARS|EXPRESSION_ENDINGS)\s*=\s*[\[\{]", "动词后缀/表情词表"),
    # FALSE_PERSON_ENDINGS（已移除，如果再次出现应警告）
    (r"FALSE_PERSON_ENDINGS\s*=\s*\{", "虚假人名后缀黑名单（应使用统计方法替代）"),
    # SINGLE_CHAR_VERBS（已移除，如果再次出现应警告）
    (r"SINGLE_CHAR_VERBS\s*=\s*\{", "单字动词词表（应使用统计方法替代）"),
    # 非文档化的魔法数字
    (r"confidence\s*[><=]+\s*0\.[0-9]", "魔法数字（置信度阈值应在配置文件中定义）"),
]


def check_file_purity(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    检查单个文件的纯度
    
    返回：
        列表，每个元素为 (行号, 行内容, 警告类型)
    """
    issues = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return issues
    
    lines = content.split('\n')
    
    # 检查是否包含已知的合理硬编码
    is_allowed = False
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, content):
            is_allowed = True
            break
    
    if is_allowed:
        return issues
    
    # 检查硬编码污染
    for i, line in enumerate(lines, 1):
        # 跳过注释行
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue
        
        for pattern, warning_type in CONTAMINATION_PATTERNS:
            if re.search(pattern, line):
                issues.append((i, line.strip(), warning_type))
    
    return issues


def main():
    """主检查流程"""
    print("=" * 80)
    print("代码纯度检查 (Purity Check)")
    print("=" * 80)
    
    all_issues = []
    files_checked = 0
    
    for check_dir in CHECK_DIRS:
        if not check_dir.exists():
            continue
        
        for py_file in check_dir.rglob('*.py'):
            # 跳过测试文件和虚拟环境
            if 'test' in py_file.name.lower():
                continue
            if '.venv' in str(py_file) or 'venv' in str(py_file):
                continue
            
            issues = check_file_purity(py_file)
            if issues:
                all_issues.extend([
                    (py_file, line_no, line_content, warning_type)
                    for line_no, line_content, warning_type in issues
                ])
            files_checked += 1
    
    print(f"\n检查了 {files_checked} 个文件\n")
    
    if all_issues:
        print("⚠️  发现硬编码污染：\n")
        for file_path, line_no, line_content, warning_type in all_issues:
            rel_path = file_path.relative_to(PROJECT_ROOT)
            print(f"  📄 {rel_path}:{line_no}")
            print(f"     类型: {warning_type}")
            print(f"     内容: {line_content[:80]}...")
            print()
        
        print("=" * 80)
        print("❌ 代码纯度检查未通过")
        print("=" * 80)
        print("\n建议：")
        print("1. 使用统计方法替代硬编码词表")
        print("2. 将配置参数移到配置文件中")
        print("3. 参考'假设驱动开发方案'中的结构性健康指标")
        return 1
    else:
        print("=" * 80)
        print("✅ 代码纯度检查通过")
        print("=" * 80)
        print("\n未发现硬编码污染，代码健康度良好。")
        return 0


if __name__ == '__main__':
    sys.exit(main())
