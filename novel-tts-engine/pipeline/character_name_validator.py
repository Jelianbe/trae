# -*- coding: utf-8 -*-
"""角色名称验证器：验证候选名称是否适合作为角色名

设计原则：
1. 基于中文命名规则（2-4字常见，单字姓氏+名）
2. 通过 HanLP 词性过滤动词型候选
3. 通过黑名单过滤非人名词

注意：
- SINGLE_CHAR_SURNAMES 基于中国前100大姓氏（覆盖85%人口）+ 网文高频虚构姓氏
  该集合有上限，不应无限扩容。新增条目需有语言学或统计依据。
"""

import logging
from typing import Optional, Set

from pipeline.nlp_basics import TITLE_WORDS

logger = logging.getLogger(__name__)


# 单字姓氏库
# 来源：中国公安部户籍统计前100大姓氏 + 网文高频虚构姓氏（如"萧"、"楚"）
# 约束：此集合基于真实姓氏统计，不应无限制扩容。当前约280条已覆盖绝大多数场景。
SINGLE_CHAR_SURNAMES: Set[str] = {
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
    '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
    '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
    '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
    '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
    '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
    '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
    '顾', '侯', '邵', '孟', '龙', '万', '段', '漕', '钱', '汤',
    '尹', '黎', '易', '常', '武', '乔', '贺', '赖', '龚', '文',
    # 网文高频虚构姓氏
    '楚', '秦', '林', '萧', '云', '风', '雷', '夜', '墨', '冷',
    '战', '厉', '君', '燕', '花', '柳', '梅', '竹', '琴', '剑',
}

# 非人名词黑名单（技术债务）
# 问题：此列表基于经验枚举而非统计验证，应逐步迁移至 ContextDiversityValidator 的统计阈值
# 建议：新增条目需基于大规模语料统计，而非个案补丁
PER_BLACKLIST: Set[str] = {
    '一个', '两个', '三个', '这个', '那个', '什么', '怎么', '为什么',
    '今天', '明天', '昨天', '现在', '时候', '地方', '东西', '事情',
    '样子', '办法', '问题', '可能', '可以', '应该', '一定', '非常',
    '而且', '但是', '所以', '因为', '如果', '虽然', '然而',
}


class CharacterNameValidator:
    """角色名称验证器"""

    def __init__(self, nlp=None):
        self.nlp = nlp
        # 扩展黑名单：合并预设黑名单和 false_person_words
        self._blacklist: Set[str] = PER_BLACKLIST | self._load_false_person_words()

    def _load_false_person_words(self) -> Set[str]:
        """加载非人名词黑名单（技术债务：来源为经验枚举）"""
        false_person_words = {
            '一声', '一眼', '一手', '一脚', '一头', '一边', '一半',
            '一切', '一起', '一定', '一点', '一些', '一般', '一样',
            '一直', '一向', '一旦', '一定', '一切',
            '突然', '忽然', '猛然', '骤然', '陡然', '赫然',
            '缓缓', '慢慢', '渐渐', '匆匆', '悄悄', '默默',
            '微微', '轻轻', '暗暗', '偷偷', '狠狠', '死死',
            '仿佛', '似乎', '好像', '犹如', '如同', '宛如',
        }
        return false_person_words

    def is_valid(self, name: str) -> bool:
        """验证名称是否适合作为角色名"""
        if not name or len(name) < 2 or len(name) > 6:
            return False

        if name in self._blacklist:
            return False

        if name in TITLE_WORDS:
            return False

        # 检查是否以有效姓氏开头
        if len(name) >= 2 and name[0] in SINGLE_CHAR_SURNAMES:
            return True

        # 名称不含常见非人名后缀
        non_person_suffixes = ['的', '了', '着', '过', '吗', '呢', '吧', '啊', '哦', '呀']
        if name[-1] in non_person_suffixes:
            return False

        return True

    def is_valid_speaker_candidate(self, name: str) -> bool:
        """验证名称是否适合作为说话人候选"""
        if not name or len(name) < 2 or len(name) > 8:
            return False

        if name in self._blacklist:
            return False

        return True

    def is_verb(self, name: str) -> bool:
        """判断名称是否为动词（通过 HanLP 词性标注或启发式规则）"""
        # 常见动词型后缀，这些出现在名称末尾时大概率是动词
        verb_suffixes = ['说道', '道', '说', '问', '喊', '叫', '笑', '叹',
                         '答', '应', '怒', '喝', '哼', '嚷', '跑', '走',
                         '看', '听', '想', '做', '打', '拿', '放', '吃']
        for suffix in verb_suffixes:
            if name.endswith(suffix) and len(name) > len(suffix):
                return True

        # 如果可用 HanLP，使用词性标注
        if self.nlp:
            try:
                result = self.nlp.analyze(name)
                for token in result.tokens:
                    if token.pos in ('v', 'vd', 'vf', 'vi', 'vl', 'vshi', 'vyou'):
                        return True
            except Exception:
                pass

        return False
