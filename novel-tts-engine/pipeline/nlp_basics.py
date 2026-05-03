import hanlp
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
import re
import threading
import warnings
import logging
from collections import Counter

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

HANLP_MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models', 'hanlp')

# Chapter title patterns that should be filtered from NER results
CHAPTER_TITLE_PATTERNS = [
    re.compile(r'^第[一二三四五六七八九十百千万零\d]+[章节回卷]'),
    re.compile(r'^卷[一二三四五六七八九十百千万零\d]+'),
    re.compile(r'^第[一二三四五六七八九十\d]+'),
    re.compile(r'^\d+[章节回卷]'),
]


@dataclass
class Token:
    text: str
    pos: str
    lemma: str = ""
    ner: str = "O"


@dataclass
class Entity:
    text: str
    type: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class NLPResult:
    tokens: List[Token]
    entities: List[Entity]
    sentences: List[str]
    pos_tags: List[Tuple[str, str]]
    raw_text: str


TITLE_WORDS = {
    '管家', '老爷', '夫人', '少爷', '小姐', '公子', '姑娘',
    '掌柜', '老板', '掌门', '长老', '堂主', '舵主',
    '将军', '大人', '王爷', '皇上', '皇后', '贵妃',
    '师父', '师叔', '师兄', '师弟', '师姐', '师妹',
    '博士', '教授', '医生', '护士', '律师', '记者',
    '经理', '总裁', '总监', '部长', '局长', '队长',
    # FO-08: 玄幻类称谓扩展（2026-05-02 修正方案）
    '导师', '学长', '执事',
}

# 职业称呼后缀（可作为人名识别）
# PROFESSION_TITLES 是 TITLE_WORDS 的子集，专门用于职业相关的称呼
PROFESSION_TITLES = {
    '博士', '教授', '医生', '护士', '律师', '记者',
    '经理', '总裁', '总监', '部长', '局长', '队长',
}

# 传统称呼后缀（身份相关的称呼）
TRADITIONAL_TITLES = {
    '管家', '老爷', '夫人', '少爷', '小姐', '公子', '姑娘',
    '掌柜', '老板', '掌门', '长老', '堂主', '舵主',
    '将军', '大人', '王爷', '皇上', '皇后', '贵妃',
    '师父', '师叔', '师兄', '师弟', '师姐', '师妹',
    # FO-08: 玄幻类称谓扩展（2026-05-02 修正方案）
    # 仅保留能独立作为说话人提示的身份词，排除关系称呼（师尊/徒儿等）
    '导师', '学长', '执事',
}

# 验证: TITLE_WORDS == PROFESSION_TITLES | TRADITIONAL_TITLES
assert TITLE_WORDS == (PROFESSION_TITLES | TRADITIONAL_TITLES), "TITLE_WORDS 应该等于 PROFESSION_TITLES 和 TRADITIONAL_TITLES 的并集"

# 职位称呼后缀（X总/X哥/X姐/X叔/X伯）
POSITION_SUFFIXES = {
    '总', '哥', '姐', '叔', '伯', '姨', '婶', '爷', '公', '婆',
}

PREFIX_TITLES = {'老', '小', '大'}

ORG_SUFFIXES = {'会', '帮', '社', '团', '协会', '联盟', '组织', '集团', '公司', '企业', '商会', '公会', '教派', '宗门'}

# 家族后缀（2026-05-02 扩展）
FAMILY_SUFFIXES = {
    '家', '府', '族', '宅', '院', '堡', '庄', '邸', '第', '舍',
    '庐', '亭', '堂', '斋', '轩', '阁', '楼', '台', '苑', '园',
    '山庄',
}

# 地点后缀（2026-05-02 扩展）
LOCATION_SUFFIXES = {
    '城', '镇', '村', '山', '河', '湖', '海', '岛', '谷', '峰',
    '岭', '原', '川', '泽', '林', '森', '漠', '殿', '宫', '哨站',
    '要塞', '堡垒', '营地', '关', '隘', '渡', '津', '桥', '崖',
    '渊', '潭', '泉', '溪', '涧', '洞', '窟', '峡', '坪',
}

# 注意：FAMILY_SUFFIXES 和 LOCATION_SUFFIXES 当前已不再用于说话角色识别管道。
# 它们被保留在代码中是为了保持向后兼容，但 _detect_surname_based_entities
# 中不再使用它们来创建 ORG/LOC 实体（参见 2026-05-02 修正方案）。
# 如果将来需要重新启用组织/地点识别，可以从版本控制历史恢复相关逻辑。

# 西方奇幻/翻译体特有名字模式
WESTERN_NAME_PREFIXES = {
    # 常见西方人名前缀（翻译体）
    '艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯',
    '亚瑟', '兰斯洛特', '梅林', '盖文', '崔斯坦', '珀西瓦尔',
    '阿拉贡', '莱戈拉斯', '金雳', '佛罗多', '甘道夫', '萨鲁曼',
    '阿尔萨斯', '吉安娜', '希尔瓦娜', '安杜因', '瓦里安',
    '凯尔', '莉亚', '雷诺', '雷诺兹', '泰兰德', '玛法里奥',
    '伊利丹', '玛维', '卡德加', '麦迪文', '克尔苏加德',
    '乌瑟尔', '提里奥', '佛丁', '图拉扬', '奥蕾莉亚',
    '安娜', '艾琳', '艾米', '奥利维亚', '伊丽莎白',
    '威廉', '亨利', '理查', '罗伯特', '爱德华', '查理',
    '亚历山大', '尼古拉', '维克多', '弗拉基米尔',
}

