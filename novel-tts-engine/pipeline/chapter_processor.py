# -*- coding: utf-8 -*-
"""章节处理器：专门负责章节级别的数据处理（NER、实体过滤、说话人匹配、情绪标注）"""

import logging
import re
from typing import List, Dict, Optional

from pipeline.chapter_splitter import Chapter
from pipeline.nlp_basics import NLPBasics, Entity
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.entity_linker import EntityLinker
from pipeline.character_manager import CharacterManager
from pipeline.legacy_rule_matcher import AbstractSpeakerMatcher
from pipeline.emotion_extractor import get_emotion_extractor
from pipeline.pipeline_runner import (
    ChapterResult, SentenceData, FragmentData, _is_chinese_char,
)
from utils.text_utils import split_sentences_smart
from utils.config import (
    EMOTION_EXTRACT_WINDOW, NARRATION_EMOTION_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


class ChapterProcessor:
    """章节处理器：专门负责章节级别的数据处理"""

    def __init__(
        self,
        nlp: NLPBasics,
        char_manager: CharacterManager,
        context_validator: ContextDiversityValidator,
        speaker_role_filter: SpeakerRoleFilter,
        entity_linker: EntityLinker,
        speaker_matcher: AbstractSpeakerMatcher,
    ):
        self.nlp = nlp
        self.char_manager = char_manager
        self.context_validator = context_validator
        self.speaker_role_filter = speaker_role_filter
        self.entity_linker = entity_linker
        self.speaker_matcher = speaker_matcher

    def process(
        self,
        chapter: Chapter,
        chapter_id: int,
        project_id: str,
        progress_updater=None,
    ) -> ChapterResult:
        """
        处理单个章节的完整流程。

        Args:
            chapter: 章节对象
            chapter_id: 章节ID
            project_id: 项目ID（用于角色关联）
            progress_updater: 可选的进度更新回调 (step, chapter, total, idx, msg)

        Returns:
            ChapterResult 章节处理结果
        """
        self._update_progress(progress_updater, "章节初始化", chapter_id, chapter_id + 1, 1, "正在初始化...")

        result = ChapterResult(
            chapter_id=chapter_id,
            title=chapter.title,
            volume=chapter.volume_index,
        )

        content = chapter.content
        if not content.strip():
            return result

        self._update_progress(progress_updater, "NER", chapter_id, chapter_id + 1, 2, "正在识别实体...")
        entities = self._extract_entities(content)

        self._update_progress(progress_updater, "实体验证", chapter_id, chapter_id + 1, 2, "正在验证实体...")
        entities = self._validate_entities(entities, content)

        self._update_progress(progress_updater, "角色过滤", chapter_id, chapter_id + 1, 2, "正在过滤说话角色...")
        entities = self._filter_speaker_roles(entities, content)

        self._update_progress(progress_updater, "实体链接", chapter_id, chapter_id + 1, 3, "正在链接实体...")
        linked_entities = self.entity_linker.link(entities, content)

        self._update_progress(progress_updater, "说话人匹配", chapter_id, chapter_id + 1, 5, "正在匹配说话人...")
        dialogue_map = self._match_speakers(content, chapter_id, project_id)

        self._update_progress(progress_updater, "情绪标注", chapter_id, chapter_id + 1, 6, "正在标注情绪...")
        sentences_data = self._annotate_sentences(content, linked_entities, dialogue_map)

        result.sentences = sentences_data
        result.statistics = self._calculate_statistics(sentences_data, linked_entities)

        return result

    def _extract_entities(self, content: str) -> List[Entity]:
        """NER 分析"""
        nlp_result = self.nlp.analyze(content)
        return list(nlp_result.entities)

    def _validate_entities(self, entities: List[Entity], content: str) -> List[Entity]:
        """上下文多样性验证"""
        return self.context_validator.validate(entities, content)

    def _filter_speaker_roles(self, entities: List[Entity], content: str) -> List[Entity]:
        """说话角色过滤"""
        return self.speaker_role_filter.filter(entities, content, self.nlp)

    def _match_speakers(
        self,
        content: str,
        chapter_id: int,
        project_id: str,
    ) -> Dict[str, str]:
        """
        说话人匹配，构建对话文本到说话人名称的映射。
        """
        self.speaker_matcher.current_project_id = project_id

        dialogue_results = self.speaker_matcher.analyze_dialogue(content, chapter_id=chapter_id)

        dialogue_map: Dict[str, str] = {}
        for dialogue_text, speaker in dialogue_results:
            if speaker:
                self.char_manager.find_or_create(speaker.name, project_id=project_id)
            dialogue_map[dialogue_text.strip()] = speaker.name if speaker else ""

        return dialogue_map

    def _annotate_sentences(
        self,
        content: str,
        linked_entities: List[Entity],
        dialogue_map: Dict[str, str],
    ) -> List[SentenceData]:
        """
        情绪标注和句子处理。
        """
        sentences = split_sentences_smart(content)

        dialogue_texts = {d.strip() for d in dialogue_map.keys()}

        sentence_data_list = []
        prev_emotion = None
        prev_confidence = 0.0

        for sentence in sentences:
            sentence_data = self._process_single_sentence(
                sentence, content, linked_entities, dialogue_map,
                dialogue_texts, prev_emotion, prev_confidence,
            )
            sentence_data_list.append(sentence_data)
            prev_emotion = sentence_data.emotion
            prev_confidence = sentence_data.emotion_confidence if hasattr(sentence_data, 'emotion_confidence') else 0.0

        return sentence_data_list

    def _process_single_sentence(
        self,
        sentence: str,
        content: str,
        linked_entities: List[Entity],
        dialogue_map: Dict[str, str],
        dialogue_texts: set,
        prev_emotion: Optional[str],
        prev_confidence: float,
    ) -> SentenceData:
        """处理单个句子，返回 SentenceData"""
        sentence_start = content.find(sentence)
        if sentence_start == -1:
            sentence_start = 0
        sentence_end = sentence_start + len(sentence)

        is_dialogue = any(d_text in sentence for d_text in dialogue_texts)
        sentence_type = "dialogue" if is_dialogue else "narration"

        emotion_extractor = get_emotion_extractor()
        emotion_window_start = max(0, sentence_start - EMOTION_EXTRACT_WINDOW)
        emotion_window_end = min(len(content), sentence_end + EMOTION_EXTRACT_WINDOW)
        emotion_context = content[emotion_window_start:emotion_window_end]
        emotion_result = emotion_extractor.classify(
            emotion_context, context_hint=prev_emotion, context_confidence=prev_confidence
        )

        speaker = ""
        emotion = emotion_result.emotion_label

        if is_dialogue:
            for d_text, d_speaker in dialogue_map.items():
                if d_text in sentence:
                    speaker = d_speaker
                    break
        else:
            if emotion_result.confidence >= NARRATION_EMOTION_CONFIDENCE_THRESHOLD:
                emotion = emotion_result.emotion_label

        sentence_entities = self._link_entities_to_sentence(sentence, linked_entities)
        fragments = self._extract_fragments(sentence, dialogue_map)

        sentence_data = SentenceData(
            text=sentence,
            type=sentence_type,
            speaker=speaker,
            emotion=emotion,
            emotion_class=emotion_result.emotion_class,
            emotion_vector=emotion_result.emotion_vector,
            entities=sentence_entities,
            fragments=fragments,
        )

        sentence_data.emotion_confidence = emotion_result.confidence

        return sentence_data

    def _link_entities_to_sentence(
        self,
        sentence: str,
        linked_entities: List[Entity],
    ) -> List[dict]:
        """实体关联到句子"""
        sentence_entities = []
        for e in linked_entities:
            e_start = e.start
            e_end = e.end
            e_text = e.text
            e_type = e.type
            e_conf = e.confidence
            e_standard = getattr(e, 'standard_name', '')
            e_is_linked = getattr(e, 'is_linked', False)

            if self._entity_in_sentence(e_text, e_start, e_end, sentence):
                entity_dict = {
                    "text": e_text,
                    "type": e_type,
                    "confidence": e_conf,
                    "start": e_start,
                    "end": e_end,
                }
                if e_standard:
                    entity_dict["standard_name"] = e_standard
                entity_dict["is_linked"] = e_is_linked
                sentence_entities.append(entity_dict)

        return sentence_entities

    @staticmethod
    def _entity_in_sentence(entity_text: str, entity_start: int, entity_end: int, sentence: str) -> bool:
        """判断实体是否存在于句子中"""
        if not entity_text or not sentence:
            return False

        if entity_text == sentence:
            return True

        if len(entity_text) == 1:
            pattern = re.compile(re.escape(entity_text))
            for match in pattern.finditer(sentence):
                left_ok = (match.start() == 0 or
                           not _is_chinese_char(sentence[match.start() - 1]))
                right_ok = (match.end() == len(sentence) or
                            not _is_chinese_char(sentence[match.end()]))
                if left_ok and right_ok:
                    return True
            return False

        return entity_text in sentence

    @staticmethod
    def _extract_fragments(sentence: str, dialogue_map: Dict[str, str]) -> List[FragmentData]:
        """将句子拆分为 fragments（对话/旁白片段）"""
        if not sentence:
            return []

        quote_patterns = [
            ('「', '」'),
            ('"', '"'),
            ('\u201c', '\u201d'),
            ('『', '』'),
        ]

        dialogue_positions = []

        for open_q, close_q in quote_patterns:
            start = 0
            while True:
                open_pos = sentence.find(open_q, start)
                if open_pos == -1:
                    break

                if open_q == close_q:
                    depth = 1
                    pos = open_pos + 1
                    while pos < len(sentence) and depth > 0:
                        if sentence[pos] == '\\' and pos + 1 < len(sentence):
                            pos += 2
                            continue
                        if sentence[pos] == close_q:
                            depth -= 1
                            if depth == 0:
                                close_pos = pos
                                break
                        pos += 1
                    else:
                        break
                else:
                    close_pos = sentence.find(close_q, open_pos + 1)
                    if close_pos == -1:
                        break

                dialogue_text = sentence[open_pos:close_pos + 1]
                speaker = ""
                for d_text, d_speaker in dialogue_map.items():
                    if d_text in dialogue_text:
                        speaker = d_speaker
                        break
                dialogue_positions.append((open_pos, close_pos + 1, dialogue_text, speaker))
                start = close_pos + 1

        if not dialogue_positions:
            return [FragmentData(text=sentence, type="narration", speaker="")]

        dialogue_positions.sort(key=lambda x: x[0])

        fragments = []
        pos = 0

        for d_start, d_end, d_text, d_speaker in dialogue_positions:
            if d_start > pos:
                narration_text = sentence[pos:d_start].strip()
                if narration_text:
                    fragments.append(FragmentData(text=narration_text, type="narration", speaker=""))
            fragments.append(FragmentData(text=d_text, type="dialogue", speaker=d_speaker))
            pos = d_end

        if pos < len(sentence):
            narration_text = sentence[pos:].strip()
            if narration_text:
                fragments.append(FragmentData(text=narration_text, type="narration", speaker=""))

        return fragments if len(fragments) > 1 else [FragmentData(text=sentence, type="narration", speaker="")]

    def _calculate_statistics(
        self,
        sentences_data: List[SentenceData],
        linked_entities: List[Entity],
    ) -> dict:
        """计算统计信息"""
        dialogue_count = sum(1 for s in sentences_data if s.type == "dialogue")
        narration_count = sum(1 for s in sentences_data if s.type == "narration")

        return {
            "total_sentences": len(sentences_data),
            "dialogue_count": dialogue_count,
            "narration_count": narration_count,
            "entity_count": len(linked_entities),
        }

    @staticmethod
    def _update_progress(
        callback,
        step: str,
        chapter: int,
        total: int,
        step_idx: int,
        message: str = "",
    ):
        """调用进度更新回调（如果提供）"""
        if callback:
            callback(step, chapter, total, step_idx, message)
