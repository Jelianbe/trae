import hanlp
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
import re
import warnings

warnings.filterwarnings('ignore')

HANLP_MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models', 'hanlp')


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
}

FAMILY_SUFFIXES = {'家', '府', '门', '派', '宗', '族', '山庄', '阁', '楼', '院'}

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
            print("HanLP模型加载成功")
        except Exception as e:
            print(f"HanLP模型加载失败: {e}")
            print("将使用简化模式...")
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
                
                enhanced_entities = self._enhance_entities(tokens, pos_tags, hanlp_entities)
                
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
            print(f"HanLP分析失败: {e}")
            return self._analyze_simple(text, sentences)

    def _parse_ner_result(self, ner_result: List) -> List[Entity]:
        entities = []
        for ner_item in ner_result:
            if isinstance(ner_item, (list, tuple)) and len(ner_item) >= 3:
                entity_text = ner_item[0]
                entity_type = ner_item[1]
                start = ner_item[2] if len(ner_item) >= 3 else 0
                end = ner_item[3] if len(ner_item) >= 4 else start + 1
                
                normalized_type = self._normalize_entity_type(entity_type)
                
                entities.append(Entity(
                    text=entity_text,
                    type=normalized_type,
                    start=start,
                    end=end
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
                          base_entities: List[Entity]) -> List[Entity]:
        rule_entities = []
        rule_covered_indices = set()
        rule_entity_texts = set()
        
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
                    end=i + 2
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
                    end=i + 2
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
                    end=i + 2
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
