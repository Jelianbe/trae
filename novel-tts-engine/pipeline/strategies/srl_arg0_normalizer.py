from typing import Optional, List

from pipeline.nlp_basics import TITLE_WORDS, SRLArg0
from pipeline.matchers.name_validator import PER_BLACKLIST


# SRL 修饰语后缀
#
# 用途：去除 SRL ARG0 结果中的方位/位置修饰后缀
# 来源：中文方位词封闭集合
# 边界：
#   - 仅包含常用的方位/位置指示词
# 更新日期：2026-05-23
# 维护者：项目规则
_SRL_LOCATION_SUFFIXES = {'那边', '这里', '那里', '里面', '外面', '旁边', '前面', '后面'}


def _normalize_srl_arg0_denoise(raw_text: str) -> str:
    """SRL ARG0 去修饰语。
    
    步骤A：去除 ARG0 中的修饰语，保留核心实体名。
    
    规则1：去除"的"前修饰
        "严肃的赵总监" → "赵总监"
    规则2：去除动词短语前缀（本质也是"的"结构变体）
        "穿西装的张总" → "张总"
    规则3：去除方位后缀
        "张总那边" → "张总"
    
    Args:
        raw_text: SRL 提取的原始 ARG0 文本
        
    Returns:
        归一化后的文本
    """
    text = raw_text.strip()
    if not text:
        return text
    
    # 规则3：去除方位/位置后缀
    for suffix in _SRL_LOCATION_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[:-len(suffix)].strip()
            break
    
    # 规则1+2：去除"的"前修饰语
    # 取"的"后面的内容（如果"的"后面有足够的内容）
    if '的' in text:
        parts = text.split('的', 1)
        after_de = parts[1].strip()
        # 只在"的"后内容 >= 2 字时保留，避免"我的赵总监"→"赵总监"这种合理情况
        if len(after_de) >= 2:
            text = after_de
    
    return text


def _normalize_srl_arg0_strip_title(text: str) -> str:
    """SRL ARG0 去头衔后缀。
    
    步骤B：如果归一化后文本以 TITLE_WORDS 中的头衔结尾，
    尝试去除头衔并检查剩余部分是否有效。
    
    "艾琳法师" → "艾琳"
    "亚瑟团长" → "亚瑟"
    
    Args:
        text: 经过去修饰后的文本
        
    Returns:
        去除头衔后的文本
    """
    if not text or len(text) <= 2:
        return text
    
    for title in sorted(TITLE_WORDS, key=len, reverse=True):
        if text.endswith(title) and len(text) > len(title):
            stripped = text[:-len(title)].strip()
            if len(stripped) >= 1:
                return stripped
    
    return text


def _is_non_person_arg0(text: str) -> bool:
    """判断 ARG0 是否为非人物（需要过滤）。
    
    步骤C：非人物过滤。
    针对 PER_BLACKLIST 进行精确匹配和子串匹配。
    
    Args:
        text: 待检查的文本
        
    Returns:
        True 表示是非人物应过滤
    """
    if not text:
        return True
    
    # 精确黑名单匹配
    if text in PER_BLACKLIST:
        return True
    
    # 单字不可能是有效人物
    if len(text) <= 1:
        return True
    
    # 纯数字或太短的ASCII字母串（非人名）
    if text.isdigit():
        return True
    if text.isascii() and text.isalpha() and len(text) < 3:
        return True
    
    return False


def _normalize_srl_arg0(arg0: SRLArg0) -> Optional[str]:
    """完整的 SRL ARG0 归一化流程：去修饰 → 去头衔 → 非人物过滤。
    
    Args:
        arg0: SRL 提取的原始 ARG0
        
    Returns:
        归一化后的有效角色名，或 None（非人物/无效）
    """
    # 步骤A：去修饰语
    name = _normalize_srl_arg0_denoise(arg0.text)
    
    # 步骤B：去头衔后缀
    name = _normalize_srl_arg0_strip_title(name)
    
    # 步骤C：非人物过滤
    if _is_non_person_arg0(name):
        return None
    
    return name


def normalize_srl_arg0_candidates(raw_candidates: List[SRLArg0]) -> List[SRLArg0]:
    """归一化 SRL ARG0 候选列表。
    
    Args:
        raw_candidates: 原始 SRLArg0 列表
        
    Returns:
        归一化后的有效 SRLArg0 列表
    """
    return [c for c in raw_candidates if _normalize_srl_arg0(c) is not None]
