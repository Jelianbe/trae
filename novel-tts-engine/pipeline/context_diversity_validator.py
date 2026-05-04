# -*- coding: utf-8 -*-
"""
ContextDiversityValidator - 上下文多样性实体验证器

对NER实体列表进行二次过滤，自动调整置信度：
- 过滤掉"固定搭配中的高频片段"（如"青龙帮"中的"青龙"）
- 保留"多种上下文中出现的真实实体"（如"林轩"、"艾德温"）
- 降低低频噪声实体的置信度

通用实体统计发现（2026-05-02）：
- 新增上下文边界词命中率统计
- 新增构词法后缀自动发现
- 新增多维度综合打分框架
"""
from typing import List, Dict, Set, Optional, Tuple
import re
import threading
import logging
from collections import defaultdict, Counter

from pipeline.nlp_basics import Entity

logger = logging.getLogger(__name__)


class ContextDiversityValidator:
    """
    基于上下文多样性的实体验证器
    
    核心判定逻辑：
    - 总出现次数 < 3 → 降为低置信度（0.3），疑似噪声
    - 总出现次数 ≥ 3，右邻字种类 ≤ 1 → 极可能为固定搭配片段，降为极低置信度（0.2）
    - 总出现次数 ≥ 3，右邻字种类 ≥ 2 → 维持原置信度
    - 总出现次数 ≥ 5，右邻字种类 ≥ 3，且章节分布 ≥ 2 → 提升为高置信度（最低0.8）
    
    FO-07 共现统计增强：
    - 统计每个实体与其他实体在同一段落中的共现关系
    - 共现多样性高（与多种不同实体组合出现）→ 提升置信度
    - 共现对象为高置信度实体（白名单/高频实体）→ 额外加分
    """
    
    BOUNDARY_PATTERNS = [
        re.compile(r'(?P<name>.{1,4})说道'),
        re.compile(r'(?P<name>.{1,4})问道'),
        re.compile(r'(?P<name>.{1,4})喊道'),
        re.compile(r'(?P<name>.{1,4})笑道'),
        re.compile(r'(?P<name>.{1,4})淡淡道'),
        re.compile(r'(?P<name>.{1,4})沉声道'),
        re.compile(r'(?P<name>.{1,4})冷声道'),
        re.compile(r'(?P<name>.{1,4})轻声道'),
        re.compile(r'(?P<name>.{1,4})低声道'),
        re.compile(r'(?P<name>.{1,4})道'),
        re.compile(r'(?P<name>.{1,4})来到'),
        re.compile(r'(?P<name>.{1,4})走出'),
        re.compile(r'(?P<name>.{1,4})看着'),
        re.compile(r'(?P<name>.{1,4})点了点头'),
        re.compile(r'(?P<name>.{1,4})摇头'),
        re.compile(r'(?P<name>.{1,4})皱眉'),
        re.compile(r'(?P<name>.{1,4})转身'),
        re.compile(r'(?P<name>.{1,4})站起'),
        re.compile(r'(?P<name>.{1,4})坐下'),
        re.compile(r'(?P<name>.{1,4})的[^\s]'),
        re.compile(r'(?P<name>.{1,4})师兄'),
        re.compile(r'(?P<name>.{1,4})师姐'),
        re.compile(r'(?P<name>.{1,4})前辈'),
        re.compile(r'(?P<name>.{1,4})大人'),
        re.compile(r'(?P<name>.{1,4})长老'),
        re.compile(r'(?P<name>.{1,4})老师'),
    ]
    
    POSTFIX_PATTERNS_CANDIDATES = [
        '尊', '皇', '帝', '主', '者', '王', '侯', '公', '伯', '将',
        '尊者', '道人', '圣人', '之主', '大帝', '天尊', '真人',
        '先生', '女士', '公子', '少爷', '姑娘', '小姐',
        '前辈', '后辈', '长老', '宗主', '峰主', '岛主',
    ]
    
    def __init__(
        self,
        min_occurrences: int = 3,
        high_conf_threshold: int = 5,
        diversity_threshold: int = 2,
        whitelist: Optional[Set[str]] = None,
        mode: str = 'general',
    ):
        self.mode = mode
        
        if mode == 'speaker_role':
            self.min_occurrences = 2
            self.high_conf_threshold = 3
        else:
            self.min_occurrences = min_occurrences
            self.high_conf_threshold = high_conf_threshold
        
        self.diversity_threshold = diversity_threshold
        self.whitelist = whitelist or set()
    
    def validate(
        self,
        entities: List[Entity],
        full_text: str,
        chapters: Optional[List[Dict]] = None,
    ) -> List[Entity]:
        """
        主入口：对实体列表进行上下文多样性验证，返回调整后的实体列表
        
        Args:
            entities: 原始实体列表（来自nlp_basics）
            full_text: 完整文本
            chapters: 章节信息列表（可选），用于计算章节分布
            
        Returns:
            调整置信度后的实体列表
        """
        # 通用实体统计发现：P0 - 提前发现"字A+字B"组合模式（2026-05-02）
        # 让发现的候选实体也经过完整的统计验证流程，而不是最后直接追加
        discovered = self.discover_compound_entities(full_text, entities)
        all_entities = entities + discovered
        
        # 步骤1：为每个唯一实体文本收集上下文统计 + 共现统计
        stats = self._collect_context_stats(all_entities, full_text, chapters)
        
        # 步骤1.5：误合并检测（2026-05-03 新增）
        # 在统计验证后，对长度≥3的实体进行误合并检测
        # 检测逻辑：如果实体去掉末端1-2字后是一个高频已知角色名，且末端是常见动词后缀
        # 则将置信度降为极低（0.1）
        mis_merged_entities = self._detect_mis_merged_entities(all_entities, stats, full_text)
        for entity_text in mis_merged_entities:
            if entity_text in stats:
                # 找到该实体的所有实例并降低置信度
                for entity in all_entities:
                    if entity.text == entity_text:
                        entity.confidence = 0.1
                        logger.debug(f"误合并检测: {entity_text} → confidence=0.1")
        
        # 步骤2：根据多样性 + 共现统计调整置信度
        validated = []
        for entity in all_entities:
            key = entity.text
            if key in stats:
                # 如果已经被误合并检测标记为低置信度，保持0.1
                if entity.confidence <= 0.1:
                    continue  # 过滤掉误合并实体
                new_conf = self._calculate_confidence(entity, stats[key])
                entity.confidence = new_conf
            validated.append(entity)
        
        return validated
    
    def _detect_mis_merged_entities(
        self,
        entities: List[Entity],
        stats: Dict[str, Dict],
        full_text: str,
    ) -> set:
        """
        基于统计的结构压缩率检测，替代硬编码后缀黑名单（2026-05-03 v2.2）。
        
        核心逻辑：
        对于每个类型为PER且长度≥3的实体A，检查是否存在一个更短的实体B
        （B是A的前缀，且B是高频角色名），满足：
          - A的出现次数 ≤ 2（极低频）
          - A的出现次数 < B出现次数的10%
          - A的右邻字中，至少50%是对话引导词（道、说、问、喊、叫、喝、笑等）
        
        如果满足，则A是B的误合并扩展，标记为mis_merged。
        
        优势：
        - 零硬编码：不依赖SINGLE_CHAR_VERBS等词表
        - 全覆盖：能检测"萧炎冷"、"萧炎承"、"萧炎承喏"等任意后缀
        - 低误杀：真实人名（如"纳兰肃"）的右邻字不是对话引导词，不会被误杀
        
        v2.2修复：
        - 使用对话引导词检测替代右邻字多样性阈值
        - 萧炎冷(右邻字=3，但100%是对话词) → 误合并 ✓
        - 纳兰肃(右邻字=2，但0%是对话词) → 保留 ✓
        """
        # 对话引导词集合（用于检测误合并）
        DIALOGUE_WORDS = {
            '道', '说', '问', '喊', '叫', '喝', '笑', '叹', '答', '应',
            '吼', '骂', '泣', '怒', '冷', '斥', '责', '嘲', '讽', '讥',
        }
        
        # 找出出现≥5次的高频角色名（作为prefix候选）
        known_persons = set()
        for entity_text, stat in stats.items():
            if stat['occurrences'] >= 5:
                known_persons.add(entity_text)
        
        mis_merged = set()
        
        for entity in entities:
            if entity.type != 'PER' or len(entity.text) < 3:
                continue
            
            entity_text = entity.text
            entity_occ = stats.get(entity_text, {}).get('occurrences', 0)
            entity_neighbors = stats.get(entity_text, {}).get('right_neighbors', set())
            
            # 条件0：实体必须是极低频（≤2次）
            if entity_occ > 2:
                continue
            
            # 检查所有可能的prefix（去掉末端1-2字）
            for suffix_len in [1, 2]:
                if len(entity_text) <= suffix_len:
                    continue
                
                prefix = entity_text[:-suffix_len]
                
                # 条件1：prefix是已知的高频角色
                if prefix not in known_persons:
                    continue
                
                prefix_occ = stats[prefix]['occurrences']
                
                # 条件2：实体出现次数远少于prefix（<10%）
                if entity_occ >= prefix_occ * 0.1:
                    continue
                
                # 边界条件：无右邻字无法判断是否误合并，跳过
                if len(entity_neighbors) == 0:
                    continue
                
                # 条件3：实体的右邻字中，至少50%是对话引导词
                dialogue_ratio = len(entity_neighbors & DIALOGUE_WORDS) / len(entity_neighbors)
                if dialogue_ratio < 0.5:
                    continue
                
                # 满足所有条件 → 标记为误合并
                mis_merged.add(entity_text)
                
                logger.debug(
                    f"[结构压缩率检测] {entity_text} → "
                    f"prefix='{prefix}'({prefix_occ}次) + "
                    f"suffix='{entity_text[-suffix_len:]}' | "
                    f"entity_occ={entity_occ}, dialogue_ratio={dialogue_ratio:.0%}"
                )
                break
        
        return mis_merged
    
    def _collect_context_stats(
        self,
        entities: List[Entity],
        full_text: str,
        chapters: Optional[List[Dict]] = None,
    ) -> Dict[str, Dict]:
        """
        收集每个实体文本的出现次数、右邻字集合、所在章节（如有）+ FO-07 共现统计

        性能优化：只对唯一实体文本进行全文扫描，避免重复搜索。
        使用 re.finditer 一次匹配所有位置。
        """
        # 获取唯一实体文本
        unique_texts = set(e.text for e in entities)

        stats = {}
        for text in unique_texts:
            stats[text] = {
                'occurrences': 0,
                'right_neighbors': set(),
                'chapter_ids': set(),
                # FO-07: 共现统计
                'co_occurrence': defaultdict(int),  # 共现实体 -> 次数
                'co_occurrence_diversity': 0,       # 共现实体种类数
                'high_conf_co_occurrence': 0,       # 与高置信度实体共现次数
                # 通用实体统计发现：新增维度（2026-05-02）
                'boundary_hits': defaultdict(int),  # 边界词模板 -> 命中次数
                'boundary_hit_templates': 0,        # 命中的不同边界模板种类数
                'boundary_hit_total': 0,            # 总边界词命中次数
                'name_suffix': None,                # 发现的名称后缀（如"尊者"、"之主"）
                'has_name_suffix': False,           # 是否具有已知名称后缀
            }

        # 预构建章节位置索引，避免每次 O(N*M) 循环
        chapter_ranges = []
        if chapters:
            for chapter_idx, chapter in enumerate(chapters):
                chapter_ranges.append(
                    (chapter.get('start', 0), chapter.get('end', len(full_text)), chapter_idx)
                )

        # 预编译标点集合，加速右邻字判断
        punctuation_set = frozenset('，。！？；：""''（）【】《》\n\r\t ')

        # FO-07: 预构建每个实体的位置索引，用于共现检测
        entity_positions: Dict[str, List[Tuple[int, int]]] = {}
        for text in unique_texts:
            pattern = re.compile(re.escape(text))
            positions = []
            for match in pattern.finditer(full_text):
                positions.append((match.start(), match.end()))
            entity_positions[text] = positions
            stats[text]['occurrences'] = len(positions)

            # 获取右邻字
            for start, end in positions:
                neighbors = self._get_right_neighbors_fast(full_text, end, punctuation_set)
                stats[text]['right_neighbors'].update(neighbors)

            # 计算章节分布
            if chapters and positions:
                for pos_start, _ in positions:
                    chapter_idx = self._find_chapter_index(pos_start, chapter_ranges)
                    if chapter_idx is not None:
                        stats[text]['chapter_ids'].add(chapter_idx)

        # FO-07: 计算共现统计（基于段落级别）
        self._compute_co_occurrence(stats, entity_positions, full_text)

        # 通用实体统计发现：计算边界词命中率（2026-05-02）
        self._compute_boundary_hits(stats, entity_positions, full_text)

        # 通用实体统计发现：发现名称后缀（2026-05-02）
        self._discover_name_suffixes(stats, entity_positions, full_text)

        return stats

    def _compute_co_occurrence(
        self,
        stats: Dict[str, Dict],
        entity_positions: Dict[str, List[Tuple[int, int]]],
        full_text: str,
    ) -> None:
        """
        FO-07: 计算实体间的共现统计

        以段落为单位，统计哪些实体出现在同一段落中。
        共现多样性高的实体更有可能是真实实体。
        """
        # 按段落分割文本
        paragraphs = []
        para_start = 0
        for i, char in enumerate(full_text):
            if char == '\n' and (i + 1 >= len(full_text) or full_text[i + 1] == '\n'):
                paragraphs.append((para_start, i))
                para_start = i + 1
                while para_start < len(full_text) and full_text[para_start] == '\n':
                    para_start += 1
        if para_start < len(full_text):
            paragraphs.append((para_start, len(full_text)))

        # 对每个段落，找出其中出现的所有实体
        for para_start, para_end in paragraphs:
            para_text = full_text[para_start:para_end]
            if len(para_text.strip()) < 10:
                continue

            # 找出该段落中出现的所有实体
            entities_in_para = []
            for entity_text, positions in entity_positions.items():
                for pos_start, pos_end in positions:
                    if para_start <= pos_start < para_end:
                        entities_in_para.append(entity_text)
                        break

            # 更新共现统计
            seen = set()
            for entity in entities_in_para:
                if entity in seen:
                    continue
                seen.add(entity)

            entity_list = list(seen)
            for i, entity_a in enumerate(entity_list):
                for entity_b in entity_list[i + 1:]:
                    stats[entity_a]['co_occurrence'][entity_b] += 1
                    stats[entity_b]['co_occurrence'][entity_a] += 1

        # 计算共现多样性
        whitelist = self.whitelist
        for entity_text, stat in stats.items():
            stat['co_occurrence_diversity'] = len(stat['co_occurrence'])
            # 计算与高置信度实体（白名单或高频）共现的次数
            high_conf_count = 0
            for co_entity, count in stat['co_occurrence'].items():
                if co_entity in whitelist or stats[co_entity]['occurrences'] >= self.high_conf_threshold:
                    high_conf_count += count
            stat['high_conf_co_occurrence'] = high_conf_count

    def _compute_boundary_hits(
        self,
        stats: Dict[str, Dict],
        entity_positions: Dict[str, List[Tuple[int, int]]],
        full_text: str,
    ) -> None:
        """
        通用实体统计发现：计算每个实体在边界词模板中的命中情况（2026-05-02）
        
        真实的说话角色名字，在全文范围内会反复出现在固定的"边界模板"中。
        统计每个候选实体出现在这些边界词模板中的命中次数。
        """
        for entity_text, positions in entity_positions.items():
            for pos_start, pos_end in positions:
                # 获取实体周围的上下文（前后各50字符）
                context_start = max(0, pos_start - 50)
                context_end = min(len(full_text), pos_end + 50)
                context = full_text[context_start:context_end]
                
                # 检查是否命中任何边界词模板
                for pattern in self.BOUNDARY_PATTERNS:
                    for match in pattern.finditer(context):
                        matched_name = match.group('name')
                        # 如果匹配的名称包含或等于当前实体，则计为一次命中
                        if entity_text in matched_name or matched_name in entity_text:
                            template_key = pattern.pattern[:30]  # 用正则前缀作为模板标识
                            stats[entity_text]['boundary_hits'][template_key] += 1
                            stats[entity_text]['boundary_hit_total'] += 1
            
            # 计算命中的不同边界模板种类数
            stats[entity_text]['boundary_hit_templates'] = len(
                [k for k, v in stats[entity_text]['boundary_hits'].items() if v > 0]
            )

    def discover_boundary_entities(
        self,
        full_text: str,
        existing_entities: List[Entity],
    ) -> List[Entity]:
        """
        通用实体统计发现：从边界词匹配中主动发现新实体（2026-05-02）
        
        扫描全文，使用边界词模板发现可能的人名实体。
        如果发现的实体不在现有实体列表中，且满足出现频率要求，
        则创建新的PER实体加入列表。
        
        使用HanLP分词来智能提取人名，而不是简单地往前取固定字符。
        
        Returns:
            新发现的实体列表
        """
        # 收集现有实体文本
        existing_texts = set(e.text for e in existing_entities)
        
        # 边界词列表（只保留词，不需要捕获组）
        BOUNDARY_WORDS = [
            '说道', '问道', '喊道', '笑道', '淡淡道', '沉声道', '冷声道',
            '轻声道', '低声道', '道', '来到', '走出', '看着',
            '点了点头', '摇了摇头', '皱眉', '转身', '站起', '坐下',
            '师兄', '师姐', '前辈', '大人', '长老', '老师',
        ]
        
        # 使用HanLP分词来智能提取人名
        try:
            import hanlp
            # 延迟导入，避免无HanLP环境报错
            from pipeline.nlp_basics import get_nlp
            nlp = get_nlp()
            # 对全文分词
            tokens = nlp.segment(full_text)
        except Exception:
            # HanLP不可用，返回空列表
            return []
        
        # 统计边界词前的潜在人名
        candidate_counter = Counter()
        candidate_positions = defaultdict(list)
        
        # 构建token位置映射
        token_texts = [t for t in tokens]
        
        for word in BOUNDARY_WORDS:
            # 在token列表中查找边界词位置
            start_idx = 0
            while True:
                # 查找边界词在token列表中的位置
                try:
                    idx = token_texts.index(word, start_idx)
                except ValueError:
                    break
                
                # 检查边界词前面的token是否是人名
                # 往前检查1-2个token
                for lookback in [1, 2]:
                    if idx - lookback >= 0:
                        candidate = token_texts[idx - lookback]
                        # 只考虑2-4个字符的候选
                        if 2 <= len(candidate) <= 4:
                            # 跳过常见非人名词
                            skip_words = {'他的', '她的', '我的', '你的', '我们', '他们', '这个', '那个',
                                         '一个', '一些', '一种', '一切', '所有', '这种', '这样', '这里',
                                         '自己', '自己', '自己', '什么', '怎么', '为什么', '哪里', '哪里'}
                            if candidate not in skip_words:
                                # 跳过纯动词、副词等
                                # 简单规则：人名通常不以常见副词/连词结尾
                                if not candidate.endswith(('地', '得', '了', '着', '过')):
                                    candidate_counter[candidate] += 1
                                    # 计算位置
                                    pos = sum(len(t) for t in token_texts[:idx-lookback])
                                    candidate_positions[candidate].append(pos)
                
                start_idx = idx + 1
        
        # 过滤：只保留出现≥2次的候选
        new_entities = []
        for name, count in candidate_counter.items():
            if count < 2:
                continue
            # 跳过已存在的实体
            if name in existing_texts:
                continue
            # 跳过如果已有实体是该名称的子串或超串
            if any(name.startswith(t) or t.startswith(name) for t in existing_texts if len(t) >= 2):
                continue
            
            # 创建新实体
            first_pos = candidate_positions[name][0]
            new_entity = Entity(
                text=name,
                type='PER',
                start=first_pos,
                end=first_pos + len(name),
                confidence=0.6,  # 边界词发现的实体给中等置信度
            )
            new_entities.append(new_entity)
        
        return new_entities

    def discover_compound_entities(
        self,
        full_text: str,
        existing_entities: List[Entity],
    ) -> List[Entity]:
        """
        通用实体统计发现：从全文扫描中发现"字A+字B"组合模式（2026-05-02）
        
        P0级别核心方法。不依赖词表，纯从文本统计中学习组合模式。
        
        策略：
        1. 找到所有单字PER实体（如"药"、"萧"、"云"）
        2. 统计"单字+后继字"组合出现在对话引导词前面的次数
        3. 如果"药老说道"出现多次，而"药师说道"不出现，说明"药老"才是说话角色
        
        方向A增强（2026-05-02）：字符紧密度预筛选
        借鉴WBA（Word Boundary Attention）思想，真正的复合实体（如"药老"），
        其构成字符之间有极高的紧密度。对于单字PER"药"，统计其后面紧跟"老"的比例。
        如果紧密度高（如70%），则"药老"很可能是真正的复合实体。
        
        Args:
            full_text: 完整文本
            existing_entities: 已有的实体列表
            
        Returns:
            新发现的组合实体列表
        """
        # 收集所有单字PER实体
        single_char_pers = set()
        for entity in existing_entities:
            if entity.type == 'PER' and len(entity.text) == 1:
                single_char_pers.add(entity.text)
        
        if not single_char_pers:
            return []
        
        # 边界词列表
        BOUNDARY_WORDS = [
            '说道', '问道', '喊道', '笑道', '淡淡道', '沉声道', '冷声道',
            '轻声道', '低声道', '道', '来到', '走出', '看着',
            '点了点头', '摇了摇头', '皱眉', '转身', '站起', '坐下',
            '讽刺道', '承喏道', '打趣道', '柔声道', '安慰道', '询问道',
            '赞叹道', '怪笑道', '冷笑道', '喃喃道', '怪声道',
        ]
        
        # 非姓氏排除列表（高频代词、指示词、常见动词等）
        NON_SURNAME_CHARS = {
            '我', '你', '他', '她', '它', '们', '这', '那', '哪', '谁',
            '什', '么', '怎', '为', '什', '如', '果', '但', '是', '而',
            '且', '或', '又', '也', '还', '更', '最', '非', '不', '没',
            '已', '经', '正', '在', '将', '会', '能', '可', '应', '该',
            '只', '是', '就', '才', '都', '全', '每', '各', '另', '某',
            '有', '无', '多', '少', '大', '小', '高', '低', '好', '坏',
            '的', '了', '着', '过', '吗', '呢', '吧', '啊', '呀', '哦',
            '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
            '百', '千', '万', '亿', '第', '上', '下', '前', '后', '左',
            '右', '中', '内', '外', '旁', '边', '面', '里', '间',
        }
        
        # 方向A：字符紧密度统计（基于全文）
        # 对于每个单字PER，统计其在全文中后面紧跟的字符分布
        # 真正的复合实体（如"药老"），其构成字符之间有极高的紧密度
        char_following_full = defaultdict(Counter)  # char -> {next_char -> count}
        char_total_full = Counter()  # char -> total_following_chars_count_in_full_text
        
        for char in single_char_pers:
            if char in NON_SURNAME_CHARS:
                continue
            
            start = 0
            while True:
                pos = full_text.find(char, start)
                if pos == -1:
                    break
                
                # 检查该字符后面是否紧跟一个字
                if pos + 1 < len(full_text):
                    next_char = full_text[pos + 1]
                    # 跳过标点和空白
                    if next_char not in '，。！？；：""''（）【】《》\n\r\t 、…':
                        char_following_full[char][next_char] += 1
                        char_total_full[char] += 1
                
                start = pos + 1
        
        # 统计"单字+后继字"组合出现在边界词前面的次数
        combo_counter = Counter()
        combo_positions = defaultdict(list)
        
        for char in single_char_pers:
            # 跳过明显非姓氏字符
            if char in NON_SURNAME_CHARS:
                continue
            
            start = 0
            while True:
                pos = full_text.find(char, start)
                if pos == -1:
                    break
                
                # 检查该字符后面是否紧跟一个字
                if pos + 1 < len(full_text):
                    next_char = full_text[pos + 1]
                    # 跳过标点和空白
                    if next_char in '，。！？；：""''（）【】《》\n\r\t 、…':
                        start = pos + 1
                        continue
                    
                    combo = char + next_char
                    
                    # 检查该组合后面不远处是否有边界词（50字符内）
                    context_end = min(len(full_text), pos + 60)
                    context = full_text[pos:context_end]
                    has_boundary = any(bw in context for bw in BOUNDARY_WORDS)
                    
                    if has_boundary:
                        combo_counter[combo] += 1
                        combo_positions[combo].append(pos)
                
                start = pos + 1
        
        # 过滤：只保留出现≥2次的组合
        existing_texts = set(e.text for e in existing_entities)
        new_entities = []
        
        from pipeline.nlp_basics import SINGLE_CHAR_SURNAMES
        
        for combo, count in combo_counter.items():
            if count < 2:
                continue
            
            # 跳过已存在的实体
            if combo in existing_texts:
                continue
            
            # 增加姓氏检查，只保留第一个字是姓氏的组合
            first_char = combo[0]
            if first_char not in SINGLE_CHAR_SURNAMES:
                continue
            
            # 方向A：字符紧密度预筛选（软阈值）
            # 计算紧密度：全文中first_char后面紧跟second_char的比例
            # 对于高频姓氏（如"萧"出现500次），"萧炎"占100次 → 紧密度20%
            # 对于低频姓氏（如"药"出现50次），"药老"占35次 → 紧密度70%
            # 设置较低阈值（10%）以容纳高频姓氏的多名字情况
            second_char = combo[1]
            total_full = char_total_full[first_char]
            following_full = char_following_full[first_char][second_char]
            tightness = following_full / total_full if total_full > 0 else 0.0
            
            # 紧密度阈值10% - 过滤掉那些几乎不连续出现的组合
            if tightness < 0.1:
                logger.debug(f"  REJECT LOW TIGHTNESS: {combo} (count={count}, tightness={tightness:.2f})")
                continue
            
            # 创建新实体
            first_pos = combo_positions[combo][0]
            
            logger.debug(f"  NEW COMPOUND: {combo} (count={count}, tightness={tightness:.2f}, pos={first_pos})")
            
            new_entity = Entity(
                text=combo,
                type='PER',
                start=first_pos,
                end=first_pos + len(combo),
                confidence=0.65,
            )
            new_entities.append(new_entity)
        
        logger.debug(f"[discover_compound_entities] found {len(new_entities)} new entities: {[e.text for e in new_entities]}")
        return new_entities

    def discover_surnames_from_text(
        self,
        full_text: str,
    ) -> Set[str]:
        """
        通用实体统计发现：从文本中自动发现虚构姓氏（2026-05-02）
        
        策略：扫描全文，统计所有单字在"X+称谓词"（如"X长老"、"X师兄"、"X大人"）
        或"X+说/道/问"模式中的出现频率。如果一个单字在这些语境中出现超过N次，
        且不是常见非姓氏字，就自动加入临时姓氏库，对当前小说生效。
        
        Returns:
            发现的姓氏集合
        """
        # 称谓词列表
        TITLE_WORDS = {
            '长老', '导师', '学长', '执事', '大人', '前辈', '师兄', '师姐',
            '师弟', '师妹', '老师', '师父', '师叔', '掌门', '宗主', '峰主',
            '堂主', '舵主', '管家', '少爷', '小姐', '公子', '姑娘', '掌柜',
            '老板', '将军', '王爷', '皇上', '皇后', '贵妃', '博士', '教授',
            '医生', '律师', '记者', '经理', '总裁', '总监', '部长', '局长',
            '队长', '尊者', '圣人', '之主', '大帝', '天尊', '真人',
            '说道', '问道', '喊道', '笑道', '道', '来到', '走出', '看着',
        }
        
        # 非姓氏排除列表
        NON_SURNAME_CHARS = {
            '我', '你', '他', '她', '它', '们', '这', '那', '哪', '谁',
            '什', '么', '怎', '为', '什', '如', '果', '但', '是', '而',
            '且', '或', '又', '也', '还', '更', '最', '非', '不', '没',
            '已', '经', '正', '在', '将', '会', '能', '可', '应', '该',
            '只', '是', '就', '才', '都', '全', '每', '各', '另', '某',
            '有', '无', '多', '少', '大', '小', '高', '低', '好', '坏',
            '的', '了', '着', '过', '吗', '呢', '吧', '啊', '呀', '哦',
            '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
            '百', '千', '万', '亿', '第', '上', '下', '前', '后', '左',
            '右', '中', '内', '外', '旁', '边', '面', '里', '间',
        }
        
        # 统计每个单字在称谓词前面出现的次数
        char_before_title_counter = Counter()
        
        for title in TITLE_WORDS:
            start = 0
            while True:
                pos = full_text.find(title, start)
                if pos == -1:
                    break
                
                # 提取称谓词前面的单字
                if pos >= 1:
                    char = full_text[pos - 1]
                    # 跳过标点和非姓氏字符
                    if char not in NON_SURNAME_CHARS and char not in '，。！？；：""''（）【】《》\n\r\t 、…':
                        char_before_title_counter[char] += 1
                
                start = pos + 1
        
        # 过滤：出现≥3次的单字认为是姓氏候选
        discovered_surnames = set()
        for char, count in char_before_title_counter.items():
            if count >= 3:
                discovered_surnames.add(char)
        
        logger.debug(f"[discover_surnames] found {len(discovered_surnames)} surnames: {discovered_surnames}")
        
        return discovered_surnames

    def _discover_name_suffixes(
        self,
        stats: Dict[str, Dict],
        entity_positions: Dict[str, List[Tuple[int, int]]],
        full_text: str,
    ) -> None:
        """
        通用实体统计发现：自动发现当前小说中的高频人名后缀模式（2026-05-02）
        
        从已确认的PER实体中提取末端字符，统计高频后缀。
        对具有这些后缀的候选实体，标记为具有名称后缀特征。
        """
        # 步骤1：收集高频实体的末端字符
        high_conf_entities = [
            text for text, stat in stats.items()
            if stat['occurrences'] >= self.high_conf_threshold
        ]
        
        suffix_counter = Counter()
        for entity_text in high_conf_entities:
            # 检查单字后缀
            if len(entity_text) >= 2:
                last_char = entity_text[-1]
                suffix_counter[last_char] += 1
                # 检查双字后缀
                if len(entity_text) >= 3:
                    last_two = entity_text[-2:]
                    suffix_counter[last_two] += 1
        
        # 步骤2：识别显著高频后缀（出现≥3次的高频实体共有此后缀）
        significant_suffixes = set()
        for suffix, count in suffix_counter.items():
            if count >= 3 and (len(suffix) == 1 or suffix in self.POSTFIX_PATTERNS_CANDIDATES):
                significant_suffixes.add(suffix)
        
        # 步骤3：为每个实体标记是否具有已知名称后缀
        for entity_text, stat in stats.items():
            if len(entity_text) >= 2:
                last_char = entity_text[-1]
                if last_char in significant_suffixes:
                    stat['name_suffix'] = last_char
                    stat['has_name_suffix'] = True
                elif len(entity_text) >= 3:
                    last_two = entity_text[-2:]
                    if last_two in significant_suffixes:
                        stat['name_suffix'] = last_two
                        stat['has_name_suffix'] = True

    def _get_right_neighbors_fast(self, text: str, end_pos: int,
                                  punctuation_set: frozenset, max_count: int = 2) -> Set[str]:
        """获取实体后的右邻字（非标点字符），使用预编译标点集合加速。"""
        neighbors = set()
        pos = end_pos
        count = 0

        while pos < len(text) and count < max_count:
            char = text[pos]
            if char not in punctuation_set:
                neighbors.add(char)
                count += 1
            pos += 1

        return neighbors

    def _find_chapter_index(self, position: int, chapter_ranges: list) -> Optional[int]:
        """在章节范围列表中查找位置所属的章节索引。"""
        for start, end, idx in chapter_ranges:
            if start <= position < end:
                return idx
        return None

    def _get_right_neighbors(self, text: str, end_pos: int, max_count: int = 2) -> Set[str]:
        """获取实体后的右邻字（非标点字符）"""
        punctuation_set = frozenset('，。！？；：""''（）【】《》\n\r\t ')
        return self._get_right_neighbors_fast(text, end_pos, punctuation_set, max_count)
    
    def _calculate_confidence(self, entity: Entity, stat: Dict) -> float:
        """
        根据上下文多样性 + FO-07 共现统计计算新置信度
        
        判定逻辑：
        - 白名单实体 → 保持原置信度
        - 总出现次数 < 3 → 0.3（低频噪声）
        - 总出现次数 ≥ 3，右邻字种类 ≤ 1 → 0.2（固定搭配片段）
        - 总出现次数 ≥ 5，右邻字种类 ≥ 3 → max(原置信度, 0.8)（高置信实体）
        - 其他情况 → 保持原置信度
        
        FO-07 共现增强：
        - 如果实体右邻字多样性不足但共现多样性高（≥3），且与高置信度实体共现 ≥ 2次
          → 恢复为中等置信度（0.5），避免误杀
        
        通用实体统计发现（2026-05-02）：
        - 新增上下文边界词命中率维度
        - 新增构词法后缀自动发现维度
        - 新增多维度综合打分框架（空壳，暂不改变现有逻辑）
        """
        # 白名单实体不受影响
        if entity.text in self.whitelist:
            return entity.confidence
        
        occ = stat['occurrences']
        diversity = len(stat['right_neighbors'])
        
        # 低频实体 → 降置信度
        if occ < self.min_occurrences:
            # 通用实体统计发现：如果有强边界词信号，可恢复为中等置信度
            if stat['boundary_hit_templates'] >= 3 and stat['boundary_hit_total'] >= 5:
                return max(entity.confidence, 0.5)
            return 0.3
        
        # 固定搭配片段（右邻字种类少）→ 极低置信度
        # FO-07: 但如果有强共现信号，则恢复为中等置信度
        if occ >= self.min_occurrences and diversity <= 1:
            co_diversity = stat['co_occurrence_diversity']
            high_conf_co = stat['high_conf_co_occurrence']
            if co_diversity >= 3 and high_conf_co >= 2:
                return max(entity.confidence, 0.5)
            # 通用实体统计发现：边界词命中率作为替代信号
            if stat['boundary_hit_templates'] >= 3 and stat['boundary_hit_total'] >= 5:
                return max(entity.confidence, 0.5)
            return 0.2
        
        # 高频高多样实体 → 提升置信度
        if occ >= self.high_conf_threshold and diversity >= self.diversity_threshold:
            return max(entity.confidence, 0.8)
        
        # 其他情况 → 保持原置信度
        # 通用实体统计发现：边界词命中可作为提升信号
        if stat['boundary_hit_templates'] >= 3 and stat['boundary_hit_total'] >= 5:
            return max(entity.confidence, 0.6)
        
        return entity.confidence

    def _calculate_composite_score(self, entity: Entity, stat: Dict) -> float:
        """
        通用实体统计发现：多维度综合打分（2026-05-02）
        
        综合置信度 = 基础置信度 × (0.3 + 0.25 × 出现频率归一化 
                                    + 0.25 × 右邻字多样性归一化 
                                    + 0.20 × 边界词命中率归一化
                                    + 0.20 × 构词法后缀分
                                    + 0.10 × 共现多样性归一化)
        
        当前为框架阶段，暂时返回原始置信度，不改变现有逻辑。
        后续可通过配置开关启用此方法替代 `_calculate_confidence`。
        """
        # Phase 1: 空壳框架，暂时返回原始置信度
        # Phase 4: 开启综合打分新逻辑时，将使用此方法
        base_confidence = entity.confidence
        
        occ = stat['occurrences']
        diversity = len(stat['right_neighbors'])
        
        # 出现频率归一化（0-1）
        freq_norm = min(1.0, occ / 10.0)  # 10次即满分
        
        # 右邻字多样性归一化（0-1）
        diversity_norm = min(1.0, diversity / 5.0)  # 5种即满分
        
        # 边界词命中率归一化（0-1）
        boundary_norm = min(1.0, stat['boundary_hit_templates'] / 5.0)  # 5种模板即满分
        
        # 构词法后缀分（0或1）
        suffix_score = 1.0 if stat['has_name_suffix'] else 0.0
        
        # 共现多样性归一化（0-1）
        co_occurrence_norm = min(1.0, stat['co_occurrence_diversity'] / 10.0)
        
        composite_score = base_confidence * (
            0.3 +
            0.25 * freq_norm +
            0.25 * diversity_norm +
            0.20 * boundary_norm +
            0.20 * suffix_score +
            0.10 * co_occurrence_norm
        )
        
        return min(1.0, composite_score)


# ============================================================
# 全局单例
# ============================================================

_validator_instance: Optional[ContextDiversityValidator] = None
_validator_lock = threading.Lock()

def get_context_validator(
    min_occurrences: int = 3,
    high_conf_threshold: int = 5,
    diversity_threshold: int = 2,
    whitelist: Optional[Set[str]] = None,
    mode: str = 'general',
) -> ContextDiversityValidator:
    """获取或创建全局上下文验证器实例（线程安全，双重检查锁）"""
    global _validator_instance
    if _validator_instance is None:
        with _validator_lock:
            if _validator_instance is None:
                _validator_instance = ContextDiversityValidator(
                    min_occurrences=min_occurrences,
                    high_conf_threshold=high_conf_threshold,
                    diversity_threshold=diversity_threshold,
                    whitelist=whitelist,
                    mode=mode,
                )
    return _validator_instance


def reset_context_validator() -> None:
    """重置全局上下文验证器实例，用于测试或重新初始化"""
    global _validator_instance
    with _validator_lock:
        _validator_instance = None
