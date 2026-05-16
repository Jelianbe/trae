# -*- coding: utf-8 -*-
"""模式提取器：从文本中提取候选角色名（规则版）。

用途：角色发现模块的第一阶段提取器，使用正则表达式从文本中提取
      潜在的中文角色名，供 CharacterDiscoveryEngine 进一步处理。

策略：
  1. 正则提取"姓+职位"（如"赵总监"）
  2. 正则提取"名称+头衔"（如"亚瑟团长"）
  3. 强过滤：内置黑名单（物品、身体部位、抽象词、方位词），可配置。

注意：不实现 NER、SRL、LLM 等复杂提取（留作第二阶段）。
"""

import re
from typing import List, Dict

from utils.config import (
    DISCOVERY_SURNAME_TITLE_CONFIDENCE,
    DISCOVERY_NAME_TITLE_CONFIDENCE,
)
# 2026-05-16 大扫除：TITLE_WORDS 已合并 FANTASY_TITLE_SUFFIXES 内容
# FANTASY_TITLE_SUFFIXES 保留为 regex 专用子集，不再独立扩容
# 新增头衔词请更新 nlp_basics.TITLE_WORDS，而非此处
from pipeline.nlp_basics import TITLE_WORDS


# CORE_NAME_REJECTION_PATTERNS
#
# 用途：在 name_title 模式提取后，过滤核心名中不可能为人名的词片段
# 来源：中文语法——动词、形容词、介词短语不能作为人名
# 边界：仅保留最常见的误匹配模式，不应无限扩展
# 上限：约10条，不应无限制扩容
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
CORE_NAME_REJECTION_PATTERNS = ['乱只', '会让', '疲惫', '负责', '宽大']


# SURNAME_PATTERN
#
# 用途：匹配现代汉语百家姓中的单姓
# 来源：《百家姓》常见版本，约100个常用单姓
# 边界：
#   - 包含最常见的汉族姓氏（赵钱孙李...）
#   - 不包含复姓（欧阳、司马等），因复姓在网文中较少且易误匹配
# 上限：约100个单姓，封闭集合
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
SURNAME_PATTERN = (
    '赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张'
    '孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎'
    '鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤'
    '滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄'
    '和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞'
    '熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭'
    '梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫'
    '经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚'
)


# MODERN_TITLE_PATTERN
#
# 用途：匹配现代职场/机构常见职位后缀
# 来源：现代汉语职位名称封闭集，基于职场常见称呼
# 边界：
#   - 包含企业、政府、教育机构中的常见职位
#   - 使用 alternation（非字符类）以支持多字职位（如"总监"而非单字"总"）
# 上限：约15个职位，封闭集合
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
MODERN_TITLES = '总监|经理|局长|处长|科长|主任|队长|老板|老师|医生|护士|司机|保安|工程师'


# SURNAME_TITLE_PATTERN
#
# 用途：匹配"单姓+职位"组合（如"赵总监"）
# 来源：SURNAME_PATTERN + MODERN_TITLES 的组合
# 边界：仅匹配百家姓单姓 + 现代职位，不匹配复姓或古代头衔
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
SURNAME_TITLE_PATTERN = re.compile(
    r'(?<![0-9\u4e00-\u9fa5])'
    r'([' + SURNAME_PATTERN + r'])'
    r'(' + MODERN_TITLES + r')'
)


# FANTASY_TITLE_SUFFIXES
#
# 用途：匹配西幻/中文网文常见的角色头衔后缀
# 来源：中文网文角色头衔封闭集，基于奇幻/西幻文学常见角色类型
#       2026-05-16 大扫除：与 nlp_basics.TITLE_WORDS 有 5 条重叠
#       （长老/掌门/队长/掌柜/管家），已在 TITLE_WORDS 中统一维护
#       此列表仅保留用于 regex 构造，不做独立扩容
# 边界：
#   - 包含军事类（团长、队长、骑士、护卫）
#   - 包含魔法类（法师、牧师、主教、修士）
#   - 包含武侠/江湖类（剑客、刺客、杀手、掌门、长老）
#   - 包含市井类（铁匠、商人、猎人、掌柜、管家）
#   - 不包含泛化词（如"勇者"、"英雄"），因过于模糊
# 上限：约25个头衔，封闭集合
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
FANTASY_TITLE_SUFFIXES = [
    '团长', '骑士', '法师', '护卫', '士兵', '剑客', '刺客',
    '杀手', '牧师', '主教', '长老', '掌门', '队长', '掌柜',
    '管家', '丫鬟', '侍女', '侍卫', '铁匠', '商人', '猎人',
    '修士', '老战士', '治疗师',
]


# NAME_TITLE_PATTERNS
#
# 用途：匹配"名称+头衔"组合（如"亚瑟团长"、"梅林法师"）
# 来源：FANTASY_TITLE_SUFFIXES 的组合
# 边界：名称部分为 2-4 汉字，后缀为 FANTASY_TITLE_SUFFIXES 中的任一
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
NAME_TITLE_PATTERNS = [
    re.compile(r'([\u4e00-\u9fa5]{2,4})(?:' + '|'.join(FANTASY_TITLE_SUFFIXES) + r')')
]


