import re
import logging
from typing import List, Optional, Dict, Tuple, TYPE_CHECKING
from collections import defaultdict

from pipeline.character_manager import CharacterManager, Character
from pipeline.nlp_basics import ALL_SPEECH_VERBS, extract_srl_arg0s
from pipeline.semantic_ranker import SemanticRanker
from pipeline.speaker_matcher import MatchResult
from pipeline.matchers.speaker_hint_matcher import (
    DIALOGUE_PATTERNS, SPEAKER_PATTERNS, _clean_speaker_name,
)
from pipeline.matchers.self_reference_inferrer import SelfReferenceInferrer
from utils.config import (
    SPEAKER_MATCHER_INSUFFICIENT_CANDIDATES_MAX_COUNT,
    SPEAKER_MATCHER_INSUFFICIENT_CANDIDATES_MAX_CONF,
)
from pipeline.strategies.srl_arg0_normalizer import _normalize_srl_arg0

if TYPE_CHECKING:
    from pipeline.speaker_matcher import DialogueContext

logger = logging.getLogger(__name__)


class CandidatePool:
    """候选池：管理所有候选角色来源的查询和排序。"""

    def __init__(
        self,
        char_manager: CharacterManager,
        semantic_ranker: SemanticRanker,
        speaker_matcher: object,
    ):
        self.char_manager = char_manager
        self.semantic_ranker = semantic_ranker
        # 代理引用：提取的方法通过 __getattr__ 访问 SpeakerMatcher 的其他方法/属性
        self._speaker_matcher = speaker_matcher

    def __getattr__(self, name: str):
        """将所有未在 CandidatePool 上定义的属性/方法代理到 SpeakerMatcher。"""
        if '_speaker_matcher' in self.__dict__ and self._speaker_matcher is not None:
            return getattr(self._speaker_matcher, name)
        raise AttributeError(
            f"'CandidatePool' object has no attribute '{name}'"
        )

    def match_by_name(self, name: str, project_id: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_name(name, project_id)
        if char:
            return MatchResult(
                character=char,
                confidence=1.0,
                match_type='exact_name'
            )
        return None

    def match_by_alias(self, alias: str, project_id: str) -> Optional[MatchResult]:
        char = self.char_manager.get_character_by_alias(alias, project_id)
        if char:
            return MatchResult(
                character=char,
                confidence=0.9,
                match_type='alias'
            )
        return None

    def match_by_semantic(self, sentence: str, project_id: str) -> Optional[MatchResult]:
        # H-20260516-10: 改用 get_eligible_characters
        all_chars = self.char_manager.get_eligible_characters(project_id)
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

    def _match_candidate_to_character(
        self,
        candidate_name: str,
        context: str,
        skip_speech_check: bool = False,
        require_library: bool = False
    ) -> Optional[Character]:
        """将候选名字匹配到角色库。

        优先级：
        1. 锁定角色精确匹配（最高优先）
        2. 普通角色精确匹配 + 别名匹配
        3. 创建临时角色（兜底）

        注意：不再使用模糊匹配（在旁白中搜索角色名），
        因为这样会导致匹配到错误角色（旁白中提到的角色 ≠ 说话人）。

        设计原则：角色库优先，但只基于候选名字本身进行精确/别名匹配，
        不依赖旁白中的模糊搜索。
        当 require_library=True 时，不创建临时角色。
        """
        # 步骤1：精确匹配角色名（项目范围内）
        char = self.char_manager.get_character_by_name(candidate_name, self._current_project_id)
        if char:
            return char

        # 步骤2：别名匹配
        char = self.char_manager.get_character_by_alias(candidate_name, self._current_project_id)
        if char:
            return char

        # 步骤2.5：角色核心词后缀匹配（无新增硬编码）
        # H-20260516-10: 改用 get_eligible_characters
        from pipeline.descriptive_role_extractor import DescriptiveRoleExtractor

        all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
        if len(candidate_name) >= 4:
            for char in all_chars:
                if len(char.name) >= 2 and len(candidate_name) > len(char.name):
                    if candidate_name.endswith(char.name):
                        return char

        for core_word in DescriptiveRoleExtractor.ROLE_CORE_WORDS_SORTED:
            if len(candidate_name) > len(core_word) and candidate_name.endswith(core_word):
                exact_char = self.char_manager.get_character_by_name(core_word, self._current_project_id)
                if exact_char:
                    return exact_char
                for char in all_chars:
                    if core_word in char.name:
                        return char

        # 步骤3：创建临时角色（兜底）
        # require_library=True 时不创建临时角色
        if not require_library:
            temp_char = self._register_temporary_character(candidate_name, context, skip_speech_check)
            return temp_char
        return None

    def _infer_from_address(
        self, narration: str, context: 'DialogueContext'
    ) -> Optional[MatchResult]:
        addressed_char = self.address_trigger_matcher.find_addressed_character(narration)
        address_confidence = 0.9 if addressed_char else 0

        candidates = []

        if addressed_char:
            # H-20260516-10: 改用 get_eligible_characters
            for char in self.char_manager.get_eligible_characters(self._current_project_id):
                if char.id != addressed_char.id:
                    activity = self._get_activity_weight(char.id)
                    candidates.append((char, 0.6 + activity * 0.05, activity))

        if self._recent_mentions:
            for mentioned in reversed(self._recent_mentions[-5:]):
                char = self.char_manager.get_character_by_name(mentioned, self._current_project_id)
                if char and (not addressed_char or char.id != addressed_char.id):
                    activity = self._get_activity_weight(char.id)
                    candidates.append((char, 0.5 + activity * 0.03, activity))

        if context.prev_speaker:
            prev_char = self.char_manager.get_character_by_name(context.prev_speaker)
            if prev_char and (not addressed_char or prev_char.id != addressed_char.id):
                activity = self._get_activity_weight(prev_char.id)
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

    def _match_from_character_library(
        self, narration: str, locked_only: bool = False
    ) -> Optional[Character]:
        """在旁白中匹配角色库。
        
        用途：优先匹配角色库中的角色，避免 NER 重复创建
        来源：角色库（characters 表）
        边界：
          - locked_only=True 时只匹配锁定角色
          - locked_only=False 时匹配所有角色
          - 精确匹配角色名和别名
          - Phase 2: 增加说话关系验证，只返回有说话动词/动作暗示支撑的匹配
        更新日期：2026-05-09
        维护者：说话人识别改进方案
        """
        if locked_only:
            characters = self.char_manager.get_locked_characters(self._current_project_id)
        else:
            # H-20260516-10: 非锁定模式使用 eligible_characters
            characters = self.char_manager.get_eligible_characters(self._current_project_id)
        
        for char in characters:
            if char.name in narration:
                idx = narration.index(char.name)
                window = narration[max(0, idx - 20):idx + len(char.name) + 20]
                has_speech_verb = any(v in window for v in ALL_SPEECH_VERBS)
                has_action_hint = any(a in window for a in ['道', '说', '问', '答', '笑', '叹', '点头', '摇头', '转身', '看着', '望向', '走上前', '上前'])
                if has_speech_verb or has_action_hint:
                    return char
        
        for char in characters:
            if char.name in narration:
                return char
            for alias in char.aliases:
                if alias in narration:
                    return char
        
        return None

    def _extract_context_speakers(
        self,
        text: str,
        context_before: str,
        context_after: str,
        prefix_narration: str = ''
    ) -> List[Tuple[str, str, float]]:
        """从上下文中提取候选说话人，使用策略列表模式。"""
        candidates = []
        seen_names = set()

        # 策略列表：每个策略独立提候选，按优先级顺序执行
        strategies = [
            self._strategy_prefix_narration,      # 步骤0: 引号前旁白
            self._strategy_pronoun,                # 步骤1: 代词消解
            self._strategy_ner,                    # 步骤2: NER人名提取
            self._strategy_descriptive_before,     # 描述性角色(前)
            self._strategy_self_reference,         # 自称推断
            self._strategy_descriptive_after,      # 描述性角色(后)
            self._strategy_context_characters,     # 方向1: 语境角色优先
            self._strategy_dynamic_candidates,     # 方向3: 动态候选
            self._strategy_fallback,               # 兜底: 角色库旁白匹配
            self._strategy_srl_arg0,               # SRL ARG0 候选信号层
        ]

        for strategy in strategies:
            strategy(text, context_before, context_after, prefix_narration, candidates, seen_names)

        # 后处理：动作主语优先 + 近因衰减
        candidates = self._apply_action_subject_boost(candidates, context_before)
        candidates = self._apply_recency_decay(candidates)

        if not candidates:
            candidates.append(('未知_无法推断', '无上下文线索', 0.30))

        return candidates

    # ------------------------------------------------------------------ #
    # 策略方法：每个方法从不同角度提取候选说话人
    # 每个策略函数体内的代码与原始 _extract_context_speakers 保持一致
    # 所有策略通过 candidates / seen_names 就地修改来累积候选
    # ------------------------------------------------------------------ #

    def _strategy_prefix_narration(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """步骤0：引号前旁白前缀优先（H-20260516-10）

        格式：赵总监皱起眉头问道："谁批准的？" -> prefix="赵总监皱起眉头问道"
        如果旁白前缀中包含角色库角色名，则该角色有最高优先级
        """
        if prefix_narration:
            speech_verbs = {'道', '说', '问', '答', '笑道', '说道', '问道', '答道',
                            '冷喝', '喝道', '冷笑', '叹道', '怒道', '斥道', '叫道', '喊道'}
            all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
            sorted_chars = sorted(all_chars, key=lambda c: -len(c.name))
            for char in sorted_chars:
                if char.name in prefix_narration and char.name not in seen_names:
                    after_name = prefix_narration[prefix_narration.index(char.name) + len(char.name):
                                                  prefix_narration.index(char.name) + len(char.name) + 15]
                    has_speech = any(v in after_name for v in speech_verbs)
                    candidates.append((char.name,
                        '同行动作主语' if has_speech else '同行引用',
                        0.88 if has_speech else 0.82))
                    seen_names.add(char.name)
                    break

    def _strategy_pronoun(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """步骤1：代词消解优先于 NER（代词比描述性短语更可靠）"""
        pronoun_weak_signal = False
        if context_before:
            pronoun_result = self._resolve_pronoun_in_context(context_before)
            if pronoun_result:
                if pronoun_result.get('weak_signal'):
                    # P1-3: 代词消解失败传递弱信号
                    # 记录存在未解析代词，后续步骤不强行匹配
                    pronoun_weak_signal = True
                    logger.debug(f"代词弱信号: {pronoun_result['reason']}")
                else:
                    char = self._match_candidate_to_character(pronoun_result['name'], context_before)
                    if char:
                        candidates.append((char.name, f'代词消解({pronoun_result["reason"]})', 0.80 if char.id != -1 else 0.65))
                        seen_names.add(char.name)

    def _strategy_ner(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """步骤2：NER 人名提取（无预注册场景的关键路径）

        注意：2026-05-14 曾移除此路径（消融实验显示 -1.9%）
        但重新评估发现：-1.9% 是在有预注册场景下的结果，无预注册时此路径是必需的角色发现机制
        修复日期：2026-05-22
        限制：只在 prefix_narration 包含说话动词时才从 NER 提取，避免从对话内容中提取被提及的角色
        """
        if prefix_narration and not candidates:
            speech_verb_present = any(v in prefix_narration for v in 
                ['道', '说', '问', '答', '笑道', '说道', '问道', '答道', '冷喝', '喝道', '叹道', '怒道'])
            if speech_verb_present:
                ner_candidates = self._extract_from_ner(prefix_narration)
                for name, reason, conf in ner_candidates:
                    if name not in seen_names:
                        candidates.append((name, reason, conf))
                        seen_names.add(name)

    def _strategy_descriptive_before(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """描述性角色提取（从 context_before 旁白中）

        新方案A: 描述性角色映射到角色库（优先）或创建临时角色（兜底）
        """
        if context_before:
            before_narr = self._extract_narration('', context_before, '')
            if before_narr:
                descriptive_roles = self.role_extractor.extract(before_narr)
            else:
                descriptive_roles = []
            for role in descriptive_roles:
                if role not in seen_names:
                    char = self._match_candidate_to_character(role, before_narr, skip_speech_check=True, require_library=False)
                    if char:
                        candidates.append((char.name, '描述性角色', 0.80))
                        seen_names.add(role)

    def _strategy_self_reference(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """自称推断"""
        # 步骤3：身份词提取已删除（2026-05-12）
        # 原因：身份词提取在测试集中没有贡献正面准确率，且干扰主流程
        # 身份词太泛（如"长老"可能对应多个角色），依赖隐式静态映射表，违背核心原则
        if text:
            self_ref_candidates = self.self_ref_inferrer.infer(text, context_before or '')
            for name, reason, confidence in self_ref_candidates:
                if name not in seen_names:
                    char = self._match_candidate_to_character(name, text, require_library=False)
                    if char:
                        candidates.append((char.name, f'自称推断({reason})', 0.80))
                        seen_names.add(name)

    def _strategy_descriptive_after(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """描述性角色提取（从 context_after 旁白中）"""
        if context_after:
            after_narr = self._extract_narration('', '', context_after)
            if after_narr:
                descriptive_roles = self.role_extractor.extract(after_narr)
            else:
                descriptive_roles = []
            for role in descriptive_roles:
                if role not in seen_names:
                    char = self._match_candidate_to_character(role, after_narr, skip_speech_check=True, require_library=False)
                    if char:
                        candidates.append((char.name, '描述性角色(后)', 0.75))
                        seen_names.add(role)

    def _strategy_context_characters(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """方向1：语境角色优先（H-20260516-10: 改用 get_eligible_characters 过滤临时角色）"""
        if context_before and not candidates:
            nearby_window = context_before[-120:]
            all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
            sorted_chars = sorted(all_chars, key=lambda c: -len(c.name))
            for char in sorted_chars:
                if char.name in nearby_window and char.name not in seen_names:
                    pos = nearby_window.rindex(char.name)
                    distance = len(nearby_window) - pos
                    proximity_bonus = max(0.10 - 0.005 * distance, 0.0)
                    after_name = nearby_window[pos + len(char.name):pos + len(char.name) + 15]
                    speech_verbs = {'道', '说', '问', '答', '笑道', '说道', '问道', '答道',
                                    '冷喝', '喝道', '冷笑', '叹道', '怒道', '斥道', '叫道', '喊道'}
                    has_speech = any(v in after_name for v in speech_verbs)
                    confidence = min(0.75 + proximity_bonus + (0.10 if has_speech else 0), 0.90)
                    candidates.insert(0, (char.name,
                        '语境角色优先({})'.format('说话动词' if has_speech else '临近'),
                        confidence))
                    seen_names.add(char.name)

    def _strategy_dynamic_candidates(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """方向3：动态候选（角色库精确匹配 + 别名匹配）

        H-20260516-10: 改用 get_eligible_characters
        """
        if not candidates and (context_before or context_after):
            merged = self._extract_narration('', context_before or '', context_after or '')
            if merged:
                all_chars = sorted(
                    self.char_manager.get_eligible_characters(self._current_project_id),
                    key=lambda c: -len(c.name)
                )
                for char in all_chars:
                    if char.name in merged:
                        candidates.append((char.name, '动态候选(角色库)', 0.72))
                    else:
                        for alias in char.aliases:
                            if alias in merged:
                                candidates.append((char.name, '动态候选(别名:{})'.format(alias), 0.70))
                                break

    def _strategy_fallback(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """兜底步骤：在角色库中匹配旁白内容

        用于处理"掌柜抬头看了看他，笑道"等场景，其中身份词提取失败但角色库中有该角色
        注意：优先匹配 context_before 中的角色，避免 context_after 中的角色干扰
        H-20260515-05 + 方向2(H-20260515-08): 话动特征强化
        方向2改动：扩大说话动词列表 + 扩大窗口至20字 + 提高置信度至0.78
        """
        if not candidates or (len(candidates) <= SPEAKER_MATCHER_INSUFFICIENT_CANDIDATES_MAX_COUNT and all(c[2] < SPEAKER_MATCHER_INSUFFICIENT_CANDIDATES_MAX_CONF for c in candidates)):
            if context_before:
                before_narration = self._extract_narration('', context_before, '')
                if before_narration:
                    speech_verbs = ['道', '说', '问', '答', '笑道', '说道', '问道', '答道',
                                    '冷喝', '喝道', '冷笑', '叹道', '怒道', '斥道', '叫道', '喊道',
                                    '笑问', '笑骂', '嗔道', '应道', '叹息', '沉吟']
                    action_verbs = ['端起', '翻开', '打开', '站起身', '皱起', '走到', '看向',
                                    '扫了', '看了看', '点头', '摇头', '坐下', '合上', '放下',
                                    '接过', '转身', '摆了摆', '喝了口', '揉了揉', '掏出']

                    all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
                    for char in all_chars:
                        if char.name in before_narration:
                            idx = before_narration.index(char.name)
                            after_name = before_narration[idx + len(char.name):idx + len(char.name) + 20]
                            has_speech = any(v in after_name for v in speech_verbs)
                            has_action = any(v in after_name for v in action_verbs)

                            if has_speech:
                                candidates.insert(0, (char.name, '角色库旁白匹配(前)(说话)', 0.78))
                            elif has_action:
                                candidates.append((char.name, '角色库旁白匹配(前)(动作)', 0.55))
                            else:
                                candidates.insert(0, (char.name, '角色库旁白匹配(前)', 0.70))
            if not candidates or (len(candidates) <= 2 and all(c[2] < 0.75 for c in candidates)):
                narration = self._extract_narration('', context_before, context_after)
                if narration:
                    char_match = self._match_from_character_library(narration)
                    if char_match:
                        candidates.insert(0, (char_match.name, '角色库旁白匹配', 0.70))

    def _strategy_srl_arg0(
        self, text: str, context_before: str, context_after: str,
        prefix_narration: str, candidates: List, seen_names: set
    ) -> None:
        """SRL ARG0 候选信号层（2026-05-23 新增）

        从 context_before 中提取 SRL ARG0（语义主语），按距离衰减加权
        """
        if context_before:
            srl_sentences = re.split(r'(?<=[。！？；\n])', context_before)
            srl_sentences = [s.strip() for s in srl_sentences if s.strip()]
            for sent_idx, sent in enumerate(srl_sentences):
                srl_arg0s = extract_srl_arg0s(sent)
                if not srl_arg0s:
                    continue
                distance = len(srl_sentences) - 1 - sent_idx
                if distance == 0:
                    srl_conf = 0.90
                elif distance == 1:
                    srl_conf = 0.80
                else:
                    srl_conf = 0.65
                for arg0 in srl_arg0s:
                    normalized = _normalize_srl_arg0(arg0)
                    if not normalized or normalized in seen_names:
                        continue
                    char = self._match_candidate_to_character(
                        normalized, context_before, require_library=True
                    )
                    if char:
                        candidates.append((char.name, f'SRL-ARG0(d={distance})', srl_conf))
                        seen_names.add(normalized)

    # ------------------------------------------------------------------ #
    # 后处理方法
    # ------------------------------------------------------------------ #

    def _apply_action_subject_boost(
        self, candidates: List[Tuple[str, str, float]], context_before: str
    ) -> List[Tuple[str, str, float]]:
        """N-2: 动作主语优先

        语言学依据：中文旁白中"角色名+动词"结构的主语通常是动作发出者
        来源：通用句法规则，非静态词表
        边界：只识别角色库中的角色名+动词结构
        """
        if context_before and candidates:
            action_subject = self._extract_action_subject(context_before)
            if action_subject and action_subject in [c[0] for c in candidates]:
                # 提升动作主语的置信度
                enhanced = []
                for name, reason, confidence in candidates:
                    if name == action_subject:
                        confidence = min(confidence + 0.10, 0.95)
                        reason = f'{reason}(动作主语)'
                    enhanced.append((name, reason, confidence))
                enhanced.sort(key=lambda x: -x[2])
                return enhanced
        return candidates

    def _apply_recency_decay(
        self, candidates: List[Tuple[str, str, float]]
    ) -> List[Tuple[str, str, float]]:
        """P2-2: 近因衰减（反粘着机制）

        v7.0 长文本基线显示：连续对话中最近说话人被过度优先
        原理：对话通常是轮流进行的，刚说完的人不应立即再次说话
        衰减梯度：越近的角色获得越多的负分
        """
        from utils.config import RECENCY_DECAY_RECENT, RECENCY_DECAY_SECOND, RECENCY_DECAY_OTHER

        if candidates and self._recent_speakers:
            recent_rank = {}
            for i, name in enumerate(reversed(self._recent_speakers[-5:])):
                recent_rank[name] = len(self._recent_speakers[-5:]) - i  # 最近=5, 次近=4, ...

            decayed = []
            for name, reason, confidence in candidates:
                if name in recent_rank:
                    rank = recent_rank[name]
                    # 衰减量：最近的 -RECENCY_DECAY_RECENT，次近 -RECENCY_DECAY_SECOND，其余 -RECENCY_DECAY_OTHER
                    if rank == len(self._recent_speakers[-5:]):
                        decay = RECENCY_DECAY_RECENT
                    elif rank == len(self._recent_speakers[-5:]) - 1:
                        decay = RECENCY_DECAY_SECOND
                    else:
                        decay = RECENCY_DECAY_OTHER
                    confidence = max(confidence - decay, 0.20)
                    reason = f'{reason}(近因衰减-r{rank})'
                decayed.append((name, reason, confidence))
            decayed.sort(key=lambda x: -x[2])
            return decayed
        return candidates
