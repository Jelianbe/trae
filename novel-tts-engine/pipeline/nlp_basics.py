import hanlp
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
import re
import warnings
import logging

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
}

# 验证: TITLE_WORDS == PROFESSION_TITLES | TRADITIONAL_TITLES
assert TITLE_WORDS == (PROFESSION_TITLES | TRADITIONAL_TITLES), "TITLE_WORDS 应该等于 PROFESSION_TITLES 和 TRADITIONAL_TITLES 的并集"

# 职位称呼后缀（X总/X哥/X姐/X叔/X伯）
POSITION_SUFFIXES = {
    '总', '哥', '姐', '叔', '伯', '姨', '婶', '爷', '公', '婆',
}

PREFIX_TITLES = {'老', '小', '大'}

ORG_SUFFIXES = {'会', '帮', '社', '团', '协会', '联盟', '组织', '集团', '公司', '企业', '商会', '公会', '教派', '宗门'}

FAMILY_SUFFIXES = {'家', '府', '山庄', '阁', '楼', '院'}

LOCATION_SUFFIXES = {'城', '镇', '村', '山', '河', '湖', '海', '岛', '谷', '峰', '殿', '宫'}

SINGLE_CHAR_SURNAMES = {
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
    '樊', '兰', '殷', '施', '陶', '洪', '温', '芦', '牛', '安',
    '莫', '章', '仇', '祖', '符', '柳', '邢', '梅', '阮', '倪',
}

MULTI_CHAR_SURNAMES = {
    '欧阳', '司马', '上官', '诸葛', '东方', '皇甫', '南宫', '西门',
    '独孤', '慕容', '轩辕', '令狐', '夏侯', '公孙', '长孙', '宇文',
}


class NLPBasics:
    def __init__(self, use_offline: bool = True, enable_foreign_name_merge: bool = False):
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
                
                all_entities.extend(enhanced_entities)
            
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
        rule_entities = []
        rule_covered_indices = set()
        rule_entity_texts = set()
        
        # 检测文体：如果包含西方译名特征（如"·"分隔符或大量非中文姓氏的NR词），跳过中文特化规则
        is_western_style = '·' in (raw_text or '') or any(pos in ('NR', 'nr') and t not in SINGLE_CHAR_SURNAMES and t not in MULTI_CHAR_SURNAMES for t, pos in zip(tokens, pos_tags[:len(tokens)]))
        if is_western_style:
            return base_entities
        
        if self.enable_foreign_name_merge:
            i = 0
            while i < len(tokens):
                pos = pos_tags[i] if i < len(pos_tags) else 'X'
                if pos not in ('NR', 'nr'):
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
                    
                    rule_entities.append(Entity(
                        text=merged,
                        type='PER',
                        start=start,
                        end=j
                    ))
                    rule_entity_texts.add(merged)
                    for idx in range(start, j):
                        rule_covered_indices.add(idx)
                    i = j
                    continue
                
                i += 1
        
        i = 0
        while i < len(tokens):
            if i in rule_covered_indices:
                i += 1
                continue
            
            token = tokens[i]
            pos = pos_tags[i] if i < len(pos_tags) else 'X'
            
            # Rule 1: Prefix titles (老X/小X/大X) where X is a surname
            if token in PREFIX_TITLES and i + 1 < len(tokens):
                next_token = tokens[i + 1]
                next_pos = pos_tags[i + 1] if i + 1 < len(pos_tags) else 'X'
                
                if next_token in SINGLE_CHAR_SURNAMES and next_pos in ('NR', 'nr'):
                    combined = token + next_token
                    rule_entities.append(Entity(
                        text=combined,
                        type='PER',
                        start=i,
                        end=i + 2,
                        confidence=0.90
                    ))
                    rule_entity_texts.add(combined)
                    rule_covered_indices.update([i, i + 1])
                    i += 2
                    continue
            
            # Rule 4: Standalone professional titles (博士/教授/医生等)
            if token in PROFESSION_TITLES:
                rule_entities.append(Entity(
                    text=token,
                    type='PER',
                    start=i,
                    end=i + 1,
                    confidence=0.85
                ))
                rule_entity_texts.add(token)
                rule_covered_indices.add(i)
                i += 1
                continue
            
            # Rule 5: Organization names with suffixes (暗影会/异能者联盟)
            # Only match if token is 2+ chars (avoid false positives like "我会", "来公司")
            if i + 1 < len(tokens) and (i + 1) not in rule_covered_indices:
                next_token = tokens[i + 1]
                if next_token in ORG_SUFFIXES and len(token) >= 2:
                    combined = token + next_token
                    rule_entities.append(Entity(
                        text=combined,
                        type='ORG',
                        start=i,
                        end=i + 2,
                        confidence=0.85
                    ))
                    rule_entity_texts.add(combined)
                    rule_covered_indices.update([i, i + 1])
                    i += 2
                    continue
            
            # Rule 2: Single surname + title words (陈管家/林少爷)
            if pos not in ('NR', 'nr'):
                i += 1
                continue
            
            if len(token) > 1:
                i += 1
                continue
            
            if token not in SINGLE_CHAR_SURNAMES:
                i += 1
                continue
            
            if i + 1 >= len(tokens) or (i + 1) in rule_covered_indices:
                i += 1
                continue
            
            next_token = tokens[i + 1]
            combined = token + next_token
            
            if next_token in TITLE_WORDS:
                rule_entities.append(Entity(
                    text=combined,
                    type='PER',
                    start=i,
                    end=i + 2,
                    confidence=0.95
                ))
                rule_entity_texts.add(combined)
                rule_covered_indices.update([i, i + 1])
                i += 2
                continue
            
            # Rule 3: Position titles (张总/李哥/王姐)
            if next_token in POSITION_SUFFIXES:
                rule_entities.append(Entity(
                    text=combined,
                    type='PER',
                    start=i,
                    end=i + 2,
                    confidence=0.90
                ))
                rule_entity_texts.add(combined)
                rule_covered_indices.update([i, i + 1])
                i += 2
                continue
            
            if next_token in FAMILY_SUFFIXES:
                rule_entities.append(Entity(
                    text=combined,
                    type='ORG',
                    start=i,
                    end=i + 2,
                    confidence=0.90
                ))
                rule_entity_texts.add(combined)
                rule_covered_indices.update([i, i + 1])
                i += 2
                continue
            
            if next_token in LOCATION_SUFFIXES:
                rule_entities.append(Entity(
                    text=combined,
                    type='LOC',
                    start=i,
                    end=i + 2,
                    confidence=0.85
                ))
                rule_entity_texts.add(combined)
                rule_covered_indices.update([i, i + 1])
                i += 2
                continue
            
            i += 1
        
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
                
                entities.append(Entity(text=entity_text, type=entity_type, start=start, end=i))
            else:
                i += 1
        
        return entities

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


def get_nlp(enable_foreign_name_merge: bool = False) -> NLPBasics:
    global _nlp_instance
    if _nlp_instance is None:
        _nlp_instance = NLPBasics(enable_foreign_name_merge=enable_foreign_name_merge)
    return _nlp_instance


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
