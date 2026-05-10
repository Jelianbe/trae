# -*- coding: utf-8 -*-
"""流水线调度器：串联所有处理模块，暴露统一的分析接口"""

import json
import logging
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from pipeline.chapter_splitter import ChapterSplitter, Chapter
from pipeline.nlp_basics import get_nlp, NLPBasics
from pipeline.context_diversity_validator import get_context_validator, ContextDiversityValidator
from pipeline.speaker_role_filter import get_speaker_role_filter, SpeakerRoleFilter
from pipeline.entity_linker import get_entity_linker, EntityLinker
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.semantic_ranker import get_semantic_ranker, SemanticRanker
from pipeline.emotion_extractor import get_emotion_extractor  # 统一情绪管道
from utils.text_utils import split_sentences_smart

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"


from utils.config import (
    COLD_START_CHARS_THRESHOLD, MAX_INPUT_CHARS, MAX_RESULT_CACHE_SIZE,
    EMOTION_EXTRACT_WINDOW, DIALOGUE_EMOTION_CONFIDENCE_THRESHOLD,
    NARRATION_EMOTION_CONFIDENCE_THRESHOLD, EMOTION_LOW_SCORE_THRESHOLD,
    CONTEXT_HINT_CONFIDENCE_THRESHOLD,
)

@dataclass
class ProgressInfo:
    """进度信息"""
    current_step: str = ""
    current_chapter: int = 0
    total_chapters: int = 0
    total_steps: int = 6
    current_step_index: int = 0
    state: PipelineState = PipelineState.IDLE
    message: str = ""
    
    @property
    def progress_percent(self) -> float:
        if self.total_chapters == 0:
            return 0.0
        chapter_progress = self.current_chapter / self.total_chapters
        step_weight = 1.0 / self.total_steps
        return (self.current_step_index + chapter_progress) * step_weight * 100


@dataclass
class FragmentData:
    """句子片段数据（对话/旁白/拟声）"""
    text: str
    type: str  # "dialogue" / "narration" / "onomatopoeia"
    speaker: str = ""


@dataclass
class SentenceData:
    """单句处理结果（MVP 7字段）"""
    text: str
    type: str  # "dialogue" / "narration"
    speaker: str
    emotion: str
    emotion_class: str
    emotion_vector: Optional[List[float]]
    entities: List[dict] = field(default_factory=list)
    fragments: List[FragmentData] = field(default_factory=list)


@dataclass
class ChapterResult:
    """章节处理结果"""
    chapter_id: int = 0
    title: str = ""
    volume: int = 0
    sentences: List[SentenceData] = field(default_factory=list)
    statistics: dict = field(default_factory=dict)


