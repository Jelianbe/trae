import re
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
from contextlib import contextmanager

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.character_manager import CharacterManager, Character, get_character_manager
from pipeline.nlp_basics import get_nlp
from pipeline.semantic_ranker import SemanticRanker, get_semantic_ranker


@dataclass
class DialogueContext:
    text: str
    speaker_hint: Optional[str] = None
    prev_speaker: Optional[str] = None
    mentioned_characters: List[str] = None
    chapter_id: Optional[int] = None
    
    def __post_init__(self):
        if self.mentioned_characters is None:
            self.mentioned_characters = []


@dataclass
class MatchResult:
    character: Character
    confidence: float
    match_type: str


PRONOUNS = {
    'male': {'他', '他俩', '他们'},
    'female': {'她', '她俩', '她们'},
    'unknown': {'它', '它们', '其'},
}

GROUP_SPEAKERS = {
    '三人': 'GROUP:3',
    '他们三人': 'GROUP:3',
    '他们三个': 'GROUP:3',
    '三人异口同声': 'GROUP:3',
    '众人': 'GROUP:CROWD',
    '大家': 'GROUP:CROWD',
    '齐声': 'GROUP:CROWD',
    '所有人': 'GROUP:CROWD',
}

SPEAKER_HINTS = {
    '说道', '道', '说', '问道', '答道', '笑道', '喊道', '叫道', '怒道',
    '冷冷道', '淡淡道', '沉声道', '低声道', '高声道', '大声道',
    '开口道', '接口道', '插口道', '回应道', '点头道', '摇头道',
    '冷笑', '微笑', '大笑', '叹气', '叹息', '惊呼', '大喊', '大叫',
    '恭敬地', '恭敬', '轻声', '低声', '高声', '大声',
    '介绍道', '命令道', '下令', '报告', '推测', '皱眉', '犹豫',
    '接话', '齐声', '猜测', '暗道', '心想',
}

DIALOGUE_PATTERNS = [
    re.compile(r'"([^"]+)"'),
    re.compile(r'「([^」]+)」'),
    re.compile(r'『([^』]+)』'),
]

SPEAKER_PATTERNS = [
    re.compile(r'^([^\s]+?)(说道|道|问道|答道|笑道|喊道|叫道|怒道|冷冷道|淡淡道|沉声道|低声道|高声道|大声道|开口道|接口道|插口道|回应道|点头道|摇头道)'),
    re.compile(r'^([^\s]+?)(冷笑|微笑|大笑|叹气|叹息|惊呼|大喊|大叫)'),
    re.compile(r'^([^\s]+?)(恭敬地|恭敬|轻声|低声|高声|大声)说道'),
    # 都市格式：对话后跟动作/描述（"dialogue" 说话人动作）
    re.compile(r'^([^\s，。！？]{2,10}?)(的声音|介绍道|命令道|下令|报告|推测|皱眉|犹豫|接话|猜测|齐声)'),
]


