import re
import json
import logging
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SfxWord:
    text: str
    position: int
    sfx_type: str


SFX_DICT_PATH = Path(__file__).parent.parent / "models" / "sfx_dict.json"


DEFAULT_SFX_WORDS = {
    '哗啦', '轰隆', '砰', '啪', '咚', '叮', '当',
    '叽叽喳喳', '嗡嗡', '喵', '汪', '哞', '咩', '嘎嘎',
    '呼呼', '沙沙', '淅沥', '滴答', '哗哗', '隆隆',
    '嗖', '嗒嗒', '噼里啪啦', '乒乒乓乓', '叮叮当当',
    '咕噜', '咕嘟', '呼哧', '扑通', '咔嚓', '咯吱',
    '嗷呜', '吱吱', '嗡', '嗡嗡嗡', '嗡嗡作响',
    '哇', '哎呀', '哎哟', '啊', '哦', '嗯',
    '嘘', '咳', '哼', '嘿',
    '咚咚', '当当', '叮叮', '啪啪', '砰砰',
    '哗啦啦', '轰隆隆', '滴答答', '淅沥沥',
    '呼',
    
    '桀桀', '喝喝', '嘶嘶', '嗬嗬', '吼吼', '嗷嗷',
    '噗', '噗嗤', '噗通', '噼啪', '噼噼啪啪',
    '叽里呱啦', '叽咕', '叽喳', '叽叽', '喳喳',
    '咕咕', '咕咚', '咕哝', '咕叽', '咕涌',
    '嘟嘟', '嘟囔', '嘟噜',
    '嗒', '嗒嗒嗒', '嗒啦',
    '咔', '咔咔', '咔哒', '咔吧', '咔嚓嚓',
    '咯', '咯咯咯', '咯噔', '咯嗒',
    '吱', '吱溜', '吱呀', '吱哇', '吱吱吱',
    '嘶', '嘶啦',
    '嗖嗖', '嗖嗖嗖',
    '呼啦', '呼噜',
    '哗啦啦啦',
    '轰', '轰隆隆隆',
    '砰砰砰',
    '啪嗒', '啪嚓', '啪啪啪',
    '咚咚咚',
    '叮当响', '叮铃', '叮咚',
    '当当当',
    '嗡嗡嗡嗡',
    '喵喵', '喵呜', '喵喵喵',
    '汪汪', '汪汪汪',
    '哞哞',
    '咩咩', '咩咩咩',
    '嘎', '嘎嘎嘎',
    '呱', '呱呱', '呱呱呱',
    '喔喔', '喔喔喔',
    '咕咕咕', '咕咕叫',
    '吱吱叫',
    '叽叽叫',
    '嗡嗡叫',
    '呼呼呼',
    '沙沙沙',
    '淅淅沥沥', '淅沥沥',
    '滴滴答答', '滴滴答',
    '哗哗哗',
    '隆隆隆',
    '嗖的一声',
    '嗒的一声',
    '咔的一声',
    '啪的一声',
    '砰的一声',
    '咚的一声',
    '叮的一声',
    '当的一声',
    '呼的一声',
    '哗的一声',
    '轰的一声',
    '噗的一声',
    '嘶的一声',
    '吱的一声',
    '咕的一声',
    '嘟的一声',
    '嗷的一声',
    '哇的一声',
    '嗯的一声',
    '哈的一声',
    '嘿的一声',
    '呵的一声',
    '嘻的一声',
    '咯的一声',
    '咳的一声',
    '哼的一声',
    '嘘的一声',
    '哎呀呀', '哎呀妈呀',
    '哎哟哟',
    '哇塞', '哇哇', '哇哇哇',
    '啊哈', '啊啊', '啊啊啊',
    '哦哦', '哦哦哦', '哦豁',
    '嗯嗯', '嗯嗯嗯',
    '呵呵呵', '哈哈哈', '嘿嘿嘿', '嘻嘻嘻',
    '哼哼', '哼哼哼',
    '咳咳', '咳咳咳',
    '嘘嘘',
    '嘶嘶嘶',
    '嗬', '嗬嗬', '嗬嗬嗬',
    '吼', '吼吼', '吼吼吼',
    '嗷', '嗷嗷嗷',
    '噗噗', '噗噗噗',
    '噼啪啦', '噼里啪啦啦',
    '乒乒', '乓乓', '乒铃乓啷',
    '叮铃铃', '叮叮咚咚',
    '咕噜噜', '咕噜咕噜',
    '咕嘟嘟', '咕嘟咕嘟',
    '呼哧呼哧', '呼哧哧',
    '扑通通', '扑通扑通',
    '咔嚓嚓', '咔嚓咔嚓',
    '咯吱吱', '咯吱咯吱',
    '吱溜溜', '吱溜吱溜',
    '哗啦啦啦', '哗啦哗啦',
    '轰隆隆隆', '轰隆轰隆',
    '滴答答答', '滴答滴答',
    '淅沥沥沥', '淅沥淅沥',
    '沙沙沙沙', '沙沙作响',
    '呼呼呼呼', '呼呼作响',
    '嗡嗡嗡嗡', '嗡嗡作响',
    '嘎吱', '嘎吱嘎吱',
    '吱嘎', '吱嘎吱嘎',
    '哐当', '哐当哐当', '哐',
    '咣当', '咣', '咣咣',
    '锵', '锵锵', '锵锵锵',
    '唰', '唰唰', '唰唰唰', '唰啦',
    '嗖嗖作响',
    '嗒嗒作响',
    '咚咚作响',
    '当当作响',
    '叮叮作响',
    '啪啪作响',
    '砰砰作响',
    '咔咔作响',
    '咯咯作响',
    '吱吱作响',
    '嘶嘶作响',
    '呼呼作响',
    '沙沙作响',
    '嗡嗡作响',
    '嘎嘎作响',
    '呱呱作响',
    '咕咕作响',
    '嘟嘟作响',
    '嗷嗷作响',
    '哇哇作响',
    '啊啊作响',
    '哦哦作响',
    '嗯嗯作响',
    '哈哈作响',
    '呵呵作响',
    '嘿嘿作响',
    '嘻嘻作响',
    '哼哼作响',
    '咳咳作响',
    '嘘嘘作响',
    '嘶嘶作响',
    '嗬嗬作响',
    '吼吼作响',
    '噗噗作响',
    '噼啪作响',
    '乒乒作响',
    '乓乓作响',
    '哐哐作响',
    '咣咣作响',
    '锵锵作响',
    '唰唰作响',
}