# 西方奇幻常见称呼/头衔（翻译体）
WESTERN_TITLES = {
    '骑士', '法师', '牧师', '圣骑士', '游侠', '德鲁伊',
    '术士', '战士', '盗贼', '猎人', '牧师', '主教',
    '团长', '副团长', '队长', '副官', '指挥官',
    '国王', '女王', '王子', '公主', '公爵', '伯爵', '侯爵',
    '陛下', '阁下', '大人', '爵士', '殿下',
    '信使', '哨兵', '斥候', '物资官', '书记员',
}

# ORG后缀检测的前缀黑名单（这些词后面跟"会/组织"等不应识别为ORG）
ORG_PREFIX_BLACKLIST = {
    # 常见代词/指示词
    '我们', '你们', '他们', '大家', '所有',
    # 常见名词（非人名/非组织名）
    '炎魔', '恶魔', '怪物', '敌人', '人类', '精灵', '矮人',
    '魔法', '黑暗', '光明', '圣光', '火焰', '冰霜',
    # 动词/副词
    '立即', '马上', '立刻', '准备', '开始', '继续',
    # 其他常见非组织词
    '一个', '这个', '那个', '这些', '那些',
    '黑暗法师', '光明法师', '黑袍人', '白袍人',
}

# ORG实体完整文本黑名单（HanLP直接误识别的完整ORG实体）
ORG_TEXT_BLACKLIST = {
    '我们会', '你们会', '他们会', '大家会',
    '炎魔会', '恶魔会',
    '立即组织', '马上组织',
    '黑暗法师', '光明法师',
}

# PER实体类型过滤黑名单（不应被识别为PER的常见词）
PER_BLACKLIST = {
    # 地点词
    '王都', '都城', '首都', '皇城', '京城', '城池',
    # 组织/群体词
    '众人', '人们', '大家', '百姓', '民众', '骑士们', '士兵们',
    '工匠们', '魔法师', '骑士团', '军队',
    # 怪物/生物
    '炎魔', '恶魔', '怪物', '魔王', '巨龙', '魔兽',
    '黑袍人', '白袍人', '陌生人', '路人',
    # 抽象概念
    '黑暗', '光明', '圣光', '希望', '正义',
    # 物品
    '剑', '盾', '法杖', '武器', '药水',
}

# 西方奇幻地名前缀模式（用于LOC增强）
WESTERN_LOC_PREFIXES = {
    '灰石', '白银', '黄金', '黑铁', '暗影', '风暴',
    '冰霜', '火焰', '雷霆', '月光', '日光', '星辰',
    '翡翠', '水晶', '血色', '铁壁', '龙骨', '鹰巢',
    # HanLP分词可能拆开的词（需要在raw_text层面匹配）
    '灰', '银', '金', '黑', '红', '蓝', '绿', '白',
    '铁', '钢', '铜', '石', '岩', '木',
}


# 单字姓氏库（2026-05-02 修正方案）
# 策略：保留真实高频姓氏 + 网文虚构姓氏，不穷举百家姓
# 穷举会导致噪声（如'武'、'容'被误识别为姓氏）
SINGLE_CHAR_SURNAMES = {
    # === 中国前100大姓氏（覆盖约85%人口）===
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
    '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
    '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
    '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
    '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
    '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
    '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
    '顾', '侯', '邵', '孟', '龙', '万', '段', '雷', '钱', '汤',
    '尹', '黎', '易', '常', '乔', '贺', '赖', '龚', '文', '庞',

    # === 常见补充姓氏 ===
    '樊', '兰', '殷', '施', '陶', '洪', '温', '芦', '牛', '安',
    '莫', '章', '仇', '祖', '符', '柳', '邢', '梅', '阮', '倪',
    '齐', '岳', '柴', '颜', '屈', '项', '祝', '蓝', '闵', '席',
    '季', '麻', '强', '路', '娄', '危', '童', '盛', '刁', '骆',
    '凌', '霍', '虞', '支', '柯', '管', '房', '缪', '干', '解',
    '应', '宗', '宣', '郁', '单', '杭', '包', '诸', '左', '吉',
    '钮', '滑', '裴', '荣', '翁', '荀', '甄', '曲', '封', '储',
    '靳', '松', '井', '富', '巫', '乌', '谷', '车', '全', '班',
    '宫', '宁', '栾', '暴', '甘', '厉', '戎', '景', '詹', '束',
    '幸', '司', '郜', '薄', '印', '宿', '怀', '蒲', '索', '卓',
    '蔺', '蒙', '池', '阴', '胥', '苍', '双', '闻', '莘', '翟',
    '劳', '姬', '申', '扶', '堵', '冉', '桑', '桂', '边', '扈',
    '尚', '农', '别', '庄', '晏', '瞿', '阎', '慕', '连', '茹',
    '向', '古', '慎', '戈', '终', '衡', '步', '耿', '满', '弘',
    '匡', '国', '寇', '禄', '沃', '蔚', '越', '隆', '巩', '聂',
    '晁', '冷', '辛', '那', '简', '饶', '沙', '养', '丰', '荆',
    '游', '权', '盖', '桓', '公', '欧', '诸', '葛', '令', '狐',
    '夏', '孙', '长', '宇', '轩', '辕', '独', '孤', '慕', '容',

    # === 玄幻/仙侠/网文高频虚构姓氏 ===
    # 这些字在常规中文中不一定是姓氏，但在网文语境中高频出现在人名首位
    '药', '云', '风', '火', '雷', '冰', '雪', '霜', '月', '星',
    '夜', '冥', '幽', '玄', '苍', '荒', '虚', '天', '灵', '神',
    '仙', '魔', '鬼', '妖', '龙', '凤', '凰', '麒', '麟',
    '羽', '花', '柳', '叶', '竹', '松', '梅', '兰', '菊', '莲',
    '水', '木', '岩', '海', '湖',
    '影', '虹', '霞', '雾', '烟', '露', '辰',
    '暮', '晓', '朝', '夕', '晨', '昏', '暗', '光', '明',
    '炎', '熙', '昊', '瀚',
    '墨', '青', '紫', '赤', '银', '铜', '玉',
    '砂', '尘', '岚', '陌', '棠', '槐',
    '念', '思', '忆', '梦',
    '蓝', '碧', '翠', '素', '锦', '绮',
    '楚', '燕', '秦', '魏',
}