# CHARACTER_BLACKLIST
#
# 用途：过滤非人物候选词，防止误提取物品/身体部位/抽象词等
# 来源：基于项目现有 NON_PERSON_CANDIDATE_EXCLUDES 扩展 + 中文语言封闭集
# 边界：
#   - 物品词：日常用品、办公物品、魔法物品
#   - 身体部位：人体器官/部位
#   - 抽象词：概念、情绪、状态
#   - 方位词：方位、位置
#   - 常见非人名词：连词、介词、副词等
# 上限：约80条去重后条目，不应无限制扩容
# 更新日期：2026-05-16
# 维护者：DISCOVERY-PREPROCESS
# 姐妹集合：nlp_basics.PER_BLACKLIST（用于 HanLP PER 实体过滤），
#           二集合互补而非重叠：CHAR 用于角色发现候选过滤，
#           PER 用于 NER 实体类型过滤
CHARACTER_BLACKLIST = {
    # 物品/场所
    '办公室', '会议室', '笔记本', '电脑', '皮椅', '茶杯', '文件', '手机',
    '桌子', '椅子', '门', '窗', '走廊', '房间',
    '烛台', '地图', '蜡烛', '烛火', '披风', '剑柄', '城墙', '铠甲', '武器', '盾牌',
    '长剑', '法杖', '护身', '寒冰', '火球', '月光', '夜色', '荒原',
    # 2026-05-16 合并自 speaker_matcher.NON_PERSON_CANDIDATE_EXCLUDES
    '符文', '魔法卷轴',
    # 身体部位
    '眼睛', '手', '头', '脚', '手指', '拳头', '嘴角', '肩膀', '心脏',
    '头发', '嘴唇', '脸', '背', '腿', '声音', '气息', '胡须',
    '面庞', '佩剑',
    # 抽象概念
    '数据', '压力', '能量', '魔法', '力量', '希望', '恐惧', '愤怒',
    '时间', '空间', '光芒', '阴影', '魔力', '咒语', '命令',
    # 2026-05-16 合并自 speaker_matcher.NON_PERSON_CANDIDATE_EXCLUDES
    '[对话]', '[音效]', '[强调]',
    # 方位词
    '前面', '后面', '左边', '右边', '上面', '下面', '中间', '里面', '外面',
    '这里', '那里', '哪里', '远处', '近处',
    # 常见非人名词（虚词/连词/介词）
    '但是', '因为', '所以', '虽然', '然而', '如果', '然后', '最后',
    '一个', '两个', '三个', '这个', '那个', '什么', '怎么', '为什么',
    '时候', '地方', '东西', '事情', '问题', '可能', '可以', '应该',
    '非常', '而且', '一定', '已经', '正在', '将要', '马上',
    '没有', '不是', '不会', '不能', '不要', '不好', '不对', '不行',
    '自己', '大家', '所有', '全部', '一起', '一直', '一般', '一样',
    # 动词/形容词开头（排除）
    '疲惫', '负责', '宽大', '沉着', '冷静', '迅速', '立刻',
    # 常见中文词组
    '众人', '骑士', '哨站', '斥候', '防御', '阵型', '防线', '弓箭',
    '北门', '东墙', '西门', '南门',
    # 西幻文本中的误匹配（基于测试数据发现）
    '作战会', '议室',
}


def extract_candidates(text: str) -> List[Dict]:
    """从文本中提取候选角色名。

    Args:
        text: 待提取的文本

    Returns:
        候选列表，每个元素为字典：
        {
            'name': str,
            'pattern': str,
            'confidence': float
        }
    """
    candidates = []
    seen_names = set()

    # 策略1: 姓+职位模式
    for match in SURNAME_TITLE_PATTERN.finditer(text):
        full_name = match.group(0)
        if full_name not in seen_names and full_name not in CHARACTER_BLACKLIST:
            candidates.append({
                'name': full_name,
                'pattern': 'surname_title',
                'confidence': DISCOVERY_SURNAME_TITLE_CONFIDENCE,
            })
            seen_names.add(full_name)

    # 策略2: 名称+头衔模式
    for pattern in NAME_TITLE_PATTERNS:
        for match in pattern.finditer(text):
            full_name = match.group(0)
            if full_name in seen_names or full_name in CHARACTER_BLACKLIST:
                continue
            # 提取核心名（去掉头衔后缀）
            core_name = full_name
            for ts in FANTASY_TITLE_SUFFIXES:
                if full_name.endswith(ts):
                    core_name = full_name[:-len(ts)]
                    break

            # 检查核心名是否合理（2-3 汉字）
            core_cn = [c for c in core_name if '\u4e00' <= c <= '\u9fff']
            if len(core_cn) < 2 or len(core_cn) > 3:
                continue

            # 过滤包含非人名词模式的核心名
            if any(word in core_name for word in CORE_NAME_REJECTION_PATTERNS):
                continue

            candidates.append({
                'name': full_name,
                'pattern': 'name_title',
                'confidence': DISCOVERY_NAME_TITLE_CONFIDENCE,
            })
            seen_names.add(full_name)

    return candidates
