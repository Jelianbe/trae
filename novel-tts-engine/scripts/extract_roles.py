# -*- coding: utf-8 -*-
"""最小可行角色提取器 v3（MVP）

设计目标：
1. 输入：一段网文全文
2. 扫描所有 "..." 对话单元
3. 对每个对话单元，向前扫描上下文
4. 用简单规则匹配角色名
5. 输出：{角色名: [出现位置列表]}

核心策略（v3 - 简化版）：
1. 全文扫描潜在人名（姓氏 + 1-3字）
2. 验证：必须在引号附近出现
3. 描述性称呼独立标记
4. 不依赖引述动词，太容易漏
"""

import re
import sys
import os
import json
import argparse
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from utils.zh_names import SINGLE_CHAR_SURNAMES, MULTI_CHAR_SURNAMES

# 描述性称呼核心词
DESCRIPTIVE_CORE_WORDS = [
    '管事', '老者', '老人', '中年修士', '中年', '青年', '少年', '少女',
    '男子', '女子', '男人', '女人', '中年人', '青年人', '少年人',
    '修士', '剑修', '法师', '骑士', '护卫', '士兵',
    '管家', '丫鬟', '侍女', '侍卫', '仆人', '小厮',
    '掌柜', '老板', '伙计', '客人', '道士', '和尚', '僧人',
    '首领', '头目', '统领', '将军',
]

# 非人名过滤词
NON_PERSON_WORDS = {
    # 常见动词/动作短语
    '回头', '点点头', '心中', '冷笑', '微笑',
    '迈步', '转身', '站起', '坐下', '抬手', '挥手',
    # 抽象概念/物品/地名（常被误识别）
    '风险', '石林', '火鸦', '玉瓶', '丹药', '符箓',
    '灵光', '机缘', '大道', '长生', '工匠', '命运',
    '明白', '知道', '好的', '规矩', '道理',
    # 代词/泛指
    '我们', '你们', '他们', '大家', '所有',
    '一个', '两个', '三个', '这个', '那个',
    # 常见形容词/副词（首字恰好是姓氏）
    '冰冷', '危险', '火苔', '那存', '乌黑', '索性',
    '幽石', '张遁', '石阴', '方向', '同时', '立刻',
    # 地名/物品名
    '火鸦涧', '幽石林', '石林立', '张遁地符', '孙项明依',
    '月笙如歌', '仙传', '简介',
}

# 不能作为人名组成部分的字（用于确定名字边界）
#
# 用途：当正则匹配到"孙项明心"时，检测到"心"是功能字，截断为"孙项明"
# 来源：中文语法 - 功能字/虚词/常见动词首字
# 边界：仅包含几乎不会出现在人名中间或末尾的字
# 更新日期：2026-05-22
# 维护者：scripts/extract_roles.py
NON_NAME_CHARS = {
    # 功能字/虚词
    '的', '了', '着', '过', '在', '有', '是', '不', '没',
    # 代词
    '他', '她', '它', '这', '那', '哪', '其',
    # 连词/介词
    '和', '与', '或', '但', '而', '因', '为', '从', '向', '对',
    # 常见动词/动作（不用于人名末尾）
    '心', '神', '身', '手', '脚', '眼', '口', '头',
    '走', '跑', '飞', '跳', '站', '坐', '躺', '看', '听',
    '想', '说', '问', '答', '喊', '叫', '笑', '哭',
    '拿', '放', '抓', '握', '推', '拉', '打', '杀',
    '来', '去', '回', '进', '出', '上', '下', '前', '后',
    '见', '觉', '感', '望', '盯', '扫', '瞥',
    '做', '干', '搞', '弄', '变', '成', '让', '给',
    '依', '顺', '随', '凭', '任',
    # 标点/空白
    ' ', '\n', '\t', '，', '。', '！', '？', '；', '：',
    '、', '"', '"', '"', '"', '「', '」', '『', '』',
}

# 动词后缀（用于排除 XX+动词 的情况）
VERB_SUFFIXES = {
    '回', '点', '沉', '迈', '走', '转', '站', '坐', '抬', '挥',
    '看', '听', '想', '感', '觉', '望', '盯', '扫',
    '接', '递', '拿', '放', '抓', '握', '推', '拉',
}


