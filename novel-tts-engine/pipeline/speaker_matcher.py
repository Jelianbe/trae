import re
import logging
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

from pipeline.character_manager import CharacterManager, Character, get_character_manager
from pipeline.nlp_basics import get_nlp
from pipeline.semantic_ranker import SemanticRanker, get_semantic_ranker
from pipeline.character_name_validator import CharacterNameValidator
from pipeline.speaker_hint_matcher import SpeakerHintMatcher, DIALOGUE_PATTERNS, SPEAKER_PATTERNS, SPEAKER_HINTS
from pipeline.descriptive_role_extractor import (
    DescriptiveRoleExtractor, TITLE_TRIGGERS, ACTION_TRIGGERS, ADDRESS_TRIGGERS, TitleTriggerMatcher, AddressTriggerMatcher,
)
from pipeline.self_reference_inferrer import SelfReferenceInferrer
from pipeline.pronoun_resolver import PronounResolver, PRONOUNS

logger = logging.getLogger(__name__)


@dataclass
class DialogueContext:
    text: str
    speaker_hint: Optional[str] = None
    prev_speaker: Optional[str] = None
    mentioned_characters: List[str] = field(default_factory=list)
    chapter_id: Optional[int] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None


@dataclass
class MatchResult:
    character: Character
    confidence: float
    match_type: str


# 群体说话人检测正则模式
#
# 用途：检测文本中的群体说话人（GROUP:N 或 GROUP:CROWD）
# 来源：中文语法结构（数量词+人称代词/群体名词）
# 边界：
#   - 模式1: 数字+人/位 → GROUP:N（如"三人"→GROUP:3）
#   - 模式2: 群体指示词 → GROUP:CROWD（众人/大家/所有/全体）
#   - 模式3: 齐声/异口同声 → GROUP:CROWD
# 更新日期：2026-05-09
# 维护者：项目规则
GROUP_NUMBER_PATTERN = re.compile(r'(\d+)人')
CROWD_INDICATOR_WORDS = {'众人', '大家', '所有', '全体', '人群', '群众'}
CROWD_ACTION_WORDS = {'齐声', '异口同声', '同声', '一起'}


def detect_group_speaker(text: str) -> Optional[str]:
    """检测文本中的群体说话人。
    
    Args:
        text: 待检测文本
        
    Returns:
        群体说话人标识（如 'GROUP:3' 或 'GROUP:CROWD'），或 None
    """
    # 模式1: 数字+人 → GROUP:N
    match = GROUP_NUMBER_PATTERN.search(text)
    if match:
        number = int(match.group(1))
        if 2 <= number <= 10:
            return f'GROUP:{number}'
    
    # 模式2: 群体指示词 → GROUP:CROWD
    for word in CROWD_INDICATOR_WORDS:
        if word in text:
            return 'GROUP:CROWD'
    
    # 模式3: 齐声/异口同声 → GROUP:CROWD
    for word in CROWD_ACTION_WORDS:
        if word in text:
            return 'GROUP:CROWD'
    
    return None


