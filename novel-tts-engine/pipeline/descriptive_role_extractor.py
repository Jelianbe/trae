# -*- coding: utf-8 -*-
"""描述性角色提取器：从修饰语+核心词结构中提取角色指称

设计原则：
1. MODIFIER_PATTERN 是通用正则结构，不是穷举词表
2. TITLE_TRIGGERS / ACTION_TRIGGERS / ADDRESS_TRIGGERS 是信号集合
   中文头衔/动作词有限，但需要定期验证是否因特定测试集而过拟合
"""

import re
import logging
from typing import List, Optional, Tuple, Set

logger = logging.getLogger(__name__)


# 头衔触发词（约25条）
# 基于中文社会称谓体系中的职衔类
TITLE_TRIGGERS = [
    '大人', '陛下', '殿下', '阁下', '阁下', '公子', '小姐', '夫人',
    '老爷', '少爷', '姑娘', '前辈', '前辈', '晚辈', '师傅', '师父',
    '长老', '掌门', '教主', '帮主', '城主', '族长', '家主',
]

# 动作触发词（约25条）
# 用于识别"XX做了某事"从而推断XX是说话人
ACTION_TRIGGERS = [
    '点头', '摇头', '皱眉', '转身', '站起', '坐下', '抬手', '挥手',
    '冷笑', '微笑', '苦笑', '大笑', '叹气', '摇头', '拍案', '拂袖',
    '推门', '推开门', '走进', '走入', '走出', '走出', '看向', '盯着',
    '扫了',
]

# 称呼触发词（约15条）
# 用于识别"XX，..."格式的直接称呼
ADDRESS_TRIGGERS = [
    '兄台', '兄', '弟', '妹', '姐', '叔', '伯', '婶', '姨',
    '姑', '舅', '哥', '贤弟', '贤兄', '仁兄',
]


class DescriptiveRoleExtractor:
    """描述性角色提取器：识别"修饰语+核心词"结构的角色指称
    
    例如："黑甲骑士"、"青衣女子"、"老者" 等
    """

    # 角色核心词（约55条）
    # 基于语言学称谓体系——社交称谓中的职衔类、职业类、身份类
    # 中文里能独立作为角色指称的社会身份词汇是有限的
    # 约束：此集合基于语言学分类，不应无限制扩容
    ROLE_CORE_WORDS = [
        '将军', '丞相', '元帅', '统领', '校尉', '大臣', '尚书', '宰相', '太傅',
        '总管', '掌门', '舵主', '堂主', '族长', '团长', '队长',
        '骑士', '剑客', '法师', '护卫', '士兵', '斥候', '杀手', '刺客',
        '盗贼', '佣兵', '猎人', '冒险者', '剑修', '修士',
        '管家', '丫鬟', '侍女', '侍卫', '铁匠', '商人', '牧师', '主教',
        '青年', '少年', '少女', '老者', '老人', '男子', '女子', '男人', '女人',
        '道士', '和尚', '僧人', '长老', '弟子', '前辈', '药老',
    ]
    ROLE_CORE_WORDS_SORTED = sorted(ROLE_CORE_WORDS, key=len, reverse=True)

    # 修饰语匹配模式（通用结构）
    # 匹配：颜色+甲/衣、年龄、性别、修饰性形容词等
    MODIFIER_PATTERN = (
        r'(?:'
        r'[黑白红蓝紫金银铁铜青灰赤绛翠黛玄]|'
        r'黑甲|白衣|青衣|红衣|蓝衣|紫衣|金甲|银甲|铁甲|'
        r'[老小长少中青幼]|'
        r'年[老迈轻少幼]|'
        r'[男女]|'
        r'[圣魔暗光血龙鹰狼凤虎蛇鬼]|'
        r'[未知神秘恐怖危险]|'
        r'中[年]|'
        r'[^\s，。！？\n「」『』""]{1,6}'
        r')?'
    )

    _role_pattern_cache = None

    def _get_role_pattern(self) -> re.Pattern:
        if self._role_pattern_cache is None:
            words_pattern = '|'.join(re.escape(w) for w in self.ROLE_CORE_WORDS_SORTED)
            full_pattern = f'({self.MODIFIER_PATTERN}(?:{words_pattern}))'
            self._role_pattern_cache = re.compile(full_pattern)
        return self._role_pattern_cache

    def extract(self, text: str) -> List[str]:
        """从文本中提取描述性角色指称"""
        if not text:
            return []

        results = []
        pattern = self._get_role_pattern()

        for match in pattern.finditer(text):
            role = match.group(1).strip()
            if len(role) >= 2 and role not in results:
                results.append(role)

        return results


class TitleTriggerMatcher:
    """头衔触发词匹配器"""

    def __init__(self, char_manager):
        self.char_manager = char_manager

    def match_by_title(self, title: str) -> Optional:
        """通过头衔匹配角色"""
        from pipeline.speaker_matcher import MatchResult

        all_chars = self.char_manager.get_all_characters()
        for char in all_chars:
            if title in char.name or title in char.aliases:
                return MatchResult(
                    character=char,
                    confidence=0.85,
                    match_type='title'
                )
        return None

    def extract_title_trigger_candidates(self, text: str) -> List[Tuple[str, str, float]]:
        """从文本中提取头衔触发词候选"""
        candidates = []
        for title in TITLE_TRIGGERS:
            if title in text:
                # 尝试匹配已知角色
                all_chars = self.char_manager.get_all_characters()
                for char in all_chars:
                    if title in char.name or title in char.aliases:
                        candidates.append((char.name, 'title_trigger', 0.80))
                        break
                else:
                    # 未知头衔，但可能是新角色
                    candidates.append((title, 'title_unknown', 0.40))

        return candidates


class AddressTriggerMatcher:
    """称呼触发词匹配器"""

    def __init__(self, char_manager):
        self.char_manager = char_manager

    def find_addressed_character(self, text: str) -> Optional:
        """找到被称呼的角色"""
        for addr in ADDRESS_TRIGGERS:
            if addr in text:
                all_chars = self.char_manager.get_all_characters()
                for char in all_chars:
                    if addr in char.aliases or char.name.endswith(addr):
                        return char
        return None