class PipelineRunner:
    """
    流水线调度器：串联所有处理模块。

    管道流程：
    1. 章节划分
    2. NER 分析 + 上下文多样性验证 + 说话角色过滤 + 实体链接
    3. 说话人匹配
    4. 情绪标注

    注：拟声词检测、实体聚类、引号分类已移入战略储备库，暂不启用。
    """
    
    def __init__(self):
        self.chapter_splitter = ChapterSplitter()
        self.nlp = get_nlp()
        self.char_manager = get_character_manager()
        self.speaker_matcher = SpeakerMatcher(self.char_manager)
        self.semantic_ranker = get_semantic_ranker()
        self.context_validator = get_context_validator()
        self.speaker_role_filter = get_speaker_role_filter()
        self.entity_linker = get_entity_linker(self.char_manager)
        
        self.progress = ProgressInfo()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._result_cache: "OrderedDict[str, List[ChapterResult]]" = OrderedDict()
        
        self._total_processed_chars = 0
        self._cold_start_done = False
    
    def _add_to_cache(self, key: str, value: List["ChapterResult"]):
        """添加结果到缓存，超过容量时淘汰最旧的"""
        if key in self._result_cache:
            del self._result_cache[key]
        self._result_cache[key] = value
        while len(self._result_cache) > MAX_RESULT_CACHE_SIZE:
            self._result_cache.popitem(last=False)
    
    def _set_progress(self, step: str, chapter: int, total: int, step_idx: int, message: str = ""):
        """更新进度信息"""
        self.progress.current_step = step
        self.progress.current_chapter = chapter
        self.progress.total_chapters = total
        self.progress.current_step_index = step_idx
        self.progress.message = message
    
    def pause(self):
        """暂停流水线"""
        self.progress.state = PipelineState.PAUSED
        self._pause_event.clear()
        logger.info("流水线已暂停")
    
    def resume(self):
        """恢复流水线"""
        self.progress.state = PipelineState.RUNNING
        self._pause_event.set()
        logger.info("流水线已恢复")
    
    def get_progress(self) -> ProgressInfo:
        """获取当前进度"""
        return self.progress
    
    def analyze_chapters(
        self,
        text: str,
        start: int = 0,
        end: int = -1,
        force: bool = False,
        cache_key: str = "default",
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> List[ChapterResult]:
        """
        分析章节的完整流程。
        
        Args:
            text: 完整小说文本
            start: 起始章节索引（0-based）
            end: 结束章节索引（-1 表示到最后）
            force: 是否强制重新分析（忽略缓存）
            cache_key: 缓存键
            progress_callback: 进度回调函数
        
        Returns:
            章节结果列表
        """
        # 输入验证
        if not text:
            raise ValueError("输入文本不能为空")
        
        if len(text) > MAX_INPUT_CHARS:
            raise ValueError(
                f"输入文本过长（{len(text)} 字符），"
                f"超过最大限制 {MAX_INPUT_CHARS} 字符（{MAX_INPUT_CHARS // (1024*1024)}MB）"
            )
        
        if not force and cache_key in self._result_cache:
            logger.info(f"使用缓存结果 (cache_key={cache_key})")
            self._result_cache.move_to_end(cache_key)
            return self._result_cache[cache_key]
        
        self.progress.state = PipelineState.RUNNING
        self._pause_event.set()
        
        results = []
        self._total_processed_chars = 0
        self._cold_start_done = False
        self._full_text = text
        
        try:
            # 第一步：章节划分
            self._set_progress("章节划分", 0, 0, 0, "正在分章...")
            self._notify_progress(progress_callback)
            
            chapters = self.chapter_splitter.split(text)
            if end == -1:
                end = len(chapters)
            
            chapters = chapters[start:end]
            total_chapters = len(chapters)
            
            logger.info(f"共识别到 {total_chapters} 个章节（范围 {start}-{end}）")
            
            # 第二步~第六步：逐章处理
            for i, chapter in enumerate(chapters):
                self._check_pause()
                
                self._set_progress("处理中", i + 1, total_chapters, 1, f"正在处理第 {i+1} 章...")
                self._notify_progress(progress_callback)
                
                chapter_result = self._process_chapter(chapter, i + start)
                results.append(chapter_result)
                
                # 冷启动检查：累积字数达到阈值时执行批量聚类
                self._total_processed_chars += len(chapter.content)
                if not self._cold_start_done and self._total_processed_chars >= COLD_START_CHARS_THRESHOLD:
                    self._trigger_cold_start()
            
            # 缓存结果
            self._add_to_cache(cache_key, results)
            
            self.progress.state = PipelineState.DONE
            self._set_progress("完成", total_chapters, total_chapters, 6, "分析完成")
            self._notify_progress(progress_callback)
            
            logger.info(f"流水线完成：{total_chapters} 个章节")
            
        except Exception as e:
            self.progress.state = PipelineState.ERROR
            self.progress.message = str(e)
            logger.error(f"流水线执行错误: {e}", exc_info=True)
            raise
        finally:
            self.speaker_matcher.reset_activity()
        
        return results
    
    def _process_chapter(self, chapter: 'Chapter', chapter_id: int) -> ChapterResult:
        """处理单个章节"""
        result = ChapterResult(
            chapter_id=chapter_id,
            title=chapter.title,
            volume=chapter.volume_index,
        )
        
        content = chapter.content
        if not content.strip():
            return result

        # 第二步：NER 分析
        self._set_progress("NER", result.chapter_id, result.chapter_id + 1, 2, "正在识别实体...")
        nlp_result = self.nlp.analyze(content)
        entities = list(nlp_result.entities)

        # 新增步骤2.1: 上下文多样性验证
        self._set_progress("实体验证", result.chapter_id, result.chapter_id + 1, 2, "正在验证实体...")
        entities = self.context_validator.validate(entities, content)

        # 新增步骤2.2: 说话角色过滤
        self._set_progress("角色过滤", result.chapter_id, result.chapter_id + 1, 2, "正在过滤说话角色...")
        entities = self.speaker_role_filter.filter(entities, content, self.nlp)

        # 第三步：实体链接
        self._set_progress("实体链接", result.chapter_id, result.chapter_id + 1, 3, "正在链接实体...")
        linked_entities = self.entity_linker.link(entities, content)
        
        # 第五步：说话人匹配
        self._set_progress("说话人匹配", result.chapter_id, result.chapter_id + 1, 5, "正在匹配说话人...")
        
        # 设置 project_id 到 speaker_matcher，使角色创建时关联到当前项目
        project_id = getattr(self, '_current_project_id', '')
        self.speaker_matcher._current_project_id = project_id
        
        dialogue_results = self.speaker_matcher.analyze_dialogue(content, chapter_id=chapter_id)
        
        # 构建对话映射（使用 project_id 关联角色）
        dialogue_map: Dict[str, str] = {}
        for dialogue_text, speaker in dialogue_results:
            # 确保角色已创建并关联到当前项目
            if speaker:
                self.char_manager.find_or_create(speaker.name, project_id=project_id)
            dialogue_map[dialogue_text.strip()] = speaker.name if speaker else ""
        
        # 第六步：情绪标注
        self._set_progress("情绪标注", result.chapter_id, result.chapter_id + 1, 6, "正在标注情绪...")
        
        # 使用智能句子分割（保护引号内内容不被拆分）
        sentences = split_sentences_smart(content)
        
        # 优化1：预构建对话文本集合（O(1) 查找替代 any() 遍历）
        dialogue_texts = {d.strip() for d in dialogue_map.keys()}
        
        sentence_id = 0
        dialogue_count = 0
        narration_count = 0
        current_pos = 0  # 跟踪当前在原文中的位置
        prev_emotion = None  # 上下文情感传递：上一句的情绪标签
        prev_confidence = 0.0  # 上下文情感传递：上一句的情绪置信度
        
        for sentence in sentences:
            sentence_id += 1
            
            # 查找句子在原文中的位置
            sentence_start = content.find(sentence, current_pos)
            if sentence_start == -1:
                sentence_start = current_pos  # 如果找不到，使用当前位置
            sentence_end = sentence_start + len(sentence)
            current_pos = sentence_end  # 更新位置
            
            # 优化3：使用预构建集合进行对话检测（避免重复遍历）
            is_dialogue = False
            for d_text in dialogue_texts:
                if d_text in sentence:
                    is_dialogue = True
                    break
            
            sentence_type = "dialogue" if is_dialogue else "narration"
            speaker = ""
            emotion = "neutral"
            
            # 管道2（情绪）：从原始文本窗口提取情绪特征（方案B 双管道并行）
            # 方案B 核心思想：情绪信号存在于原始文本中，不应等角色匹配完再标注
            # 取句子前后 EMOTION_EXTRACT_WINDOW 字上下文作为情绪提取窗口
            emotion_extractor = get_emotion_extractor()
            emotion_window_start = max(0, sentence_start - EMOTION_EXTRACT_WINDOW)
            emotion_window_end = min(len(content), sentence_end + EMOTION_EXTRACT_WINDOW)
            emotion_context = content[emotion_window_start:emotion_window_end]
            emotion_result = emotion_extractor.classify(emotion_context, context_hint=prev_emotion, context_confidence=prev_confidence)
            
            # 从 EmotionResult 提取各层标注
            emotion = emotion_result.emotion_label
            emotion_class = emotion_result.emotion_class
            emotion_vector = emotion_result.emotion_vector
            emotion_text = emotion_result.emotion_text
            emotion_intensity = emotion_result.intensity
            emotion_conf = emotion_result.confidence
            
            if is_dialogue:
                for d_text, d_speaker in dialogue_map.items():
                    if d_text in sentence:
                        speaker = d_speaker
                        emotion = emotion_result.emotion_label
                        dialogue_count += 1
                        break
            else:
                narration_count += 1
                if emotion_conf >= NARRATION_EMOTION_CONFIDENCE_THRESHOLD:
                    emotion = emotion_result.emotion_label
            
            # 预构建实体属性字典
            sentence_entities = []
            for e in linked_entities:
                # 直接属性访问替代 getattr
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
                        # 新增：存储实体在原文中的绝对位置
                        "start": e_start,
                        "end": e_end,
                    }
                    if e_standard:
                        entity_dict["standard_name"] = e_standard
                    entity_dict["is_linked"] = e_is_linked
                    sentence_entities.append(entity_dict)
            
            # 提取 fragments（对话/旁白拆分）
            fragments = PipelineRunner._extract_fragments(sentence, dialogue_map)
            
            result.sentences.append(SentenceData(
                text=sentence,
                type=sentence_type,
                speaker=speaker,
                emotion=emotion,
                emotion_class=emotion_class,
                emotion_vector=emotion_vector,
                entities=sentence_entities,
                fragments=fragments,
            ))
            
            # 更新上下文情感传递
            prev_emotion = emotion
            prev_confidence = emotion_conf
        
        result.statistics = {
            "total_sentences": sentence_id,
            "dialogue_count": dialogue_count,
            "narration_count": narration_count,
            "entity_count": len(linked_entities),
        }
        
        return result
    
    def _trigger_cold_start(self):
        """
        冷启动触发逻辑：当累积字数达到阈值时，执行批量聚类。
        
        注意：entity_clusterer 已移入战略储备库，冷启动聚类功能暂不启用。
        仅回填未知说话人。
        """
        if self._cold_start_done:
            return
        
        logger.info(f"冷启动触发：已处理 {self._total_processed_chars} 字，达到阈值 {COLD_START_CHARS_THRESHOLD}")
        
        try:
            backfill_count = 0
            for result in self._result_cache.get("default", []):
                count = self.speaker_matcher.backfill_unknown_speakers(result.sentences)
                backfill_count += count
            
            self._cold_start_done = True
            logger.info(f"冷启动完成：回填 {backfill_count} 个未知说话人")
        except Exception as e:
            logger.error(f"冷启动处理失败: {e}", exc_info=True)
    
    def _check_pause(self):
        """检查是否暂停"""
        self._pause_event.wait()

    @staticmethod
    def _extract_fragments(sentence: str, dialogue_map: Dict[str, str]) -> List[FragmentData]:
        """
        将句子拆分为 fragments（对话/旁白片段）。

        核心逻辑：
        - 识别句子中所有引号内的对话文本
        - 按原文顺序交替提取旁白和对话片段
        - 每个 fragment 标记类型和说话人

        Args:
            sentence: 完整句子文本
            dialogue_map: 对话文本到说话人的映射

        Returns:
            FragmentData 列表
        """
        if not sentence:
            return []

        # 对话引号模式：「...」、"..."、"..."、『...』
        quote_patterns = [
            ('「', '」'),
            ('"', '"'),
            ('\u201c', '\u201d'),
            ('『', '』'),
        ]

        # 收集所有引号内的对话片段及其位置
        dialogue_positions = []  # [(start, end, text, speaker)]

        for open_q, close_q in quote_patterns:
            start = 0
            while True:
                open_pos = sentence.find(open_q, start)
                if open_pos == -1:
                    break
                close_pos = sentence.find(close_q, open_pos + 1)
                if close_pos == -1:
                    break
                dialogue_text = sentence[open_pos:close_pos + 1]
                # 查找匹配的说话人
                speaker = ""
                for d_text, d_speaker in dialogue_map.items():
                    if d_text in dialogue_text:
                        speaker = d_speaker
                        break
                dialogue_positions.append((open_pos, close_pos + 1, dialogue_text, speaker))
                start = close_pos + 1

        # 如果没有对话，整个句子就是单个旁白 fragment
        if not dialogue_positions:
            return [FragmentData(text=sentence, type="narration", speaker="")]

        # 按位置排序
        dialogue_positions.sort(key=lambda x: x[0])

        # 交替提取旁白和对话片段
        fragments = []
        pos = 0

        for d_start, d_end, d_text, d_speaker in dialogue_positions:
            # 提取对话前的旁白
            if d_start > pos:
                narration_text = sentence[pos:d_start].strip()
                if narration_text:
                    fragments.append(FragmentData(text=narration_text, type="narration", speaker=""))
            # 提取对话
            fragments.append(FragmentData(text=d_text, type="dialogue", speaker=d_speaker))
            pos = d_end

        # 提取最后的旁白
        if pos < len(sentence):
            narration_text = sentence[pos:].strip()
            if narration_text:
                fragments.append(FragmentData(text=narration_text, type="narration", speaker=""))

        # 如果只有一个 fragment，返回它
        # 如果有多个 fragments，返回完整列表
        return fragments if len(fragments) > 1 else [FragmentData(text=sentence, type="narration", speaker="")]

    @staticmethod
    def _entity_in_sentence(entity_text: str, entity_start: int, entity_end: int, sentence: str) -> bool:
        """
        判断实体是否存在于句子中，使用精确边界匹配避免部分匹配问题。

        核心逻辑：
        - 对于单字实体（如 "林"），检查前后是否有其他中文字符（避免匹配到 "树林"）。
        - 对于多字实体（如 "苏夜"），只要文本精确出现即可。

        Args:
            entity_text: 实体文本
            entity_start: 实体在原文中的起始位置
            entity_end: 实体在原文中的结束位置
            sentence: 当前句子文本

        Returns:
            True 如果实体精确存在于句子中
        """
        if not entity_text or not sentence:
            return False

        # 策略1: 如果实体文本完全等于句子，直接返回 True
        if entity_text == sentence:
            return True

        # 策略2: 精确文本匹配
        # 对于单字实体，需要额外检查边界（避免匹配到更长词的一部分）
        if len(entity_text) == 1:
            pattern = re.compile(re.escape(entity_text))
            for match in pattern.finditer(sentence):
                # 检查左边界
                left_ok = (match.start() == 0 or
                           not _is_chinese_char(sentence[match.start() - 1]))
                # 检查右边界
                right_ok = (match.end() == len(sentence) or
                            not _is_chinese_char(sentence[match.end()]))
                if left_ok and right_ok:
                    return True
            return False

        # 多字实体：只要文本在句子中精确出现即可
        return entity_text in sentence
    
    def _notify_progress(self, callback: Optional[Callable]):
        """通知进度更新"""
        if callback:
            callback(self.progress)
    
    def export_json(self, results: List[ChapterResult], pretty: bool = True) -> str:
        """导出为 JSON 格式"""
        data = []
        for chapter in results:
            chapter_dict = {
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "volume": chapter.volume,
                "statistics": chapter.statistics,
                "sentences": [
                    {
                        "text": s.text,
                        "type": s.type,
                        "speaker": s.speaker,
                        "emotion": s.emotion,
                        "emotion_class": s.emotion_class,
                        "emotion_vector": s.emotion_vector,
                        "entities": s.entities,
                    }
                    for s in chapter.sentences
                ],
            }
            data.append(chapter_dict)
        
        return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    
    def export_ssml(self, results: List[ChapterResult]) -> str:
        """导出为 SSML 格式（MVP 简化版）"""
        ssml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<speak version="1.0">']
        
        for chapter in results:
            ssml_parts.append(f'<p><!-- 第{chapter.chapter_id}章 {chapter.title} -->')
            
            for sentence in chapter.sentences:
                ssml_parts.append(f'  <s>{sentence.text}</s>')
            
            ssml_parts.append('</p>')
        
        ssml_parts.append('</speak>')
        return '\n'.join(ssml_parts)


def _is_chinese_char(char: str) -> bool:
    """判断字符是否为中文字符"""
    return '\u4e00' <= char <= '\u9fff'


_pipeline_runner: Optional[PipelineRunner] = None
_pipeline_runner_lock = threading.Lock()


def get_pipeline_runner() -> PipelineRunner:
    """获取或创建全局流水线调度器实例（线程安全，双重检查锁）"""
    global _pipeline_runner
    if _pipeline_runner is None:
        with _pipeline_runner_lock:
            if _pipeline_runner is None:
                _pipeline_runner = PipelineRunner()
    return _pipeline_runner


def reset_pipeline_runner() -> None:
    """重置全局流水线调度器实例，用于测试或重新初始化"""
    global _pipeline_runner
    with _pipeline_runner_lock:
        _pipeline_runner = None
