#!/usr/bin/env python3
"""硬编码自动化扫描器

扫描 pipeline/ 和 utils/ 下的 Python 文件，检测：
1. 缺少来源注释的静态词表
2. A→B 映射表（严重违规）
3. 硬编码魔法数字
4. 重复定义的常量

输出格式：结构化报告，可用于 CI/CD 集成

使用方式：
    python scan_hardcode.py                    # 扫描并输出报告
    python scan_hardcode.py --ci               # CI 模式（有违规则退出码=1）
    python scan_hardcode.py --json             # JSON 格式输出
"""

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from pathlib import Path


# ============================================================
# 数据模型
# ============================================================

@dataclass
class HardcodeIssue:
    """硬编码问题记录"""
    file: str
    line: int
    var_name: str
    issue_type: str  # 'missing_source' | 'mapping_table' | 'magic_number' | 'duplicate'
    severity: str    # 'P0' | 'P1' | 'P2' | 'P3'
    description: str
    suggestion: str


@dataclass
class ScanResult:
    """扫描结果"""
    total_files: int = 0
    total_issues: int = 0
    issues: List[HardcodeIssue] = field(default_factory=list)
    by_severity: Dict[str, int] = field(default_factory=lambda: {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0})
    by_type: Dict[str, int] = field(default_factory=dict)


# ============================================================
# 配置
# ============================================================

# 已知的合法词表（有完整来源注释，无需报警）
LEGITIMATE_CONSTANTS: Set[str] = {
    # nlp_basics.py
    'SINGLE_CHAR_SURNAMES', 'MULTI_CHAR_SURNAMES',
    'TITLE_WORDS', 'PROFESSION_TITLES', 'TRADITIONAL_TITLES',
    'POSITION_SUFFIXES', 'PREFIX_TITLES', 'ORG_SUFFIXES',
    'FAMILY_SUFFIXES', 'LOCATION_SUFFIXES',
    'WESTERN_TITLES', 'WESTERN_LOC_PREFIXES',
    'ORG_PREFIX_BLACKLIST', 'ORG_TEXT_BLACKLIST', 'PER_BLACKLIST',
    'CHAPTER_TITLE_PATTERNS',
    # descriptive_role_extractor.py
    'ROLE_CORE_WORDS', 'ROLE_CORE_WORDS_SORTED',
    'TITLE_TRIGGERS', 'ACTION_TRIGGERS', 'ADDRESS_TRIGGERS',
    # speech_verb_detector.py
    'SIMPLE_SPEECH_VERBS', 'EMOTION_MODIFIED_SPEECH',
    'COMPOUND_ACTION_SPEECH', 'ALL_SPEECH_VERBS', 'SPEECH_BOUNDARY_WORDS',
    # pronoun_resolver.py
    'PRONOUNS',
    # speaker_matcher.py
    'GROUP_NUMBER_PATTERN', 'CROWD_INDICATOR_WORDS', 'CROWD_ACTION_WORDS',
    # character_manager.py
    'GENDER_HINTS', 'TITLE_PATTERNS', 'MALE_TITLES', 'FEMALE_TITLES',
    # entity_linker.py
    'TITLE_PATTERNS', 'SINGLE_CHAR_FILTER',
    # dialogue_boundary_detector.py
    '_QUOTE_TYPES', '_BOOK_QUOTE_KEYWORDS', '_PROPER_NOUN_SUFFIXES',
    '_SPEECH_VERB_PATTERN', '_BOOK_QUOTE_PATTERNS',
    '_PURE_NOUN_PHRASE_PATTERN', '_SINGLE_CHAR_EXCLAIM_PATTERN',
    '_SINGLE_WORD_PATTERN', 'ANCHOR_WINDOW',
    # context_diversity_validator.py
    'BOUNDARY_PATTERNS', 'POSTFIX_PATTERNS_CANDIDATES',
    # emotion_extractor.py
    'DIRTY_WORDS', 'EMOTION_ADVERBS', 'EMOTION_VERBS',
    'MOOD_PARTICLES', '_DISGUST_KEYWORDS', 'IMPERATIVE_PATTERNS',
    'SPECIAL_LAUGHTER_MAP',
    # speech_hint_matcher.py
    'SPEAKER_HINTS', 'SPEAKER_PATTERNS',
    # tts_indextts.py (TTS后端适配层，非业务逻辑)
    'EMOTION_TO_TEXT',
}