class SpeakerMatcher:
    # ROLE_CORE_WORDS
    #
    # 用途：角色核心词表，用于识别"修饰语+核心词"结构的角色指称
    # 来源：中文语言学称谓体系——社交称谓中的职衔类、职业类、身份类
    #       结合中文网文高频角色类型统计
    # 边界：
    #   - 仅包含能独立作为说话人身份的词
    #   - 中文里能独立作为角色指称的社会身份词汇是有限的
    #   - 此集合基于语言学分类，不应无限制扩容
    # 更新日期：2026-05-02
    # 维护者：项目规则
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
        self._current_project_id: str = ''
        self.semantic_ranker = semantic_ranker or get_semantic_ranker()
        self.l2_threshold = l2_threshold
        self._character_dialogues: Dict[str, List[str]] = defaultdict(list)
        self._role_extract_cache: Dict[str, List[str]] = {}
        self._temp_char_cache: Dict[str, Character] = {}

        self.name_validator = CharacterNameValidator(self.nlp)
        self.hint_matcher = SpeakerHintMatcher(self.name_validator)
        self.role_extractor = DescriptiveRoleExtractor()
        self.self_ref_inferrer = SelfReferenceInferrer(self.char_manager)
        self.pronoun_resolver = PronounResolver(self.char_manager)
        self.title_trigger_matcher = TitleTriggerMatcher(self.char_manager)
        self.address_trigger_matcher = AddressTriggerMatcher(self.char_manager)

    def _extract_descriptive_roles(self, text: str) -> List[str]:
        return self.role_extractor.extract(text)

    def _is_valid_character_name(self, name: str) -> bool:
        return self.name_validator.is_valid(name)

    def _is_verb(self, name: str) -> bool:
        return self.name_validator.is_verb(name)

    def _infer_gender_from_context(self, name: str, context: str) -> str:
        return self.self_ref_inferrer.infer_gender_from_context(name, context)

    def _has_speech_context(self, context: str) -> bool:
        """检测文本是否包含说话/动作上下文。
        
        优先使用 HanLP 词性标注检测动词后是否紧跟引号或冒号。
        降级方案：HanLP 不可用时使用关键词匹配（仅作为辅助信号）。
        
        Args:
            context: 待检测的上下文文本
            
        Returns:
            是否包含说话上下文
        """
        # 优先方案：使用 HanLP 词性标注
        try:
            result = self.nlp.analyze(context)
            tokens = result.tokens
            pos_tags = [t.pos for t in tokens]
            
            # 检测动词(v/vd/VV)后是否紧跟引号或冒号
            for i, pos in enumerate(pos_tags):
                if pos in ('v', 'vd', 'VV', 'V', 'VE', 'VC', 'VW', 'VL', 'VH', 'VO', 'VP', 'VB'):
                    # 检查后续字符是否有引号或冒号
                    if i + 1 < len(tokens):
                        next_token = tokens[i + 1].text
                        if next_token in ('"', '"', ''', ''', '：', ':', '「', '『'):
                            return True
                    # 检查当前token后是否有标点符号
                    if i + 1 < len(pos_tags):
                        next_pos = pos_tags[i + 1]
                        if next_pos in ('PU', 'w', ':'):
                            return True
            
            # 检测引号对的存在（表示对话）
            has_open_quote = any(t.text in ('"', ''', '「', '『') for t in tokens)
            has_close_quote = any(t.text in ('"', ''', '」', '』') for t in tokens)
            if has_open_quote and has_close_quote:
                return True
                
        except Exception:
            # HanLP 不可用，降级到关键词匹配
            # TODO: 仅在 HanLP 不可用时使用此降级方案
            return self._has_speech_context_fallback(context)
        
        return False
    
    def _has_speech_context_fallback(self, context: str) -> bool:
        """降级方案：使用关键词匹配检测说话上下文。
        
        注意：此方法仅作为 HanLP 不可用时的降级方案，
        关键词只能作为辅助信号，不能作为唯一依据。
        """
        SPEECH_ACTION_PATTERNS = [
            r'(?:说道|道|问|说|喊道|叫道|笑道|沉声道|低声道|高声道|冷冷道|淡淡道)',
            r'(?:点头|摇头|皱眉|转身|站起|坐下|抬手|挥手|冷笑|微笑)',
            r'(?:出现|走来|过来|进来|离开|推开|抓住|跑进|冲进)',
            r'(?:看着|盯着|扫了|抬起|放下|举起|拔出|跪)',
        ]
        return any(
            re.search(pat, context) for pat in SPEECH_ACTION_PATTERNS
        )

    def _register_temporary_character(self, name: str, context: str) -> Optional[Character]:
        # 使用通则推理检测说话上下文
        if not self._has_speech_context(context):
            return None

        if name in self._temp_char_cache:
            return self._temp_char_cache[name]

        try:
            gender = self._infer_gender_from_context(name, context)
            char = self.char_manager.add_character(
                name=name,
                project_id=self._current_project_id,
                aliases=set(),
                gender=gender
            )
            if char:
                self._temp_char_cache[name] = char
                logger.debug(f"注册临时角色: {name} (性别: {gender})")
            return char
        except Exception as e:
            logger.warning(f"注册临时角色失败: {name}, {e}")
            return None

    def backfill_unknown_speakers(self, sentences: list) -> int:
        if not sentences:
            return 0

        confirmed_chars = list(self.char_manager._confirmed_characters.values())
        if not confirmed_chars:
            return 0

        char_map = {}
        for char in confirmed_chars:
            char_map[char.name] = char
            for alias in char.aliases:
                char_map[alias] = char

        backfill_count = 0
        for sentence in sentences:
            if not sentence.speaker.startswith("未知"):
                continue

            text = sentence.text
            sorted_chars = sorted(char_map.items(), key=lambda x: len(x[0]), reverse=True)
            for char_name, char in sorted_chars:
                if char_name in text:
                    sentence.speaker = char_name
                    sentence.speaker_id = char.id
                    backfill_count += 1
                    break

        return backfill_count

    def _extract_context_speakers(
        self,
        text: str,
        context_before: str,
        context_after: str
    ) -> List[Tuple[str, str, float]]:
        candidates = []
        seen_names = set()

        if context_before:
            speech_pattern = self.hint_matcher.extract_speech_patterns(context_before)
            for name, hint in speech_pattern:
                if not self.name_validator.is_valid_speaker_candidate(name):
                    continue
                char = self.char_manager.get_character_by_name(name)
                if not char:
                    char = self._register_temporary_character(name, context_before)
                if char and char.name not in seen_names:
                    candidates.append((char.name, f'显式提示:{name}{hint}', 0.95))
                    seen_names.add(char.name)

            descriptive_roles = self.role_extractor.extract(context_before)
            for role in descriptive_roles:
                if role not in seen_names:
                    char = self.char_manager.get_character_by_name(role)
                    if not char:
                        char = self._register_temporary_character(role, context_before)
                    if char:
                        candidates.append((char.name, '描述性角色', 0.80))
                        seen_names.add(char.name)

            try:
                result = self.nlp.analyze(context_before)
                before_pers = [e for e in result.entities if e.type == 'PER']
                for pe in reversed(before_pers):
                    if not self.name_validator.is_valid(pe.text) or self.name_validator.is_verb(pe.text):
                        continue
                    is_substring = False
                    for seen in seen_names:
                        if pe.text in seen or seen in pe.text:
                            is_substring = True
                            break
                    if is_substring:
                        continue
                    char = self.char_manager.get_character_by_name(pe.text)
                    if not char:
                        char = self._register_temporary_character(pe.text, context_before)
                    if char and char.name not in seen_names:
                        candidates.append((char.name, '上下文PER(前)', 0.75))
                        seen_names.add(char.name)
            except Exception:
                pass

            pronoun_candidates = self.pronoun_resolver.resolve(context_before)
            for name, reason, confidence in pronoun_candidates:
                if name not in seen_names and self.name_validator.is_valid(name) and not self.name_validator.is_verb(name):
                    candidates.append((name, reason, confidence))
                    seen_names.add(name)

        if text:
            self_ref_candidates = self.self_ref_inferrer.infer(text, context_before or '')
            for name, reason, confidence in self_ref_candidates:
                if name not in seen_names:
                    candidates.append((name, reason, confidence))
                    seen_names.add(name)

        if context_after:
            descriptive_roles = self.role_extractor.extract(context_after)
            for role in descriptive_roles:
                if role not in seen_names:
                    char = self.char_manager.get_character_by_name(role)
                    if not char:
                        char = self._register_temporary_character(role, context_after)
                    if char:
                        candidates.append((char.name, '描述性角色(后)', 0.75))
                        seen_names.add(char.name)

            try:
                result = self.nlp.analyze(context_after)
                after_pers = [e for e in result.entities if e.type == 'PER']
                for pe in after_pers:
                    if not self.name_validator.is_valid(pe.text) or self.name_validator.is_verb(pe.text):
                        continue
                    is_substring = False
                    for seen in seen_names:
                        if pe.text in seen or seen in pe.text:
                            is_substring = True
                            break
                    if is_substring:
                        continue
                    char = self.char_manager.get_character_by_name(pe.text)
                    if not char:
                        char = self._register_temporary_character(pe.text, context_after)
                    if char and char.name not in seen_names:
                        candidates.append((char.name, '上下文PER(后)', 0.70))
                        seen_names.add(char.name)
            except Exception:
                pass

        if not candidates:
            candidates.append(('未知', '无充分证据', 0.30))

        return candidates

    @contextmanager
    def chapter_context(self, chapter_id: int):
        self.reset_activity()
        self._current_chapter_id = chapter_id
        try:
            yield self
        finally:
            self._current_chapter_id = None

    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        return self.hint_matcher.extract_speaker_hint(text)

    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        return self.hint_matcher._is_address_pattern(text, prefix)

    def extract_post_dialogue_hint(self, suffix: str) -> Optional[str]:
        return self.hint_matcher.extract_post_dialogue_hint(suffix)

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
        return self.title_trigger_matcher.match_by_title(title)

    def match_by_semantic(self, sentence: str) -> Optional[MatchResult]:
        all_chars = self.char_manager.get_all_characters()
        if not all_chars:
            return None

        profiles = []
        char_by_name = {}

        for char in all_chars:
            char_by_name[char.name] = char
            dialogue_context = self.get_dialogue_context(char.name)
            if dialogue_context:
                profiles.append((char.name, dialogue_context))
            else:
                profile_parts = []
                profile_parts.append(char.name)
                if char.aliases:
                    profile_parts.extend(char.aliases)
                if char.gender != "unknown":
                    profile_parts.append("他" if char.gender == "male" else "她")
                profile_parts.append(f"{char.name}说道")
                profile_parts.append(f"{char.name}点头")
                profile_parts.append(f"{char.name}看着")
                for alias in char.aliases:
                    profile_parts.append(f"{alias}道")

                profile_text = " ".join(profile_parts)
                profiles.append((char.name, profile_text))

        results = self.semantic_ranker.rank_with_profiles(
            sentence=sentence,
            profiles=profiles,
            threshold=self.l2_threshold,
        )

        if not results:
            return None

        best_char_name, best_score = results[0]
        matched_char = char_by_name.get(best_char_name)

        if matched_char:
            confidence = 0.6 + (best_score - self.l2_threshold) * 0.5
            confidence = max(0.6, min(confidence, 0.8))

            return MatchResult(
                character=matched_char,
                confidence=confidence,
                match_type='semantic',
            )

        return None

    def match_by_trigger_words(self, text: str, context: DialogueContext) -> Optional[MatchResult]:
        title_candidates = self.title_trigger_matcher.extract_title_trigger_candidates(text)
        for name, match_type_str, conf in title_candidates:
            char = self.char_manager.get_character_by_name(name)
            if char:
                return MatchResult(
                    character=char,
                    confidence=conf,
                    match_type=match_type_str
                )

        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char:
                idx = text.find(prev_char.name)
                if idx >= 0:
                    context_window = text[max(0, idx-20):idx+20+len(prev_char.name)]
                    if any(action in context_window for action in ACTION_TRIGGERS):
                        return MatchResult(
                            character=prev_char,
                            confidence=0.65,
                            match_type='trigger_action_prev_speaker'
                        )

        for addr in ADDRESS_TRIGGERS:
            if addr in text:
                for char in self.char_manager.get_all_characters():
                    if addr in char.aliases or char.name.endswith(addr):
                        unique_recent = []
                        for recent in reversed(self._recent_speakers[-3:]):
                            if recent != char.name:
                                speaker = self.char_manager.get_character_by_name(recent)
                                if speaker and speaker not in unique_recent:
                                    unique_recent.append(speaker)

                        if len(unique_recent) == 1:
                            return MatchResult(
                                character=unique_recent[0],
                                confidence=0.70,
                                match_type='trigger_address'
                            )

        return None

    def match_by_pronoun(self, pronoun: str, context: DialogueContext) -> Optional[MatchResult]:
        gender = self.pronoun_resolver.resolve_by_pronoun(pronoun)
        if not gender:
            return None

        local_result = self.pronoun_resolver.resolve_in_local_window(gender, self._recent_speakers)
        if local_result:
            return local_result

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

    def _match_pronoun_in_local_window(self, gender: str) -> Optional[MatchResult]:
        return self.pronoun_resolver.resolve_in_local_window(gender, self._recent_speakers)

    def match_speaker(self, context: DialogueContext) -> Optional[MatchResult]:
        if context.context_before or context.context_after:
            context_candidates = self._extract_context_speakers(
                context.text,
                context.context_before or '',
                context.context_after or ''
            )
            if context_candidates:
                name, reason, confidence = context_candidates[0]
                if name == '未知':
                    unknown_char = Character(
                        id=-1,
                        name='未知',
                        aliases=set(),
                        gender='unknown'
                    )
                    return MatchResult(
                        character=unknown_char,
                        confidence=confidence,
                        match_type=f'context_reasoning:{reason}'
                    )
                char = self.char_manager.get_character_by_name(name, self._current_project_id)
                if char:
                    return MatchResult(
                        character=char,
                        confidence=confidence,
                        match_type=f'context_reasoning:{reason}'
                    )

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

                # 如果 speaker_hint 存在但匹配不到角色，创建新角色
                hint_char = self.char_manager.find_or_create(
                    context.speaker_hint,
                    project_id=self._current_project_id,
                    context=context.text
                )
                if hint_char:
                    return MatchResult(
                        character=hint_char,
                        confidence=0.85,
                        match_type='speaker_hint_created'
                    )

        mentioned = context.mentioned_characters or []
        if mentioned:
            for name in mentioned:
                result = self.match_by_name(name)
                if result:
                    return result

                result = self.match_by_alias(name)
                if result:
                    return result

        if context.chapter_id is not None and self.semantic_ranker.is_available():
            result = self.match_by_semantic(context.text)
            if result:
                return result

        trigger_result = self.match_by_trigger_words(context.text, context)
        if trigger_result:
            return trigger_result

        result = self._infer_from_address(context)
        if result:
            return result

        return None

    def _infer_from_address(self, context: DialogueContext) -> Optional[MatchResult]:
        text = context.text
        addressed_char = self.address_trigger_matcher.find_addressed_character(text)
        address_confidence = 0.9 if addressed_char else 0

        candidates = []

        if addressed_char:
            for char in self.char_manager.get_all_characters():
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
        self._character_activity[character_id] = self._character_activity.get(character_id, 0) + 1

        if name not in self._recent_speakers:
            self._recent_speakers.append(name)
            if len(self._recent_speakers) > 10:
                self._recent_speakers.pop(0)

    def cache_dialogue(self, character_name: str, dialogue_text: str):
        if character_name not in self._character_dialogues:
            self._character_dialogues[character_name] = []
        self._character_dialogues[character_name].append(dialogue_text)
        if len(self._character_dialogues[character_name]) > 20:
            self._character_dialogues[character_name] = self._character_dialogues[character_name][-20:]

    def get_dialogue_context(self, character_name: str) -> str:
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
        self._temp_char_cache.clear()

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
        dialogues = []
        seen_positions = set()

        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                if not any(start <= p < end or p <= start < p + (end - start) for p in seen_positions):
                    dialogues.append((start, end, match.group(1)))
                    seen_positions.add(start)

        self._build_dialogue_cache(text, chapter_id)

        self._recent_speakers.clear()
        self._recent_mentions.clear()
        self._character_activity.clear()

        dialogues.sort(key=lambda x: x[0])
        results = []
        prev_speaker = None
        last_successful_speaker = None
        for i, (start, end, dialogue) in enumerate(dialogues):
            prefix_start = dialogues[i-1][1] if i > 0 else 0
            prefix = text[prefix_start:start].strip()

            suffix_end = dialogues[i+1][0] if i < len(dialogues) - 1 else len(text)
            suffix = text[end:suffix_end].strip()

            speaker_hint, hint_type = self.extract_speaker_hint(prefix + " " + suffix)
            mentioned = self.extract_mentioned_characters(prefix + " " + suffix)

            if mentioned:
                self.update_mentions(mentioned)

            pronoun_speaker = last_successful_speaker

            context = DialogueContext(
                text=prefix + " " + dialogue + " " + suffix,
                speaker_hint=speaker_hint,
                prev_speaker=pronoun_speaker,
                mentioned_characters=mentioned,
                chapter_id=chapter_id
            )

            match_result = self.match_speaker(context)

            if match_result:
                speaker = match_result.character
                self.update_activity(speaker.id, speaker.name)
                prev_speaker = speaker.name
                last_successful_speaker = speaker.name
            else:
                speaker = None
                prev_speaker = None

            results.append((dialogue, speaker))

        return results

    def _build_dialogue_cache(self, text: str, chapter_id: int = None):
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
                if char and getattr(char, 'name', None):
                    self.cache_dialogue(char.name, dialogue)


_speaker_matcher: Optional[SpeakerMatcher] = None


def get_speaker_matcher() -> SpeakerMatcher:
    global _speaker_matcher
    if _speaker_matcher is None:
        _speaker_matcher = SpeakerMatcher()
    return _speaker_matcher
