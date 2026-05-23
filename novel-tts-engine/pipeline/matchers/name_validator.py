from typing import Set, Optional

# PER_BLACKLIST
#
# 用途：非人名词黑名单，用于过滤不可能作为人名的词汇
# 来源：基于经验枚举，应逐步迁移至 ContextDiversityValidator 的统计阈值
# 边界：
#   - 仅包含常见的非人名词汇（疑问词、时间词、连词等）
#   - 不包含领域特定词汇
# 更新日期：2026-05-14
# 维护者：内联自 character_name_validator.py
PER_BLACKLIST: Set[str] = {
    '一个', '两个', '三个', '这个', '那个', '什么', '怎么', '为什么',
    '今天', '明天', '昨天', '现在', '时候', '地方', '东西', '事情',
    '样子', '办法', '问题', '可能', '可以', '应该', '一定', '非常',
    '而且', '但是', '所以', '因为', '如果', '虽然', '然而',
}

# _SINGLE_CHAR_SURNAMES
#
# 用途：单字姓氏集合，用于人名验证（姓氏+名字结构）
# 来源：《百家姓》常见姓氏，约 280 条
# 边界：
#   - 仅包含常见的单字姓氏
#   - 不应无限制扩容
# 上限：约 280 条
# 更新日期：2026-05-14
# 维护者：内联自 character_name_validator.py
_SINGLE_CHAR_SURNAMES: Set[str] = {
    '赵', '钱', '孙', '李', '周', '吴', '郑', '王', '冯', '陈',
    '褚', '卫', '蒋', '沈', '韩', '杨', '朱', '秦', '尤', '许',
    '何', '吕', '施', '张', '孔', '曹', '严', '华', '金', '魏',
    '陶', '姜', '戚', '谢', '邹', '喻', '柏', '水', '窦', '章',
    '苏', '潘', '葛', '范', '彭', '鲁', '韦', '昌', '马', '苗',
    '凤', '花', '方', '俞', '任', '袁', '柳', '酆', '鲍', '史',
    '唐', '费', '廉', '岑', '薛', '雷', '贺', '倪', '汤', '滕',
    '殷', '罗', '毕', '郝', '邬', '安', '常', '乐', '于', '时',
    '傅', '皮', '卞', '齐', '康', '伍', '余', '元', '卜', '顾',
    '孟', '平', '黄', '萧', '程', '嵇', '邢', '滑', '裴', '陆',
    '荣', '翁', '荀', '羊', '於', '惠', '甄', '曲', '家', '封',
    '芮', '羿', '储', '靳', '汲', '邴', '糜', '松', '井', '段',
    '富', '巫', '乌', '焦', '巴', '弓', '牧', '隗', '山', '谷',
    '车', '侯', '宓', '蓬', '全', '郗', '班', '仰', '秋', '仲',
    '伊', '宫', '宁', '仇', '栾', '暴', '甘', '钭', '厉', '戎',
    '祖', '武', '符', '刘', '景', '詹', '束', '龙', '叶', '幸',
    '司', '韶', '郜', '黎', '蓟', '薄', '印', '宿', '白', '怀',
    '蒲', '邰', '从', '鄂', '索', '咸', '籍', '赖', '卓', '蔺',
    '屠', '蒙', '池', '乔', '阴', '郁', '胥', '能', '苍', '双',
    '闻', '莘', '党', '翟', '谭', '贡', '劳', '逄', '姬', '申',
    '扶', '堵', '冉', '宰', '郦', '雍', '郤', '璩', '桑', '桂',
    '濮', '牛', '寿', '通', '边', '扈', '燕', '冀', '郏', '浦',
    '尚', '农', '温', '别', '庄', '晏', '柴', '瞿', '阎', '充',
    '慕', '连', '茹', '习', '宦', '艾', '鱼', '容', '向', '古',
    '易', '慎', '戈', '廖', '庾', '终', '暨', '居', '衡', '步',
    '都', '耿', '满', '弘', '匡', '国', '文', '寇', '广', '禄',
    '阙', '东', '欧', '殳', '沃', '利', '蔚', '越', '夔', '隆',
    '师', '巩', '厍', '聂', '晁', '勾', '敖', '融', '冷', '訾',
    '辛', '阚', '那', '简', '饶', '空', '曾', '母', '沙', '乜',
    '养', '鞠', '须', '丰', '巢', '关', '蒯', '相', '查', '后',
    '荆', '红', '游', '竺', '权', '逯', '盖', '益', '桓', '公',
}

SINGLE_CHAR_SURNAMES = _SINGLE_CHAR_SURNAMES


class CharacterNameValidator:
    """角色名称验证器"""

    def __init__(self, nlp=None):
        self.nlp = nlp
        self._blacklist: Set[str] = PER_BLACKLIST | self._load_false_person_words()

    def _load_false_person_words(self) -> Set[str]:
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
        if not name or len(name) < 2 or len(name) > 6:
            return False
        if name in self._blacklist:
            return False
        if len(name) >= 2 and name[0] in SINGLE_CHAR_SURNAMES:
            return True
        non_person_suffixes = ['的', '了', '着', '过', '吗', '呢', '吧', '啊', '哦', '呀']
        if name[-1] in non_person_suffixes:
            return False
        return True

    def is_valid_speaker_candidate(self, name: str) -> bool:
        if not name or len(name) < 2 or len(name) > 20:
            return False
        if name in self._blacklist:
            return False
        return True

    def is_verb(self, name: str) -> bool:
        verb_suffixes = ['说道', '道', '说', '问', '喊', '叫', '笑', '叹',
                         '答', '应', '怒', '喝', '哼', '嚷', '跑', '走',
                         '看', '听', '想', '做', '打', '拿', '放', '吃']
        for suffix in verb_suffixes:
            if name.endswith(suffix) and len(name) > len(suffix):
                return True
        if self.nlp:
            try:
                result = self.nlp.analyze(name)
                for token in result.tokens:
                    if token.pos in ('v', 'vd', 'vf', 'vi', 'vl', 'vshi', 'vyou'):
                        return True
            except Exception:
                pass
        return False
