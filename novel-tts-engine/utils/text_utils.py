# -*- coding: utf-8 -*-
"""
文本处理工具：智能句子分割
解决引号内句子被错误拆分的问题。
"""

import re
from typing import List


# 句子结束标点（句号、问号、叹号、分号）
_SENTENCE_END_PATTERN = re.compile(r'([。！？；])')

# 中文引号对（用于检测引号内的文本）
_QUOTE_PAIRS = [
    ('"', '"'),      # 直引号
    ('\u201c', '\u201d'),  # 中文引号 " "
    ('「', '」'),     # 日式引号
    ('『', '』'),     # 双日式引号
    ('〈', '〉'),     # 单书名号
    ('《', '》'),     # 双书名号
]


def _find_quote_boundaries(text: str) -> List[tuple]:
    """
    找出所有引号对的起止位置。
    
    Returns:
        列表，每个元素为 (start, end) 元组，表示引号对的范围。
    """
    boundaries = []
    for open_quote, close_quote in _QUOTE_PAIRS:
        start = 0
        while True:
            open_pos = text.find(open_quote, start)
            if open_pos == -1:
                break
            close_pos = text.find(close_quote, open_pos + 1)
            if close_pos == -1:
                break
            boundaries.append((open_pos, close_pos + 1))
            start = close_pos + 1
    return boundaries


def split_sentences_smart(text: str) -> List[str]:
    """
    智能句子分割：避免将引号内的内容错误拆分。
    
    传统 split('[。！？]') 会把引号内的句子也拆开，
    例如："你好。"他说。 -> 会被拆成 ['"你好', '"他说']
    
    本函数会识别引号对，保护引号内的完整内容。
    
    Args:
        text: 需要分割的文本。
        
    Returns:
        分割后的句子列表，每个句子保留原有的标点符号。
        
    Examples:
        >>> split_sentences_smart('苏夜说道："你好。我是苏夜。"')
        ['苏夜说道："你好。我是苏夜。"']
        
        >>> split_sentences_smart('第一章。苏夜醒来。他看了看四周。')
        ['第一章', '苏夜醒来', '他看了看四周']
    """
    if not text or not text.strip():
        return []
    
    # 找出所有引号边界
    quote_boundaries = _find_quote_boundaries(text)
    
    if not quote_boundaries:
        # 没有引号，使用简单分割
        sentences = _SENTENCE_END_PATTERN.split(text)
        result = []
        current = ""
        for part in sentences:
            if _SENTENCE_END_PATTERN.match(part):
                current += part
                if current.strip():
                    result.append(current.strip())
                current = ""
            else:
                current += part
        if current.strip():
            result.append(current.strip())
        return result
    
    # 有引号，需要保护引号内的内容
    sentences = []
    current = ""
    i = 0
    text_len = len(text)
    
    while i < text_len:
        char = text[i]
        current += char
        
        # 检查当前字符是否是句子结束标点
        if _SENTENCE_END_PATTERN.match(char):
            # 检查当前位置是否在某个引号对内部
            in_quotes = False
            for q_start, q_end in quote_boundaries:
                if q_start <= i < q_end:
                    in_quotes = True
                    break
            
            if not in_quotes:
                # 不在引号内，可以拆分
                if current.strip():
                    sentences.append(current.strip())
                current = ""
        
        i += 1
    
    # 处理剩余部分
    if current.strip():
        sentences.append(current.strip())
    
    return sentences