class MinimalRoleExtractor:
    """最小可行角色提取器"""
    
    def __init__(self):
        # 预编译人名模式 - 简单贪婪匹配，后处理截断
        surname_chars = ''.join(sorted(SINGLE_CHAR_SURNAMES))
        self.name_pattern = re.compile(
            r'([' + surname_chars + r'][\u4e00-\u9fa5]{1,3})'
        )
        # 复姓模式
        self.multi_surname_patterns = []
        for ms in MULTI_CHAR_SURNAMES:
            self.multi_surname_patterns.append(
                re.compile(re.escape(ms) + r'([\u4e00-\u9fa5]{1,2})')
            )
    
    def extract_from_novel(self, text: str, scan_length: int = 150) -> Dict:
        """从网文全文中提取角色信息"""
        quotes = self._find_all_quotes(text)
        
        # 第一步：全文扫描所有潜在人名
        all_potential_names = self._scan_all_names(text)
        
        # 第二步：过滤，只保留在引号附近出现的
        valid_names = self._filter_near_quotes(all_potential_names, quotes, text)
        
        # 第三步：提取描述性称呼
        descriptive_references = self._extract_descriptive(text, quotes, scan_length)
        
        # 第四步：构建结果
        quote_contexts = []
        for quote_start, quote_end, quote_content in quotes[:20]:
            context_start = max(0, quote_start - scan_length)
            context_text = text[context_start:quote_start]
            suffix_end = min(len(text), quote_end + 80)
            suffix_text = text[quote_end:suffix_end]
            
            quote_contexts.append({
                "quote": quote_content[:50],
                "prefix": context_text[-100:] if len(context_text) > 100 else context_text,
                "suffix": suffix_text[:80],
                "quote_pos": quote_start,
            })
        
        # 去重排序
        for k in valid_names:
            valid_names[k] = sorted(set(valid_names[k]))
        for k in descriptive_references:
            descriptive_references[k] = sorted(set(descriptive_references[k]))
        
        # 频率过滤：只保留出现 >= 2次的角色名（过滤一次性误匹配）
        # 描述性称呼不受此限制（可能只出现1次）
        valid_names = {k: v for k, v in valid_names.items() if len(v) >= 2}
        
        statistics = {
            "total_quotes": len(quotes),
            "unique_named_characters": len(valid_names),
            "unique_descriptive_references": len(descriptive_references),
            "top_named_characters": self._get_top_items(valid_names, 30),
            "top_descriptive_references": self._get_top_items(descriptive_references, 20),
        }
        
        return {
            "named_characters": dict(valid_names),
            "descriptive_references": dict(descriptive_references),
            "quote_contexts": quote_contexts,
            "statistics": statistics,
        }
    
    def _find_all_quotes(self, text: str) -> List[Tuple[int, int, str]]:
        """找到所有引号对话"""
        quotes = []
        
        # 中文双引号
        for match in re.finditer(r'\u201c([^\u201d]+)\u201d', text):
            quotes.append((match.start(), match.end(), match.group(1)))
        
        # 直角引号
        for match in re.finditer(r'\u300c([^\u300d]+)\u300d', text):
            quotes.append((match.start(), match.end(), match.group(1)))
        
        # 普通双引号
        for match in re.finditer(r'"([^"]+)"', text):
            if not any(abs(match.start() - q[0]) < 2 for q in quotes):
                quotes.append((match.start(), match.end(), match.group(1)))
        
        quotes.sort(key=lambda x: x[0])
        return quotes
    
    def _scan_all_names(self, text: str) -> Dict[str, List[int]]:
        """全文扫描所有潜在人名"""
        results = defaultdict(list)
        seen = set()  # (name, position) pairs to avoid duplicates
        
        # 单姓 + 1-3字
        for match in self.name_pattern.finditer(text):
            raw_name = match.group(1)
            # 截断到正确的名字边界
            name = self._truncate_to_name_boundary(raw_name)
            pos = match.start()
            key = (name, pos)
            
            if key not in seen and self._is_valid_name(name):
                results[name].append(pos)
                seen.add(key)
        
        # 复姓 + 1-2字
        for pattern in self.multi_surname_patterns:
            for match in pattern.finditer(text):
                raw_name = match.group(0)
                name = self._truncate_to_name_boundary(raw_name)
                pos = match.start()
                key = (name, pos)
                
                if key not in seen and self._is_valid_name(name):
                    results[name].append(pos)
                    seen.add(key)
        
        return results
    
    def _truncate_to_name_boundary(self, name: str) -> str:
        """截断名字到正确的边界
        
        例如："孙项明心" -> "孙项明"（因为"心"是功能字）
        """
        for i in range(1, len(name)):
            if name[i] in NON_NAME_CHARS:
                return name[:i]
        return name
    
    def _filter_near_quotes(self, all_names: Dict[str, List[int]], 
                            quotes: List[Tuple[int, int, str]], 
                            text: str) -> Dict[str, List[int]]:
        """过滤：只保留在引号附近（前后200字）出现的名字"""
        valid = defaultdict(list)
        
        # 构建引号区间列表（更高效）
        quote_ranges = []
        for q_start, q_end, _ in quotes:
            quote_ranges.append((max(0, q_start - 200), min(len(text), q_end + 200)))
        
        # 过滤：检查名字位置是否在任何引号区间内
        for name, positions in all_names.items():
            valid_positions = []
            for pos in positions:
                for range_start, range_end in quote_ranges:
                    if range_start <= pos <= range_end:
                        valid_positions.append(pos)
                        break
            if valid_positions:
                valid[name] = valid_positions
        
        return valid
    
    def _extract_descriptive(self, text: str, quotes: List[Tuple[int, int, str]], 
                             scan_length: int) -> Dict[str, List[int]]:
        """提取描述性称呼（只在引号上下文中）"""
        results = defaultdict(list)
        
        for q_start, q_end, _ in quotes:
            context_start = max(0, q_start - scan_length)
            context_text = text[context_start:q_end + 80]
            offset = context_start
            
            for desc_word in sorted(DESCRIPTIVE_CORE_WORDS, key=len, reverse=True):
                for match in re.finditer(re.escape(desc_word), context_text):
                    pos = offset + match.start()
                    results[desc_word].append(pos)
        
        return results
    
    def _is_valid_name(self, name: str) -> bool:
        """判断是否是有效的角色名"""
        if len(name) < 2 or len(name) > 4:
            return False
        
        if name in NON_PERSON_WORDS:
            return False
        
        # 首字检查
        if name[:2] in MULTI_CHAR_SURNAMES:
            pass  # 复姓开头，OK
        elif name[0] not in SINGLE_CHAR_SURNAMES:
            return False
        
        # 排除 XX+动词
        if len(name) == 2 and name[1] in VERB_SUFFIXES:
            return False
        
        # 排除包含功能字的
        invalid_chars = {'的', '了', '着', '过', '在', '有', '是', '不', '没', '他', '她'}
        if any(c in invalid_chars for c in name[1:]):
            return False
        
        return True
    
    def _get_top_items(self, data: Dict, n: int) -> List[Tuple[str, int]]:
        """获取出现频率最高的 N 项"""
        items = [(k, len(v)) for k, v in data.items()]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:n]