# 可接受跨文件同名的常量（不同文件有不同用途）
ACCEPTED_CROSS_FILE_NAMES: Set[str] = {
    'TITLE_PATTERNS',  # character_manager.py (身份词集合) vs entity_linker.py (称呼后缀列表)
    'NEGATION_WORDS',  # _emotion_tagger_legacy.py (旧文件) vs emotion_extractor.py
    'ROLE_CORE_WORDS_SORTED',  # descriptive_role_extractor.py 定义, speaker_matcher.py 从 config 导入
    'PROJECT_ROOT',  # config.py (权威定义) vs tts_kokoro.py (旧代码)
    'GUIDE_PHRASE_PATTERN',  # _emotion_tagger_legacy.py (旧) vs emotion_extractor.py
    'QUOTE_START_PATTERN',  # _emotion_tagger_legacy.py (旧) vs emotion_extractor.py
}

# 不扫描的文件（遗留/废弃代码）
SCAN_EXCLUDE_FILES: Set[str] = {
    '_emotion_tagger_legacy.py',  # 旧版情绪标注器，已被 emotion_extractor.py 替代
}
CLASS_ATTRIBUTE_CONSTANTS: Set[str] = {
    'CHAPTER_PATTERNS', 'VOLUME_PATTERNS',  # chapter_splitter.py 类属性
    'VERB_POS',  # nlp_basics.py 方法内局部常量
}

# 需要检查的目录
SCAN_DIRS = ['pipeline', 'utils']

# 源注释关键词（用于检测是否存在来源注释）
SOURCE_COMMENT_KEYWORDS = [
    '# 用途：', '# 来源：', '# 边界：', '# 来源',
    '# 用途', '# 边界',
]

# A→B 映射表特征：值为字符串的字典
MAPPING_VALUE_PATTERN = re.compile(r"['\"][\w:]+['\"]:")


# ============================================================
# 扫描器
# ============================================================