MULTI_CHAR_SURNAMES = {
    '欧阳', '司马', '上官', '诸葛', '东方', '皇甫', '南宫', '西门',
    '独孤', '慕容', '轩辕', '令狐', '夏侯', '公孙', '长孙', '宇文',
}


class NLPBasics:
    def __init__(self, use_offline: bool = True, enable_foreign_name_merge: bool = True):
        self.pipeline = None
        self._initialized = False
        self.enable_foreign_name_merge = enable_foreign_name_merge
        
        if use_offline:
            os.environ['HANLP_HOME'] = HANLP_MODEL_DIR
        
        self._init_models()

    def _init_models(self):
        try:
            self.pipeline = hanlp.load(
                hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH
            )
            self._initialized = True
            logger.info("HanLP模型加载成功")
        except Exception as e:
            logger.warning(f"HanLP模型加载失败: {e}")
            logger.warning("将使用简化模式...")
            self._initialized = False

    def analyze(self, text: str) -> NLPResult:
        if not text or not text.strip():
            return NLPResult(
                tokens=[],
                entities=[],
                sentences=[],
                pos_tags=[],
                raw_text=text
            )
        
        sentences = self._split_sentences(text)
        
        if self._initialized:
            return self._analyze_with_hanlp(text, sentences)
        else:
            return self._analyze_simple(text, sentences)

    def _analyze_with_hanlp(self, text: str, sentences: List[str]) -> NLPResult:
        try:
            all_tokens = []
            all_pos_tags = []
            all_entities = []
            
            for sent in sentences:
                if not sent.strip():
                    continue
                
                result = self.pipeline(sent)
                
                tokens = result.get('tok/fine', [])
                pos_tags = result.get('pos/ctb', [])
                ner_result = result.get('ner/msra', [])
                
                if os.getenv('DEBUG_NER'):
                    print(f"[DEBUG] 句子: {sent}")
                    print(f"[DEBUG] HanLP NER原始输出: {ner_result}")
                
                for i, token in enumerate(tokens):
                    pos = pos_tags[i] if i < len(pos_tags) else 'X'
                    all_tokens.append(Token(text=token, pos=pos))
                    all_pos_tags.append((token, pos))
                
                hanlp_entities = self._parse_ner_result(ner_result)
                
                if os.getenv('DEBUG_NER'):
                    print(f"[DEBUG] 解析后实体: {[(e.text, e.type) for e in hanlp_entities]}")
                
                enhanced_entities = self._enhance_entities(tokens, pos_tags, hanlp_entities, raw_text=sent)
                
                if os.getenv('DEBUG_NER'):
                    print(f"[DEBUG] 增强后实体: {[(e.text, e.type) for e in enhanced_entities]}")
                    print()
                
                # ORG/LOC处理移除（2026-05-02 修正方案）
                # 只保留PER类型实体，减少内存占用和后续处理时间
                # ORG/LOC提取逻辑保留在代码中，但在此处过滤
                all_entities.extend([e for e in enhanced_entities if e.type == 'PER'])
            
            return NLPResult(
                tokens=all_tokens,
                entities=all_entities,
                sentences=sentences,
                pos_tags=all_pos_tags,
                raw_text=text
            )
        except Exception as e:
            logger.warning(f"HanLP分析失败: {e}")
            return self._analyze_simple(text, sentences)

    def _parse_ner_result(self, ner_result: List) -> List[Entity]:
        entities = []
        for ner_item in ner_result:
            if isinstance(ner_item, (list, tuple)) and len(ner_item) >= 3:
                entity_text = ner_item[0]
                entity_type = ner_item[1]
                start = ner_item[2] if len(ner_item) >= 3 else 0
                end = ner_item[3] if len(ner_item) >= 4 else start + 1
                confidence = ner_item[4] if len(ner_item) >= 5 else 0.9
                
                normalized_type = self._normalize_entity_type(entity_type)
                
                entities.append(Entity(
                    text=entity_text,
                    type=normalized_type,
                    start=start,
                    end=end,
                    confidence=confidence
                ))
        
        return entities

    def _normalize_entity_type(self, entity_type: str) -> str:
        type_map = {
            'PERSON': 'PER',
            'LOCATION': 'LOC',
            'ORGANIZATION': 'ORG',
            'GPE': 'LOC',
            'NR': 'PER',
            'NS': 'LOC',
            'NT': 'ORG',
        }
        return type_map.get(entity_type.upper(), entity_type)

    def _enhance_entities(self, tokens: List[str], pos_tags: List[str],
                          base_entities: List[Entity], raw_text: Optional[str] = None) -> List[Entity]:
        """增强实体识别结果，通过规则补充 HanLP 未识别的实体。

        主方法负责协调各子规则的执行顺序。
        """
        rule_entities: List[Entity] = []
        rule_covered_indices: set = set()
        rule_entity_texts: set = set()

        is_western = self._detect_western_style(tokens, pos_tags, raw_text)

        # 检测文体：如果包含西方译名特征，跳过中文特化规则
        if is_western:
            # 对西方文体，应用PER/ORG黑名单过滤
            filtered = self._apply_entity_blacklist(base_entities)
            # 增强西方LOC识别
            loc_entities = self._detect_western_locations(tokens, pos_tags, rule_covered_indices)
            return self._combine_entities(loc_entities, set(), set(), filtered)

        # 合并西方名字（如 "亚瑟·潘德拉贡"）
        if self.enable_foreign_name_merge:
            foreign_entities, covered, texts = self._merge_foreign_names(tokens, pos_tags)
            rule_entities.extend(foreign_entities)
            rule_covered_indices.update(covered)
            rule_entity_texts.update(texts)

        # 检测前缀称呼（老陈/小李）
        prefix_entities = self._detect_prefix_titles(tokens, pos_tags, rule_covered_indices)
        self._merge_rule_results(rule_entities, rule_covered_indices, rule_entity_texts, prefix_entities)

        # 检测职业称呼（博士/教授）
        profession_entities = self._detect_profession_titles(tokens, pos_tags, rule_covered_indices)
        self._merge_rule_results(rule_entities, rule_covered_indices, rule_entity_texts, profession_entities)

        # 检测组织后缀（暗影会/异能者联盟）
        org_entities = self._detect_org_suffixes(tokens, pos_tags, rule_covered_indices)
        self._merge_rule_results(rule_entities, rule_covered_indices, rule_entity_texts, org_entities)

        # 检测职位称呼（张总/李哥）和传统称呼（陈管家/林少爷）
        surname_entities = self._detect_surname_based_entities(tokens, pos_tags, rule_covered_indices)
        self._merge_rule_results(rule_entities, rule_covered_indices, rule_entity_texts, surname_entities)

        # 合并规则实体和基础实体
        combined = self._combine_entities(rule_entities, rule_entity_texts, rule_covered_indices, base_entities)

        # 全局黑名单过滤（所有文体都应用）
        combined = self._apply_entity_blacklist(combined)
        
        # 2026-05-02 修复：过滤HanLP误识别的虚假人名（如"萧炎冷"、"萧炎承"）
        # "萧炎冷笑道" → HanLP识别为"萧炎冷"(人名)
        # "萧炎承喏道" → HanLP识别为"萧炎承"(人名)
        combined = self._filter_false_persons(combined)

        # 非西方文体也尝试检测西方LOC（如'灰石哨站'），使用独立覆盖集
        loc_covered = set()
        loc_entities = self._detect_western_locations(tokens, pos_tags, loc_covered)
        if loc_entities:
            return self._combine_entities(loc_entities, set(), set(), combined)

        return combined

    def _detect_western_style(self, tokens: List[str], pos_tags: List[str],
                              raw_text: Optional[str]) -> bool:
        """检测是否包含西方译名特征（如"·"分隔符或大量非中文姓氏的NR词）。"""
        text = raw_text or ''
        if '·' in text:
            return True
        # 检查是否包含大量非中文姓氏的NR词
        for t, pos in zip(tokens, pos_tags[:len(tokens)]):
            if pos in ('NR', 'nr') and t not in SINGLE_CHAR_SURNAMES and t not in MULTI_CHAR_SURNAMES:
                return True
        return False

    def _apply_entity_blacklist(self, entities: List[Entity]) -> List[Entity]:
        """对西方文体应用实体类型黑名单过滤。

        解决常见问题：
        - '王都' 被 HanLP 误识别为 PER（应为 LOC）
        - '我们会' / '炎魔会' 等被误识别为 ORG
        - '黑暗法师' 等被误识别为 ORG
        """
        filtered: List[Entity] = []
        for e in entities:
            # PER 黑名单过滤：将误识别的 PER 转为正确的类型或直接过滤
            if e.type == 'PER' and e.text in PER_BLACKLIST:
                # 如果是地点词，转换为 LOC
                loc_words = {'王都', '都城', '首都', '皇城', '京城', '城池'}
                if e.text in loc_words:
                    filtered.append(Entity(
                        text=e.text, type='LOC', start=e.start, end=e.end,
                        confidence=max(getattr(e, 'confidence', 1.0), 0.8),
                    ))
                # 否则过滤掉
                continue

            # ORG 黑名单过滤（前缀词+完整文本）
            if e.type == 'ORG':
                if e.text in ORG_TEXT_BLACKLIST or e.text in ORG_PREFIX_BLACKLIST:
                    continue

            filtered.append(e)

        return filtered

    def _detect_western_locations(self, tokens: List[str], pos_tags: List[str],
                                  covered: set) -> List[Entity]:
        """检测西方奇幻风格的地名（如'灰石哨站'）。

        规则：
        - HanLP 已识别为 LOC 的实体直接保留
        - WESTERN_LOC_PREFIXES + LOC_SUFFIXES 组合（支持跨token拼接）
        - 使用 raw_text 层面的正则匹配，处理 HanLP 分词过细的情况
        """
        entities: List[Entity] = []
        i = 0

        # 首先收集所有 HanLP 已识别的 LOC
        while i < len(tokens):
            if i in covered:
                i += 1
                continue

            token = tokens[i]
            pos = pos_tags[i] if i < len(pos_tags) else 'X'

            # HanLP 已识别为 LOC 的保留
            if pos in ('NS', 'LOC', 'GPE'):
                entities.append(Entity(
                    text=token, type='LOC', start=i, end=i + 1,
                    confidence=0.9,
                ))
                covered.add(i)
                i += 1
                continue

            i += 1

        # 第二轮：在raw_text层面用正则匹配西方地名模式
        # 构建: (灰石|白银|暗影|...) + (哨站|要塞|堡垒|营地|城|镇|...)
        prefix_pattern = '|'.join(sorted(WESTERN_LOC_PREFIXES, key=len, reverse=True))
        suffix_pattern = '|'.join(sorted(LOCATION_SUFFIXES, key=len, reverse=True))
        # 匹配: 前缀(可能由多个单字token组成) + 后缀
        # 允许前缀和后缀之间无分隔符（HanLP分词场景）
        loc_regex = re.compile(
            f'(?:{prefix_pattern})'
            f'(?:{suffix_pattern})'
        )

        # 构建token位置映射
        full_text = ''.join(tokens)
        token_positions = []
        pos = 0
        for tok in tokens:
            token_positions.append((pos, pos + len(tok)))
            pos += len(tok)

        for match in loc_regex.finditer(full_text):
            match_start = match.start()
            match_end = match.end()
            matched_text = match.group()

            # 跳过太短的匹配（< 3字）
            if len(matched_text) < 3:
                continue

            # 找到对应的token范围
            start_token = None
            end_token = None
            for idx, (tok_start, tok_end) in enumerate(token_positions):
                if tok_start <= match_start < tok_end:
                    start_token = idx
                if tok_start < match_end <= tok_end:
                    end_token = idx
                    break

            if start_token is not None and end_token is not None:
                # 检查是否已被覆盖
                if not any(idx in covered for idx in range(start_token, end_token + 1)):
                    entities.append(Entity(
                        text=matched_text, type='LOC', start=start_token, end=end_token + 1,
                        confidence=0.85,
                    ))
                    for idx in range(start_token, end_token + 1):
                        covered.add(idx)

        return entities

    def _merge_foreign_names(self, tokens: List[str], pos_tags: List[str]) -> Tuple[List[Entity], set, set]:
        """合并西方名字（如 "亚瑟·潘德拉贡"）。

        改进：
        1. 支持 "名·中间名·姓" 格式（如 "亚瑟·潘德拉贡"）
        2. 支持缩写格式 "A·P·潘德拉贡"
        3. 支持以西方名字前缀开头的独立NR词
        4. 优化边界检测，避免跨句子合并

        Returns:
            (entities, covered_indices, entity_texts) 三元组
        """
        entities: List[Entity] = []
        covered: set = set()
        texts: set = set()

        i = 0
        while i < len(tokens):
            pos = pos_tags[i] if i < len(pos_tags) else 'X'
            if pos not in ('NR', 'nr') and tokens[i] not in WESTERN_NAME_PREFIXES:
                i += 1
                continue

            start = i
            parts = [tokens[i]]
            separators = []
            j = i + 1

            while j < len(tokens):
                next_pos = pos_tags[j] if j < len(pos_tags) else 'X'
                next_token = tokens[j]

                if next_pos in ('NR', 'nr'):
                    parts.append(next_token)
                    j += 1
                elif next_token in ('·', '-', '.', '/') and j + 1 < len(tokens):
                    check_pos = pos_tags[j + 1] if j + 1 < len(pos_tags) else 'X'
                    if check_pos in ('NR', 'nr'):
                        separators.append((len(parts) - 1, next_token))
                        j += 1
                    else:
                        break
                elif next_token in WESTERN_NAME_PREFIXES:
                    # 连续出现的西方名字（无分隔符，如 "艾德温 伊莉雅"）
                    parts.append(next_token)
                    j += 1
                elif next_token in ('和', '与', '及'):
                    # "艾德温和伊莉雅" - 名字连接词
                    if j + 1 < len(tokens):
                        check_pos = pos_tags[j + 1] if j + 1 < len(pos_tags) else 'X'
                        check_token = tokens[j + 1]
                        if check_pos in ('NR', 'nr') or check_token in WESTERN_NAME_PREFIXES:
                            j += 1  # 跳过连接词
                            continue
                    break
                else:
                    break

            if len(parts) > 1:
                merged_parts = []
                for idx, part in enumerate(parts):
                    merged_parts.append(part)
                    for sep_idx, sep_char in separators:
                        if sep_idx == idx:
                            merged_parts.append(sep_char)
                merged = ''.join(merged_parts)

                entities.append(Entity(
                    text=merged, type='PER', start=start, end=j
                ))
                texts.add(merged)
                for idx in range(start, j):
                    covered.add(idx)
                i = j
                continue

            i += 1

        return entities, covered, texts

    def _detect_prefix_titles(self, tokens: List[str], pos_tags: List[str],
                              covered: set) -> List[Entity]:
        """检测前缀称呼（老陈/小李/大张），其中 X 必须是姓氏。"""
        entities: List[Entity] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in PREFIX_TITLES and i + 1 < len(tokens) and i not in covered:
                next_token = tokens[i + 1]
                next_pos = pos_tags[i + 1] if i + 1 < len(pos_tags) else 'X'

                if next_token in SINGLE_CHAR_SURNAMES and next_pos in ('NR', 'nr'):
                    combined = token + next_token
                    entities.append(Entity(
                        text=combined, type='PER', start=i, end=i + 2, confidence=0.90
                    ))
                    i += 2
                    continue
            i += 1
        return entities

    def _detect_profession_titles(self, tokens: List[str], pos_tags: List[str],
                                  covered: set) -> List[Entity]:
        """检测独立的职业称呼（博士/教授/医生等）。"""
        entities: List[Entity] = []
        for i, token in enumerate(tokens):
            if i not in covered and token in PROFESSION_TITLES:
                entities.append(Entity(
                    text=token, type='PER', start=i, end=i + 1, confidence=0.85
                ))
        return entities

    def _detect_org_suffixes(self, tokens: List[str], pos_tags: List[str],
                             covered: set) -> List[Entity]:
        """检测组织后缀（暗影会/异能者联盟），仅匹配2字符以上前缀。

        增加 ORG_PREFIX_BLACKLIST 过滤，避免'炎魔会'/'我们会'/'立即组织'等误识别。
        """
        entities: List[Entity] = []
        i = 0
        while i < len(tokens):
            if i not in covered and i + 1 < len(tokens) and (i + 1) not in covered:
                next_token = tokens[i + 1]
                if next_token in ORG_SUFFIXES and len(tokens[i]) >= 2:
                    # 黑名单检查：前缀词不在黑名单中
                    if tokens[i] not in ORG_PREFIX_BLACKLIST:
                        combined = tokens[i] + next_token
                        entities.append(Entity(
                            text=combined, type='ORG', start=i, end=i + 2, confidence=0.85
                        ))
                        i += 2
                        continue
            i += 1
        return entities

    def _detect_surname_based_entities(self, tokens: List[str], pos_tags: List[str],
                                       covered: set) -> List[Entity]:
        """基于姓氏的实体检测：
        - Rule 2: 单姓 + 称呼词（陈管家/林少爷/李医生）
        - Rule 3: 单姓 + 职位后缀（张总/李哥/王姐）
        
        注意：Rule 6（家族后缀→ORG）和 Rule 7（位置后缀→LOC）已移除。
        因策略调整为只识别说话角色，ORG/LOC 实体会被 SpeakerRoleFilter 丢弃。
        FAMILY_SUFFIXES 和 LOCATION_SUFFIXES 保留为向后兼容，不再用于实体创建。
        （参见 2026-05-02 修正方案）
        
        2026-05-02 修复：增加动词检查，防止"赵虎嗤"类错误。
        当HanLP将"赵虎嗤笑道"切分为 [赵虎/nr, 嗤/v, 笑道/v] 时，
        原规则会将"赵"(单姓) + "嗤"(动词) 组合成错误实体"赵嗤"。
        现在会检查下一个token的词性，如果是动词则跳过。
        """
        # 动词词性集合（HanLP词性标签）
        VERB_POS = {'V', 'VE', 'VC', 'VV', 'VW', 'VD', 'VL', 'VH', 'VO', 'VP', 'VB', 'v'}
        
        entities: List[Entity] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            pos = pos_tags[i] if i < len(pos_tags) else 'X'

            # 跳过已覆盖或非姓氏标记
            # 修复：确保token是单字姓氏（len(token) == 1）
            if pos not in ('NR', 'nr') or len(token) != 1 or token not in SINGLE_CHAR_SURNAMES:
                i += 1
                continue

            if i + 1 >= len(tokens) or (i + 1) in covered:
                i += 1
                continue

            next_token = tokens[i + 1]
            next_pos = pos_tags[i + 1] if i + 1 < len(pos_tags) else 'X'
            
            # 2026-05-02 修复：检查下一个token是否是动词
            # 防止"赵虎/nr 嗤/v 笑道/v" → "赵嗤"类错误
            if next_pos.upper() in VERB_POS:
                i += 1
                continue
            
            combined = token + next_token

            if next_token in TITLE_WORDS:
                entities.append(Entity(
                    text=combined, type='PER', start=i, end=i + 2, confidence=0.95
                ))
                i += 2
            elif next_token in POSITION_SUFFIXES:
                entities.append(Entity(
                    text=combined, type='PER', start=i, end=i + 2, confidence=0.90
                ))
                i += 2
            else:
                # ORG/LOC创建逻辑已移除（2026-05-02 修正方案）
                # 不再创建 FAMILY_SUFFIXES → ORG 和 LOCATION_SUFFIXES → LOC 实体
                i += 1
                continue

        return entities

    def _merge_rule_results(self, rule_entities: List[Entity], covered: set,
                            texts: set, new_entities: List[Entity]) -> None:
        """将子规则产生的实体合并到主结果中，并更新覆盖集合。"""
        for e in new_entities:
            for idx in range(e.start, e.end):
                covered.add(idx)
            rule_entities.append(e)
            texts.add(e.text)

    def _combine_entities(self, rule_entities: List[Entity], rule_entity_texts: set,
                          rule_covered_indices: set, base_entities: List[Entity]) -> List[Entity]:
        """合并规则实体和基础实体，过滤重复和冲突。"""
        enhanced = list(rule_entities)
        entity_texts = set(rule_entity_texts)

        for e in base_entities:
            skip = False
            for idx in range(e.start, e.end):
                if idx in rule_covered_indices:
                    skip = True
                    break

            if not skip and e.text not in entity_texts:
                enhanced.append(e)
                entity_texts.add(e.text)

        # Filter out chapter title entities
        enhanced = filter_chapter_title_entities(enhanced)

        return enhanced

    def _analyze_simple(self, text: str, sentences: List[str]) -> NLPResult:
        import jieba
        import jieba.posseg as pseg
        
        all_tokens = []
        all_pos_tags = []
        
        for sent in sentences:
            if not sent.strip():
                continue
            words = pseg.cut(sent)
            for word, pos in words:
                if word.strip():
                    all_tokens.append(Token(text=word, pos=pos))
                    all_pos_tags.append((word, pos))
        
        entities = self._extract_entities_from_pos(all_tokens)
        
        # Filter out chapter title entities
        entities = filter_chapter_title_entities(entities)
        
        return NLPResult(
            tokens=all_tokens,
            entities=entities,
            sentences=sentences,
            pos_tags=all_pos_tags,
            raw_text=text
        )

    def _split_sentences(self, text: str) -> List[str]:
        pattern = r'(?<=[。！？；\n])'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_entities_from_pos(self, tokens: List[Token]) -> List[Entity]:
        pos_to_entity = {
            'NR': 'PER',
            'NS': 'LOC',
            'NT': 'ORG',
            'nr': 'PER',
            'ns': 'LOC',
            'nt': 'ORG',
        }
        
        entities = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            entity_type = pos_to_entity.get(token.pos)
            
            if entity_type:
                entity_text = token.text
                start = i
                i += 1
                
                while i < len(tokens) and pos_to_entity.get(tokens[i].pos) == entity_type:
                    entity_text += tokens[i].text
                    i += 1
                
                # ORG/LOC处理移除（2026-05-02 修正方案）
                # 只保留PER类型实体
                if entity_type == 'PER':
                    entities.append(Entity(text=entity_text, type=entity_type, start=start, end=i))
            else:
                i += 1
        
        # 2026-05-02 修复：过滤HanLP/jieba误识别的虚假人名
        # "萧炎冷笑道" → HanLP识别为"萧炎冷"(人名)
        # 过滤以常见表情/动作字结尾的人名实体
        entities = self._filter_false_persons(entities)
        
        return entities
    
    def _filter_false_persons(self, entities: List[Entity]) -> List[Entity]:
        """过滤HanLP误识别的虚假人名实体。

        过滤规则：
        1. 单字实体不可能是有效人名（排除）
        2. 包含"家/族/宗/门/派/帮/教/会"等组织词的实体应归类为ORG
        3. 包含常见非人名词（"天道"、"大道"、"世界"、"空间"等）的应排除
        4. 长度>=4且包含"之/的/与/和"的短语不是人名

        注意：主要的误合并检测（如"萧炎冷"→"萧炎"+"冷"）
        现在由ContextDiversityValidator的_detect_mis_merged_entities处理。
        此方法仅处理单句层面的简单过滤。
        """
        # 组织特征词：包含这些词的应归类为 ORG
        org_patterns = [
            '家', '族', '宗', '门', '派', '帮', '教', '会', '阁', '殿', '府',
            '宫', '堡', '寨', '岛', '城', '国', '界', '域', '天'
        ]
        # 常见非人名词（网文高频但非人名）
        false_person_words = [
            '天道', '大道', '世界', '空间', '时间', '天地', '万物', '虚空',
            '宇宙', '星辰', '天命', '命运', '轮回', '因果', '境界', '修炼',
            '灵力', '灵力', '灵气', '真气', '斗气', '魂力', '元力', '法力',
            '神识', '意识', '灵魂', '魂魄', '肉身', '血脉', '功法', '武技',
            '剑意', '剑道', '阵法', '丹药', '灵药', '法宝', '神器', '兵器',
            '飞舟', '马车', '山洞', '树林', '草原', '沙漠', '河流', '瀑布'
        ]
        # 长度阈值：过长不是人名
        max_person_len = 7

        filtered = []
        for ent in entities:
            name = ent.text
            ent_type = ent.type
            name_len = len(name)

            # 规则1：单字实体不可能是有效人名
            if name_len < 2:
                continue

            # 规则2：包含组织特征词的归类为 ORG
            if ent_type == 'PER' and any(pat in name for pat in org_patterns):
                ent.type = 'ORG'
                filtered.append(ent)
                continue

            # 规则3：常见非人名词直接过滤
            if name in false_person_words:
                continue

            # 规则4：长度超限过滤
            if name_len > max_person_len:
                # 检查是否包含连接词
                if any(conn in name for conn in ['之', '的', '与', '和', '而', '但']):
                    continue

            # 规则5：纯数字或字母+数字不是人名
            if name.isdigit():
                continue
            if name.replace('·', '').isalpha() and '·' not in name and name_len < 3:
                # 可能是单字英文名，排除
                continue

            filtered.append(ent)

        return filtered

    def tokenize(self, text: str) -> List[str]:
        result = self.analyze(text)
        return [t.text for t in result.tokens]

    def pos_tag(self, text: str) -> List[Tuple[str, str]]:
        result = self.analyze(text)
        return result.pos_tags

    def get_entities(self, text: str) -> List[Entity]:
        result = self.analyze(text)
        return result.entities

    def get_persons(self, text: str) -> List[str]:
        entities = self.get_entities(text)
        return [e.text for e in entities if e.type in ('PER', 'PERSON', 'NR')]

    def get_locations(self, text: str) -> List[str]:
        entities = self.get_entities(text)
        return [e.text for e in entities if e.type in ('LOC', 'LOCATION', 'NS', 'GPE')]

    def get_organizations(self, text: str) -> List[str]:
        entities = self.get_entities(text)
        return [e.text for e in entities if e.type in ('ORG', 'ORGANIZATION', 'NT')]


