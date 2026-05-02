# -*- coding: utf-8 -*-
"""流水线调度器：串联所有处理模块，暴露统一的分析接口"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from pipeline.chapter_splitter import ChapterSplitter, Chapter
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import get_nlp, NLPBasics
from pipeline.context_diversity_validator import get_context_validator, ContextDiversityValidator
from pipeline.speaker_role_filter import get_speaker_role_filter, SpeakerRoleFilter
from pipeline.entity_linker import get_entity_linker, EntityLinker
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.semantic_ranker import get_semantic_ranker, SemanticRanker
from pipeline.emotion_tagger import EmotionTagger, get_emotion_tagger

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"


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
    2. NER + 实体链接 + 角色聚类
    3. 对话分类
    4. 拟声词检测
    5. 说话人匹配
    6. 情绪标注
    """
    
    def __init__(self):
        self.chapter_splitter = ChapterSplitter()
        self.dialogue_classifier = DialogueClassifier()
        self.sfx_detector = SfxDetector()
        self.nlp = get_nlp()
        self.char_manager = get_character_manager()
        self.speaker_matcher = SpeakerMatcher(self.char_manager)
        self.semantic_ranker = get_semantic_ranker()
        self.emotion_tagger = get_emotion_tagger()
        self.context_validator = get_context_validator()
        self.speaker_role_filter = get_speaker_role_filter()
        self.entity_linker = get_entity_linker(self.char_manager)
        
        self.progress = ProgressInfo()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._result_cache: Dict[str, List[ChapterResult]] = {}
    
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
        
        # 第二步：NER + 实体链接
        self._set_progress("NER", result.chapter_id, result.chapter_id + 1, 2, "正在识别实体...")
        nlp_result = self.nlp.analyze(content)
        entities = list(nlp_result.entities)
        
        # 应用实体链接
        linked_entities = self.entity_linker.link(entities, content)
        
        # 第三步：对话分类
        self._set_progress("对话分类", result.chapter_id, result.chapter_id + 1, 3, "正在分类对话...")
        dialogue_type = self.dialogue_classifier.classify(content)
        
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
        
        # 按句号/问号/叹号拆分句子
        import re
        sentences = re.split(r'[。！？]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
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
            
            # 构建实体列表
            sentence_entities = []
            for e in linked_entities:
                e_start = getattr(e, 'start', 0)
                e_end = getattr(e, 'end', 0)
                e_text = getattr(e, 'text', '')
                e_type = getattr(e, 'type', '')
                e_conf = getattr(e, 'confidence', 1.0)
                if sentence.find(e_text) >= 0:
                    sentence_entities.append({
                        "text": e_text,
                        "type": e_type,
                        "confidence": e_conf,
                    })
            
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
    
    def _check_pause(self):
        """检查是否暂停"""
        self._pause_event.wait()
    
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


def get_pipeline_runner() -> PipelineRunner:
    """获取或创建全局流水线调度器实例"""
    global _pipeline_runner
    if _pipeline_runner is None:
        _pipeline_runner = PipelineRunner()
    return _pipeline_runner
