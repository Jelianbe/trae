# -*- coding: utf-8 -*-
"""流水线调度器：串联所有处理模块，暴露统一的分析接口"""

import json
import logging
import re
import threading
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from pipeline.chapter_splitter import ChapterSplitter, Chapter
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import get_nlp, NLPBasics
from pipeline.context_diversity_validator import get_context_validator, ContextDiversityValidator
from pipeline.speaker_role_filter import get_speaker_role_filter, SpeakerRoleFilter
from pipeline.entity_linker import get_entity_linker, EntityLinker
from pipeline.entity_clusterer import get_entity_clusterer, EntityClusterer
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.semantic_ranker import get_semantic_ranker, SemanticRanker
from pipeline.emotion_tagger import EmotionTagger, get_emotion_tagger
from utils.text_utils import split_sentences_smart

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"


from utils.config import COLD_START_CHARS_THRESHOLD

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
class SentenceData:
    """单句处理结果"""
    text: str
    type: str = "narration"
    speaker: str = ""
    emotion: str = "neutral"
    speed: float = 1.0
    tone: str = "normal"
    sfx: List[str] = field(default_factory=list)
    entities: List[dict] = field(default_factory=list)
    sentence_id: int = 0


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
    3. 拟声词检测
    4. 说话人匹配
    5. 情绪标注
    """
    
    def __init__(self):
        self.chapter_splitter = ChapterSplitter()
        self.sfx_detector = SfxDetector()
        self.nlp = get_nlp()
        self.char_manager = get_character_manager()
        self.speaker_matcher = SpeakerMatcher(self.char_manager)
        self.semantic_ranker = get_semantic_ranker()
        self.emotion_tagger = get_emotion_tagger()
        self.context_validator = get_context_validator()
        self.speaker_role_filter = get_speaker_role_filter()
        self.entity_linker = get_entity_linker(self.char_manager)
        self.entity_clusterer = get_entity_clusterer()
        
        self.progress = ProgressInfo()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._result_cache: Dict[str, List[ChapterResult]] = {}
        
        self._total_processed_chars = 0
        self._cold_start_done = False
    
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
        if not force and cache_key in self._result_cache:
            logger.info(f"使用缓存结果 (cache_key={cache_key})")
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
            self._result_cache[cache_key] = results
            
            self.progress.state = PipelineState.DONE
            self._set_progress("完成", total_chapters, total_chapters, 6, "分析完成")
            self._notify_progress(progress_callback)
            
            logger.info(f"流水线完成：{total_chapters} 个章节")
            
        except Exception as e:
            self.progress.state = PipelineState.ERROR
            self.progress.message = str(e)
            logger.error(f"流水线执行错误: {e}", exc_info=True)
            raise
        
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

        # 第四步：拟声词检测
        self._set_progress("拟声词检测", result.chapter_id, result.chapter_id + 1, 4, "正在检测拟声词...")
        sfx_words = self.sfx_detector.detect(content)
        
        # 第五步：说话人匹配
        self._set_progress("说话人匹配", result.chapter_id, result.chapter_id + 1, 5, "正在匹配说话人...")
        dialogue_results = self.speaker_matcher.analyze_dialogue(content, chapter_id=chapter_id)
        
        # 构建对话映射
        dialogue_map: Dict[str, str] = {}
        for dialogue_text, speaker in dialogue_results:
            dialogue_map[dialogue_text.strip()] = speaker.name if speaker else ""
        
        # 第六步：情绪标注
        self._set_progress("情绪标注", result.chapter_id, result.chapter_id + 1, 6, "正在标注情绪...")
        
        # 使用智能句子分割（保护引号内内容不被拆分）
        sentences = split_sentences_smart(content)
        
        sentence_id = 0
        dialogue_count = 0
        narration_count = 0
        sfx_count = 0
        
        for sentence in sentences:
            sentence_id += 1
            
            # 判断是否为对话
            is_dialogue = any(d.strip() in sentence for d in dialogue_map.keys())
            
            sentence_type = "dialogue" if is_dialogue else "narration"
            speaker = ""
            emotion = "neutral"
            
            if is_dialogue:
                for d_text, d_speaker in dialogue_map.items():
                    if d_text in sentence:
                        speaker = d_speaker
                        emotion = self.emotion_tagger.tag(sentence, speaker)
                        dialogue_count += 1
                        break
            else:
                narration_count += 1
            
            # 检测拟声词
            sentence_sfx = []
            for sfx in sfx_words:
                if sentence.find(sfx.text) >= 0:
                    sentence_sfx.append(sfx.text)
                    sfx_count += 1
            
            # 构建实体列表（使用 position-based 匹配避免部分匹配问题）
            sentence_entities = []
            for e in linked_entities:
                e_start = getattr(e, 'start', 0)
                e_end = getattr(e, 'end', 0)
                e_text = getattr(e, 'text', '')
                e_type = getattr(e, 'type', '')
                e_conf = getattr(e, 'confidence', 1.0)
                e_standard = getattr(e, 'standard_name', '')
                e_is_linked = getattr(e, 'is_linked', False)

                if self._entity_in_sentence(e_text, e_start, e_end, sentence):
                    entity_dict = {
                        "text": e_text,
                        "type": e_type,
                        "confidence": e_conf,
                    }
                    if e_standard:
                        entity_dict["standard_name"] = e_standard
                    entity_dict["is_linked"] = e_is_linked
                    sentence_entities.append(entity_dict)
            
            result.sentences.append(SentenceData(
                text=sentence,
                type=sentence_type,
                speaker=speaker,
                emotion=emotion,
                sfx=sentence_sfx,
                entities=sentence_entities,
                sentence_id=sentence_id,
            ))
        
        result.statistics = {
            "total_sentences": sentence_id,
            "dialogue_count": dialogue_count,
            "narration_count": narration_count,
            "sfx_count": sfx_count,
            "entity_count": len(linked_entities),
        }
        
        return result
    
    def _trigger_cold_start(self):
        """
        冷启动触发逻辑：当累积字数达到阈值时，执行批量聚类。
        
        此方法将当前所有 is_confirmed=0 的实体升级为 is_confirmed=1，
        并执行一次完整的 EntityClusterer.cluster(write_back=True)。
        """
        if self._cold_start_done:
            return
        
        logger.info(f"冷启动触发：已处理 {self._total_processed_chars} 字，达到阈值 {COLD_START_CHARS_THRESHOLD}")
        
        try:
            all_entities = []
            for result in self._result_cache.get("default", []):
                for sentence in result.sentences:
                    for e_dict in sentence.entities:
                        from pipeline.nlp_basics import Entity
                        entity = Entity(
                            text=e_dict.get("text", ""),
                            type=e_dict.get("type", "PER"),
                            start=0,
                            end=len(e_dict.get("text", "")),
                            confidence=e_dict.get("confidence", 1.0),
                        )
                        if entity.type == "PER" and len(entity.text) >= 2:
                            all_entities.append(entity)
            
            if all_entities:
                self.entity_clusterer.cluster(entities=all_entities, text=self._full_text, write_back=True)
                self._cold_start_done = True
                logger.info(f"冷启动批量聚类完成：{len(all_entities)} 个实体参与聚类")
            else:
                logger.warning("冷启动触发但无有效实体，跳过聚类")
                self._cold_start_done = True
        except Exception as e:
            logger.error(f"冷启动聚类失败: {e}", exc_info=True)
    
    def _check_pause(self):
        """检查是否暂停"""
        self._pause_event.wait()

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
        # 对于单字实体，需要额外检查边界
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


def _is_chinese_char(char: str) -> bool:
    """判断字符是否为中文字符"""
    return '\u4e00' <= char <= '\u9fff'

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
                        "speed": s.speed,
                        "tone": s.tone,
                        "sfx": s.sfx,
                        "entities": s.entities,
                        "sentence_id": s.sentence_id,
                    }
                    for s in chapter.sentences
                ],
            }
            data.append(chapter_dict)
        
        return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    
    def export_ssml(self, results: List[ChapterResult]) -> str:
        """导出为 SSML 格式"""
        ssml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<speak version="1.0">']
        
        for chapter in results:
            ssml_parts.append(f'<p><!-- 第{chapter.chapter_id}章 {chapter.title} -->')
            
            for sentence in chapter.sentences:
                prosody_attrs = []
                if sentence.speed != 1.0:
                    prosody_attrs.append(f'rate="{sentence.speed}"')
                if sentence.tone != "normal":
                    prosody_attrs.append(f'pitch="{sentence.tone}"')
                
                prosody = f'<prosody {" ".join(prosody_attrs)}>' if prosody_attrs else ''
                prosody_close = '</prosody>' if prosody_attrs else ''
                
                ssml_parts.append(f'  <s>{prosody}{sentence.text}{prosody_close}</s>')
            
            ssml_parts.append('</p>')
        
        ssml_parts.append('</speak>')
        return '\n'.join(ssml_parts)


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