_nlp_instance: Optional[NLPBasics] = None
_nlp_lock = threading.Lock()


def get_nlp(enable_foreign_name_merge: bool = True) -> NLPBasics:
    """获取或创建全局 NLP 实例（线程安全，双重检查锁）"""
    global _nlp_instance
    if _nlp_instance is None:
        with _nlp_lock:
            if _nlp_instance is None:
                _nlp_instance = NLPBasics(enable_foreign_name_merge=enable_foreign_name_merge)
    return _nlp_instance


def reset_nlp() -> None:
    """重置全局 NLP 实例，用于测试或重新初始化"""
    global _nlp_instance
    with _nlp_lock:
        _nlp_instance = None


def analyze(text: str) -> NLPResult:
    return get_nlp().analyze(text)


def tokenize(text: str) -> List[str]:
    return get_nlp().tokenize(text)


def pos_tag(text: str) -> List[Tuple[str, str]]:
    return get_nlp().pos_tag(text)


def get_entities(text: str) -> List[Entity]:
    return get_nlp().get_entities(text)


def get_persons(text: str) -> List[str]:
    return get_nlp().get_persons(text)


def get_locations(text: str) -> List[str]:
    return get_nlp().get_locations(text)


def get_organizations(text: str) -> List[str]:
    return get_nlp().get_organizations(text)