def main():
    parser = argparse.ArgumentParser(description='最小可行角色提取器 v3')
    parser.add_argument('input_file', help='输入网文文件路径')
    parser.add_argument('-o', '--output', help='输出 JSON 文件路径')
    parser.add_argument('-l', '--scan-length', type=int, default=150, help='向前扫描字符数')
    parser.add_argument('--max-chars', type=int, default=None, help='只处理前N个字符')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"错误：文件不存在 - {args.input_file}")
        sys.exit(1)
    
    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    if args.max_chars:
        text = text[:args.max_chars]
        print(f"截取前 {args.max_chars:,} 字符进行测试")
    
    print(f"文件大小：{len(text):,} 字符")
    print(f"扫描长度：{args.scan_length} 字符")
    print()
    
    import time
    start_time = time.time()
    
    extractor = MinimalRoleExtractor()
    result = extractor.extract_from_novel(text, args.scan_length)
    
    elapsed = time.time() - start_time
    print(f"提取耗时：{elapsed:.2f} 秒")
    print()
    
    stats = result['statistics']
    print(f"=== 提取结果统计 ===")
    print(f"对话总数：{stats['total_quotes']}")
    print(f"唯一角色名：{stats['unique_named_characters']}")
    print(f"唯一描述性称呼：{stats['unique_descriptive_references']}")
    print()
    
    print(f"=== 高频角色名 Top 30 ===")
    for name, count in stats['top_named_characters']:
        print(f"  {name}: {count} 次")
    print()
    
    print(f"=== 高频描述性称呼 Top 20 ===")
    for desc, count in stats['top_descriptive_references']:
        print(f"  {desc}: {count} 次")
    print()
    
    print(f"=== 对话上下文样本（前5个）===")
    for i, sample in enumerate(result['quote_contexts'][:5], 1):
        print(f"\n--- 样本 {i} ---")
        print(f"  prefix：...{sample['prefix']}")
        print(f"  quote：「{sample['quote']}」")
        print(f"  suffix：{sample['suffix']}...")
    print()
    
    # 保存 JSON
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(PROJECT_ROOT, 'output')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'extracted_roles_v3.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到：{output_path}")


if __name__ == '__main__':
    main()