class SpeakerMatcher:
    def __init__(
        self,
        character_manager: CharacterManager = None,
        semantic_ranker: SemanticRanker = None,
        l2_threshold: float = 0.7,
    ):
        self.char_manager = character_manager or get_character_manager()
        self.nlp = get_nlp()
        self._character_activity: Dict[int, int] = defaultdict(int)
        self._recent_speakers: List[str] = []
        self._recent_mentions: List[str] = []
        self._mention_counter = 0
        self._current_chapter_id: Optional[int] = None
        self.semantic_ranker = semantic_ranker or get_semantic_ranker()
        self.l2_threshold = l2_threshold
        self._character_dialogues: Dict[str, List[str]] = defaultdict(list)
    
    @contextmanager
    def chapter_context(self, chapter_id: int):
        self.reset_activity()
        self._current_chapter_id = chapter_id
        try:
            yield self
        finally:
            self._current_chapter_id = None
    
    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        text = text.strip()
        
        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(text)
            if match:
                speaker = match.group(1).strip()
                hint = match.group(2)
                if speaker and len(speaker) <= 10:
                    if self._is_address_pattern(text, speaker):
                        return None, ""
                    return speaker, hint
        
        for hint in SPEAKER_HINTS:
            if hint in text:
                idx = text.find(hint)
                prefix = text[:idx].strip()
                
                if prefix:
                    for pattern in DIALOGUE_PATTERNS:
                        match = pattern.search(prefix)
                        if match:
                            prefix = prefix[:match.start()].strip()
                            break
                    
                    if prefix and len(prefix) <= 10:
                        if self._is_address_pattern(text, prefix):
                            return None, ""
                        return prefix, hint
        
        return None, ""
    
    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        """检查是否是呼唤句式（前缀是被呼唤的对象而非说话人）"""
        prefix_len = len(prefix)
        if prefix_len < len(text):
            next_char = text[prefix_len]
            if next_char in '！!':
                # 获取感叹号之后的内容（去掉感叹号本身）
                after_exclamation = text[prefix_len + 1:].strip()
                # 如果感叹号后紧跟说话提示词，则不是呼唤模式
                if after_exclamation.startswith(('说', '道', '问', '答', '笑', '喊', '叫')):
                    return False
                return True
            if next_char in '：:':
                # 获取冒号之后的内容（去掉冒号本身）
                after_colon = text[prefix_len + 1:].strip()
                # 如果冒号后紧跟说话提示词，则不是呼唤模式
                if after_colon.startswith(('说', '道', '问', '答', '笑', '喊', '叫')):
                    return False
                return True
            if next_char in '，,':
                remaining = text[prefix_len + 1:].strip()
                dialogue_start = re.match(r'^[您你你我我他她我们你们他们]+', remaining)
                if dialogue_start and len(dialogue_start.group()) >= 1:
                    return True
        return False
    
    def extract_post_dialogue_hint(self, suffix: str) -> Optional[str]:
        suffix = suffix.strip()
        
        patterns = [
            re.compile(r'^([^\s]+?)(说道|道|问道|答道|笑道|喊道|叫道)'),
            re.compile(r'^(他|她)说道'),
            re.compile(r'^(他|她)道'),
        ]
        
        for pattern in patterns:
            match = pattern.search(suffix)
            if match:
                speaker = match.group(1).strip()
                if speaker in ('他', '她'):
                    return speaker
                if speaker and len(speaker) <= 10:
                    return speaker
        
        return None
    
    def extract_mentioned_characters(self, text: str) -> List[str]:
        try:
            result = self.nlp.analyze(text)
            persons = [e.text for e in result.entities if e.type == 'PER']
        except Exception:
            persons = []
        return list(set(persons))
    
    def match_by_name(self, name: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_name(name)
        if char:
            return MatchResult(
                character=char,
                confidence=1.0,
                match_type='exact_name'
            )
        return None
    
    def match_by_alias(self, alias: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_alias(alias)
        if char:
            return MatchResult(
                character=char,
                confidence=0.9,
                match_type='alias'
            )
        return None
    
    def match_by_title(self, title: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_name(title)
        if char:
            return MatchResult(
                character=char,
                confidence=1.0,
                match_type='exact_name'
            )
        
        char = self.char_manager.get_character_by_alias(title)
        if char:
            return MatchResult(
                character=char,
                confidence=0.95,
                match_type='title'
            )
        
        return None
    
    def match_by_semantic(self, sentence: str) -> Optional[MatchResult]:
        """L2 语义匹配阶段。

        使用句子嵌入模型对候选角色进行语义相似度排序。
        先用角色名/别名进行初步筛选，然后用对话历史画像进行精细排序。

        Args:
            sentence: 输入句子（通常包含对话和上下文）

        Returns:
            匹配结果，如果没有候选超过阈值则返回 None
        """
        all_chars = self.char_manager.get_all_characters()
        if not all_chars:
            return None

        # 构建对话画像列表：(角色名, 画像文本)
        profiles = []
        char_by_name = {}  # 角色名 -> Character
        
        for char in all_chars:
            char_by_name[char.name] = char
            # 获取对话历史作为画像
            dialogue_context = self.get_dialogue_context(char.name)
            if dialogue_context:
                # 使用对话历史作为语义画像
                profiles.append((char.name, dialogue_context))
            else:
                # 没有对话历史，用角色名+别名作为画像
                profile_text = char.name + " " + " ".join(char.aliases)
                profiles.append((char.name, profile_text))

        # 使用语义排序器（用对话画像进行匹配）
        results = self.semantic_ranker.rank_with_profiles(
            sentence=sentence,
            profiles=profiles,
            threshold=self.l2_threshold,
        )

        if not results:
            return None

        # 取最高相似度的结果
        best_char_name, best_score = results[0]
        matched_char = char_by_name.get(best_char_name)

        if matched_char:
            # 将语义相似度映射到置信度 (0.6-0.8 范围)
            confidence = 0.6 + (best_score - self.l2_threshold) * 0.5
            confidence = min(confidence, 0.8)

            return MatchResult(
                character=matched_char,
                confidence=confidence,
                match_type='semantic',
            )

        return None
    
    def match_by_pronoun(self, pronoun: str, context: DialogueContext) -> Optional[MatchResult]:
        gender = None
        for g, pronouns in PRONOUNS.items():
            if pronoun in pronouns:
                gender = g
                break
        
        if not gender:
            return None
        
        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char and prev_char.gender == gender:
                return MatchResult(
                    character=prev_char,
                    confidence=0.8,
                    match_type='pronoun_prev_speaker'
                )
        
        for mentioned in reversed(self._recent_mentions):
            char = self.char_manager.get_character_by_name(mentioned)
            if char and char.gender == gender:
                return MatchResult(
                    character=char,
                    confidence=0.7,
                    match_type='pronoun_recent'
                )
        
        candidates = []
        for char in self.char_manager.get_all_characters():
            if char.gender == gender:
                activity = self._character_activity.get(char.id, 0)
                candidates.append((char, activity))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return MatchResult(
                character=candidates[0][0],
                confidence=0.4,
                match_type='pronoun_activity'
            )
        
        return None
    
    def match_speaker(self, context: DialogueContext) -> Optional[MatchResult]:
        if context.speaker_hint:
            if context.speaker_hint in ('他', '她'):
                result = self.match_by_pronoun(context.speaker_hint, context)
                if result:
                    return result
            else:
                result = self.match_by_name(context.speaker_hint)
                if result:
                    return result
                
                result = self.match_by_alias(context.speaker_hint)
                if result:
                    return result
                
                result = self.match_by_title(context.speaker_hint)
                if result:
                    return result
        
        mentioned = context.mentioned_characters or []
        if mentioned:
            for name in mentioned:
                result = self.match_by_name(name)
                if result:
                    return result
                
                result = self.match_by_alias(name)
                if result:
                    return result
        
        # L2 semantic matching (after L0/L1, before address inference)
        if context.chapter_id is not None and self.semantic_ranker.is_available():
            result = self.match_by_semantic(context.text)
            if result:
                return result
        
        result = self._infer_from_address(context)
        if result:
            return result
        
        return None
    
    def _infer_from_address(self, context: DialogueContext) -> Optional[MatchResult]:
        text = context.text
        all_chars = self.char_manager.get_all_characters()
        
        addressed_char = None
        address_confidence = 0
        
        for char in all_chars:
            if char.name in text:
                addressed_char = char
                address_confidence = 0.9
                break
        
        if not addressed_char:
            for char in all_chars:
                for alias in char.aliases:
                    if alias in text:
                        addressed_char = char
                        address_confidence = 0.8
                        break
                if addressed_char:
                    break
        
        candidates = []
        
        if addressed_char:
            for char in all_chars:
                if char.id != addressed_char.id:
                    activity = self._character_activity.get(char.id, 0)
                    candidates.append((char, 0.6 + activity * 0.05, activity))
        
        if self._recent_mentions:
            for mentioned in reversed(self._recent_mentions[-5:]):
                char = self.char_manager.get_character_by_name(mentioned)
                if char and (not addressed_char or char.id != addressed_char.id):
                    activity = self._character_activity.get(char.id, 0)
                    candidates.append((char, 0.5 + activity * 0.03, activity))
        
        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char and (not addressed_char or prev_char.id != addressed_char.id):
                activity = self._character_activity.get(prev_char.id, 0)
                candidates.append((prev_char, 0.4, activity))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        seen_ids = set()
        unique_candidates = []
        for char, conf, activity in candidates:
            if char.id not in seen_ids:
                seen_ids.add(char.id)
                unique_candidates.append((char, conf, activity))
        
        if not unique_candidates:
            return None
        
        best_char, best_conf, _ = unique_candidates[0]
        
        MIN_CONFIDENCE_THRESHOLD = 0.4
        if best_conf < MIN_CONFIDENCE_THRESHOLD:
            return None
        
        return MatchResult(
            character=best_char,
            confidence=min(best_conf, 0.6),
            match_type='address_inference'
        )
    
    def update_activity(self, character_id: int, name: str):
        """记录角色出现，增加活跃度"""
        self._character_activity[character_id] = self._character_activity.get(character_id, 0) + 1
        
        # 维护最近活跃角色列表（最多10个）
        if name not in self._recent_speakers:
            self._recent_speakers.append(name)
            if len(self._recent_speakers) > 10:
                self._recent_speakers.pop(0)
    
    def cache_dialogue(self, character_name: str, dialogue_text: str):
        """缓存角色的对话文本，用于L2语义画像"""
        if character_name not in self._character_dialogues:
            self._character_dialogues[character_name] = []
        self._character_dialogues[character_name].append(dialogue_text)
        # 保持最近20条对话
        if len(self._character_dialogues[character_name]) > 20:
            self._character_dialogues[character_name] = self._character_dialogues[character_name][-20:]
    
    def get_dialogue_context(self, character_name: str) -> str:
        """获取角色的对话上下文（用于L2语义匹配）"""
        if character_name in self._character_dialogues:
            return " ".join(self._character_dialogues[character_name])
        return ""
    
    def update_mentions(self, names: List[str]):
        for name in names:
            if name not in self._recent_mentions:
                self._recent_mentions.append(name)
        if len(self._recent_mentions) > 20:
            self._recent_mentions = self._recent_mentions[-20:]
    
    def reset_activity(self):
        self._character_activity.clear()
        self._recent_speakers.clear()
        self._recent_mentions.clear()
    
    def get_speaker_for_sentence(self, sentence: str, prev_speaker: str = None, 
                                  chapter_id: int = None) -> Tuple[Optional[Character], str]:
        speaker_hint, hint_type = self.extract_speaker_hint(sentence)
        mentioned = self.extract_mentioned_characters(sentence)
        
        if mentioned:
            self.update_mentions(mentioned)
        
        context = DialogueContext(
            text=sentence,
            speaker_hint=speaker_hint,
            prev_speaker=prev_speaker or (self._recent_speakers[-1] if self._recent_speakers else None),
            mentioned_characters=mentioned,
            chapter_id=chapter_id
        )
        
        match_result = self.match_speaker(context)
        
        if match_result:
            self.update_activity(match_result.character.id, match_result.character.name)
            return match_result.character, match_result.character.name
        
        return None, None
    
    def analyze_dialogue(self, text: str, chapter_id: int = None) -> List[Tuple[str, Optional[Character]]]:
        # 第一轮：提取所有对话并建立缓存
        dialogues = []
        seen_positions = set()
        
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                if not any(start <= p < end or p <= start < p + (end - start) for p in seen_positions):
                    dialogues.append((start, end, match.group(1)))
                    seen_positions.add(start)
        
        # 第一轮：建立对话历史缓存
        self._build_dialogue_cache(text, chapter_id)
        
        # 重置追踪状态，避免第一轮缓存建立干扰第二轮说话人匹配
        self._recent_speakers.clear()
        self._recent_mentions.clear()
        
        # 第二轮：匹配说话人
        dialogues.sort(key=lambda x: x[0])
        results = []
        prev_speaker = None
        for i, (start, end, dialogue) in enumerate(dialogues):
            prefix_start = dialogues[i-1][1] if i > 0 else 0
            prefix = text[prefix_start:start].strip()
            
            suffix_end = dialogues[i+1][0] if i < len(dialogues) - 1 else len(text)
            suffix = text[end:suffix_end].strip()
            
            speaker_hint, hint_type = self.extract_speaker_hint(prefix + " " + suffix)
            mentioned = self.extract_mentioned_characters(prefix + " " + suffix)
            
            if mentioned:
                self.update_mentions(mentioned)
            
            context = DialogueContext(
                text=prefix + " " + dialogue + " " + suffix,
                speaker_hint=speaker_hint,
                prev_speaker=prev_speaker,
                mentioned_characters=mentioned,
                chapter_id=chapter_id
            )
            
            match_result = self.match_speaker(context)
            
            if match_result:
                speaker = match_result.character
                self.update_activity(speaker.id, speaker.name)
                prev_speaker = speaker.name
            else:
                speaker = None
                prev_speaker = None
            
            results.append((dialogue, speaker))
        
        return results
    
    def _build_dialogue_cache(self, text: str, chapter_id: int = None):
        """
        第一轮扫描全文，建立角色对话历史缓存。
        先提取所有有明确说话人的对话，缓存到对应角色名下。
        这样第二轮语义匹配时可以利用已建立的对话画像。
        """
        all_dialogues = []
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                dialogue = match.group(1)
                
                prefix_start = max(0, start - 50)
                suffix_end = min(len(text), end + 50)
                prefix = text[prefix_start:start].strip()
                suffix = text[end:suffix_end].strip()
                context = prefix + " " + dialogue + " " + suffix
                
                all_dialogues.append((start, context, dialogue))
        
        all_dialogues.sort(key=lambda x: x[0])
        
        for _, context, dialogue in all_dialogues:
            speaker_hint, _ = self.extract_speaker_hint(context)
            if speaker_hint and speaker_hint not in ('他', '她'):
                char = self.char_manager.get_character_by_name(speaker_hint)
                if not char:
                    char = self.char_manager.get_character_by_alias(speaker_hint)
                if char:
                    self.cache_dialogue(char.name, dialogue)


_speaker_matcher: Optional[SpeakerMatcher] = None


def get_speaker_matcher() -> SpeakerMatcher:
    global _speaker_matcher
    if _speaker_matcher is None:
        _speaker_matcher = SpeakerMatcher()
    return _speaker_matcher