class SfxDetector:
    SFX_PATTERNS = [
        re.compile(r'[哗轰砰啪咚叮当叽喳嗡喵汪哞咩嘎呼沙淅滴隆嗖噼乒咕咔咯吱嗷嘿哈哦嗯嘘咳哼]{2,}'),
    ]
    
    SFX_EXCLUDE = {
        '一声', '两声', '三声', '四声', '五声', '六声', '七声', '八声', '九声', '十声',
        '一下', '两下', '三下', '四下', '五下',
    }
    
    SFX_TYPE_MAP = {
        'water': ['哗', '啦', '淅', '沥', '滴', '答', '咕', '嘟'],
        'explosion': ['轰', '隆', '砰', '啪', '崩'],
        'knock': ['咚', '叮', '当', '咔', '嚓', '咯', '吱'],
        'animal': ['喵', '汪', '哞', '咩', '嘎', '叽', '喳', '嗡', '吱', '嗷'],
        'wind': ['呼', '沙', '嗖', '呼呼', '沙沙'],
        'laugh': ['哈', '呵', '嘿', '嘻', '咯'],
        'voice': ['哇', '哎', '呀', '哟', '啊', '哦', '嗯', '嘘', '咳', '哼'],
    }

    def __init__(self, dict_path: str = None):
        self.sfx_words: Set[str] = set()
        self._trie: Dict[str, any] = {}
        self._trie_built: bool = False
        self._load_dictionary(dict_path)

    def _load_dictionary(self, dict_path: str = None):
        self.sfx_words = DEFAULT_SFX_WORDS.copy()
        
        path = Path(dict_path) if dict_path else SFX_DICT_PATH
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.sfx_words.update(data)
                    elif isinstance(data, dict) and 'words' in data:
                        self.sfx_words.update(data['words'])
                logger.info(f"拟声词词典加载成功: {len(self.sfx_words)} 个词")
            except Exception as e:
                logger.warning(f"拟声词词典加载失败: {e}")
        
        self._build_trie()
    
    def _build_trie(self):
        """构建trie树用于快速匹配"""
        self._trie = {}
        for word in self.sfx_words:
            if word not in self.SFX_EXCLUDE:
                node = self._trie
                for char in word:
                    if char not in node:
                        node[char] = {}
                    node = node[char]
                node['#'] = word  # 标记词尾
        self._trie_built = True

    def detect(self, text: str) -> List[SfxWord]:
        results = []
        
        if self._trie_built:
            for i in range(len(text)):
                node = self._trie
                if text[i] in node:
                    node = node[text[i]]
                    if '#' in node:
                        word = node['#']
                        sfx_type = self._get_sfx_type(word)
                        results.append(SfxWord(
                            text=word,
                            position=i,
                            sfx_type=sfx_type
                        ))
                    for j in range(i + 1, len(text)):
                        if text[j] in node:
                            node = node[text[j]]
                            if '#' in node:
                                word = node['#']
                                sfx_type = self._get_sfx_type(word)
                                results.append(SfxWord(
                                    text=word,
                                    position=i,
                                    sfx_type=sfx_type
                                ))
                        else:
                            break
        
        for pattern in self.SFX_PATTERNS:
            for match in pattern.finditer(text):
                word = match.group()
                if word in self.SFX_EXCLUDE:
                    continue
                if word not in self.sfx_words and len(word) >= 2:
                    sfx_type = self._get_sfx_type(word)
                    results.append(SfxWord(
                        text=word,
                        position=match.start(),
                        sfx_type=sfx_type
                    ))
        
        results = self._deduplicate(results)
        results.sort(key=lambda x: x.position)
        
        return results

    def _get_sfx_type(self, word: str) -> str:
        for sfx_type, chars in self.SFX_TYPE_MAP.items():
            for char in chars:
                if char in word:
                    return sfx_type
        return 'other'

    def _deduplicate(self, results: List[SfxWord]) -> List[SfxWord]:
        if not results:
            return []
        
        results.sort(key=lambda x: (x.position, -len(x.text)))
        
        unique = []
        for sfx in results:
            sfx_end = sfx.position + len(sfx.text)
            
            skip = False
            for existing in unique:
                existing_end = existing.position + len(existing.text)
                
                # 检查是否是完全相同的匹配（文本和位置都相同）
                if sfx.text == existing.text and sfx.position == existing.position:
                    skip = True
                    break
                
                # 检查是否被现有匹配完全包含
                if (existing.position <= sfx.position and 
                    sfx_end <= existing_end):
                    skip = True
                    break
            
            if not skip:
                unique.append(sfx)
        
        return unique

    def is_sfx(self, word: str) -> bool:
        if word in self.sfx_words:
            return True
        
        for pattern in self.SFX_PATTERNS:
            if pattern.fullmatch(word):
                return True
        
        return False

    def add_word(self, word: str):
        self.sfx_words.add(word)

    def remove_word(self, word: str) -> bool:
        if word in self.sfx_words:
            self.sfx_words.discard(word)
            return True
        return False

    def save_dictionary(self, path: str = None):
        save_path = Path(path) if path else SFX_DICT_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(list(self.sfx_words), f, ensure_ascii=False, indent=2)
        
        print(f"拟声词词典已保存: {save_path}")

    def get_all_words(self) -> List[str]:
        return sorted(list(self.sfx_words))


def detect_sfx(text: str) -> List[SfxWord]:
    detector = SfxDetector()
    return detector.detect(text)


def is_sfx_word(word: str) -> bool:
    detector = SfxDetector()
    return detector.is_sfx(word)


def get_sfx_words() -> List[str]:
    detector = SfxDetector()
    return detector.get_all_words()