def is_chapter_title_pattern(text: str) -> bool:
    """Check if text matches chapter title patterns.

    Args:
        text: Text to check.

    Returns:
        True if text matches chapter title patterns, False otherwise.

    Examples:
        >>> is_chapter_title_pattern("第一章")
        True
        >>> is_chapter_title_pattern("卷一")
        True
        >>> is_chapter_title_pattern("林轩")
        False
    """
    return any(pattern.match(text) for pattern in CHAPTER_TITLE_PATTERNS)


def filter_chapter_title_entities(
    entities: List[Entity],
    chapters: Optional[List] = None,
    raw_text: Optional[str] = None,
) -> List[Entity]:
    """Filter out entities that are chapter titles.

    Removes entities that match chapter title patterns (e.g., "第一章", "卷一")
    while preserving normal entities in the body text.

    Args:
        entities: List of entities to filter.
        chapters: Optional list of Chapter objects for position-based filtering.
        raw_text: Optional raw text for title position matching.

    Returns:
        Filtered list of entities with chapter title entities removed.

    Examples:
        >>> from pipeline.nlp_basics import Entity, Chapter
        >>> entities = [
        ...     Entity(text="第一章", type="LOC", start=0, end=3),
        ...     Entity(text="林轩", type="PER", start=10, end=12),
        ... ]
        >>> filtered = filter_chapter_title_entities(entities)
        >>> [e.text for e in filtered]
        ['林轩']
    """
    if not entities:
        return []

    # Build a set of chapter title strings for quick lookup
    chapter_title_texts = set()
    chapter_title_positions = []  # (start_pos, end_pos) tuples

    if chapters:
        for chapter in chapters:
            if hasattr(chapter, 'title'):
                chapter_title_texts.add(chapter.title)
            if hasattr(chapter, 'start_pos') and hasattr(chapter, 'end_pos'):
                chapter_title_positions.append(
                    (chapter.start_pos, chapter.end_pos)
                )

    filtered = []
    for entity in entities:
        # Check if entity text matches chapter title patterns
        if is_chapter_title_pattern(entity.text):
            logger.debug(f"过滤章节标题实体: {entity.text} ({entity.type})")
            continue

        # Check if entity text matches known chapter titles
        if entity.text in chapter_title_texts:
            logger.debug(f"过滤已知章节标题: {entity.text}")
            continue

        # Check if entity is within a chapter title position range
        # Chapter titles are typically at the start_pos of each chapter
        in_title_range = False
        if chapters:
            for chapter in chapters:
                if hasattr(chapter, 'title') and hasattr(chapter, 'start_pos'):
                    # Check if entity position overlaps with chapter title
                    title_start = chapter.start_pos
                    title_end = title_start + len(chapter.title)
                    if entity.start >= title_start and entity.end <= title_end:
                        in_title_range = True
                        break

        if in_title_range:
            logger.debug(f"过滤章节标题范围内的实体: {entity.text}")
            continue

        filtered.append(entity)

    return filtered