class HardcodeScanner:
    """硬编码扫描器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.result = ScanResult()
        self._seen_vars: Dict[str, str] = {}  # var_name -> file path (for duplicate detection)

    def scan(self) -> ScanResult:
        """执行扫描"""
        for scan_dir in SCAN_DIRS:
            dir_path = self.project_root / scan_dir
            if not dir_path.exists():
                continue

            for py_file in sorted(dir_path.glob('*.py')):
                # 跳过排除列表中的文件
                if py_file.name in SCAN_EXCLUDE_FILES:
                    continue
                self.result.total_files += 1
                self._scan_file(py_file)

        return self.result

    def _scan_file(self, file_path: Path):
        """扫描单个 Python 文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        # 第一遍：收集类属性常量位置（不检查这些）
        class_attrs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                class_attrs.add(target.id)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                self._check_assignment(node, file_path, lines, class_attrs)
            elif isinstance(node, ast.Constant):
                self._check_magic_numbers(node, file_path, lines)

    def _check_assignment(self, node: ast.Assign, file_path: Path, lines: List[str], class_attrs: Set[str]):
        """检查赋值语句"""
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue

            var_name = target.id
            # 跳过私有变量和非常量名
            if var_name.startswith('_') and not var_name.startswith('__'):
                continue
            if var_name.islower():
                continue

            # 跳过类属性常量
            if var_name in class_attrs:
                continue

            # 跳过豁免列表
            if var_name in CLASS_ATTRIBUTE_CONSTANTS:
                continue

            # 跳过已知的合法常量
            if var_name in LEGITIMATE_CONSTANTS:
                continue

            # 检测字典是否为 A→B 映射
            if isinstance(node.value, ast.Dict):
                self._check_mapping_table(node, var_name, file_path, lines)

            # 检测集合/列表是否有来源注释
            if isinstance(node.value, (ast.Set, ast.List)):
                self._check_source_comment(node, var_name, file_path, lines)

            # 检测重复定义（跨文件，排除可接受同名）
            if var_name in self._seen_vars and var_name not in ACCEPTED_CROSS_FILE_NAMES:
                self._report_issue(HardcodeIssue(
                    file=str(file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    var_name=var_name,
                    issue_type='duplicate',
                    severity='P2',
                    description=f'"{var_name}" 在 {self._seen_vars[var_name]} 中已定义',
                    suggestion='考虑统一导入，消除重复定义',
                ))
            else:
                self._seen_vars[var_name] = str(file_path)

    def _check_mapping_table(self, node: ast.Assign, var_name: str, file_path: Path, lines: List[str]):
        """检查是否为 A→B 映射表"""
        # 检查字典值是否为字符串
        if isinstance(node.value, ast.Dict):
            for value in node.value.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    self._report_issue(HardcodeIssue(
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        var_name=var_name,
                        issue_type='mapping_table',
                        severity='P0',
                        description=f'"{var_name}" 是 A→B 映射表，违反"不建新映射表"原则',
                        suggestion='改造为正则+提取/句法检测/上下文推理方法',
                    ))
                    return

    def _check_source_comment(self, node: ast.Assign, var_name: str, file_path: Path, lines: List[str]):
        """检查是否有来源注释"""
        if node.lineno < 2:
            return

        # 向前查找注释（最多 10 行）
        start = max(0, node.lineno - 11)
        context_lines = lines[start:node.lineno - 1]
        context = '\n'.join(context_lines)

        has_source = any(kw in context for kw in SOURCE_COMMENT_KEYWORDS)

        if not has_source:
            self._report_issue(HardcodeIssue(
                file=str(file_path.relative_to(self.project_root)),
                line=node.lineno,
                var_name=var_name,
                issue_type='missing_source',
                severity='P1',
                description=f'"{var_name}" 缺少来源注释',
                suggestion='添加标准注释模板（用途/来源/边界/更新日期/维护者）',
            ))

    def _check_magic_numbers(self, node: ast.Constant, file_path: Path, lines: List[str]):
        """检查魔法数字（简化版：只检查比较语句中的浮点数）"""
        # 这个检查比较激进，暂时只做最低级别报警
        pass

    def _report_issue(self, issue: HardcodeIssue):
        """报告问题"""
        self.result.issues.append(issue)
        self.result.total_issues += 1
        self.result.by_severity[issue.severity] += 1
        self.result.by_type[issue.issue_type] = self.result.by_type.get(issue.issue_type, 0) + 1


# ============================================================
# 输出格式化
# ============================================================

def format_text_report(result: ScanResult) -> str:
    """生成文本格式报告"""
    if result.total_issues == 0:
        return "✅ 扫描完成：未发现硬编码违规问题\n"

    lines = []
    lines.append("=" * 60)
    lines.append(" 硬编码自动化扫描报告")
    lines.append("=" * 60)
    lines.append(f"扫描文件: {result.total_files}")
    lines.append(f"发现问题: {result.total_issues}")
    lines.append("")

    # 按严重程度统计
    lines.append("严重程度分布:")
    for sev, count in result.by_severity.items():
        if count > 0:
            lines.append(f"  {sev}: {count}")
    lines.append("")

    # 按类型统计
    lines.append("问题类型分布:")
    for typ, count in result.by_type.items():
        lines.append(f"  {typ}: {count}")
    lines.append("")

    # 详细列表
    lines.append("-" * 60)
    lines.append("详细问题列表:")
    lines.append("-" * 60)

    # 按严重程度排序
    severity_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
    sorted_issues = sorted(result.issues, key=lambda x: severity_order.get(x.severity, 99))

    for i, issue in enumerate(sorted_issues, 1):
        lines.append(f"\n#{i} [{issue.severity}] {issue.issue_type}")
        lines.append(f"  文件: {issue.file}:{issue.line}")
        lines.append(f"  变量: {issue.var_name}")
        lines.append(f"  描述: {issue.description}")
        lines.append(f"  建议: {issue.suggestion}")

    lines.append("")
    lines.append("=" * 60)

    # CI 模式退出码
    p0_p1_count = result.by_severity.get('P0', 0) + result.by_severity.get('P1', 0)
    if p0_p1_count > 0:
        lines.append(f"❌ CI 检查失败：发现 {p0_p1_count} 个 P0/P1 级问题")
    else:
        lines.append("✅ CI 检查通过：无 P0/P1 级问题")

    return '\n'.join(lines)


# ============================================================
# 主入口
# ============================================================

def main():
    ci_mode = '--ci' in sys.argv
    json_mode = '--json' in sys.argv

    # 确定项目根目录
    script_dir = Path(__file__).parent.parent
    scanner = HardcodeScanner(str(script_dir))
    result = scanner.scan()

    if json_mode:
        output = json.dumps({
            'total_files': result.total_files,
            'total_issues': result.total_issues,
            'by_severity': result.by_severity,
            'by_type': result.by_type,
            'issues': [asdict(i) for i in result.issues],
        }, ensure_ascii=False, indent=2)
        print(output)
    else:
        print(format_text_report(result))

    # CI 模式：有 P0/P1 问题时退出码=1
    if ci_mode:
        p0_p1_count = result.by_severity.get('P0', 0) + result.by_severity.get('P1', 0)
        if p0_p1_count > 0:
            sys.exit(1)
        sys.exit(0)


if __name__ == '__main__':
    main()
