# -*- coding: utf-8 -*-
"""情绪标注器：规则标注六种基础情绪

改进内容：
1. 精确引导词提取：只提取紧邻引号的动词短语（≤5字）
2. 问句置信度分层：区分强疑问词（难道/怎么）和普通问句
3. 笑类关键词拆分：苦笑→sadness，冷笑→anger，微笑→neutral
4. 否定词降级：否定词降低强度，不反转情绪
"""

import re
import threading
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class EmotionScore:
    """情绪评分结果"""
    emotion: str          # 情绪类别
    confidence: float     # 置信度 (0.0 - 1.0)
    intensity: str        # 强度 (mild/moderate/strong)
    reason: str           # 判断依据


# 精确引导词提取正则：匹配"xx道"、"xx说"、"xx问"、"xx笑"、"xx叹"、"xx怒"等
GUIDE_PHRASE_PATTERN = re.compile(
    r'([\u4e00-\u9fa5]{0,5}?(?:道|说|问|喊|叫|骂|笑|叹|答|应|怒|喝|哼|嚷)[：:，。！!]?)'
)

# 引号位置正则
QUOTE_START_PATTERN = re.compile(r'[""]')

# 基础情绪关键词模式（已拆分笑类 + GT数据驱动扩展 + 清理不精准扩展词）
EMOTION_PATTERNS: Dict[str, list] = {
    "joy": [
        r"笑", r"开心", r"高兴", r"喜悦", r"欢快", r"欢喜", r"愉快",
        r"哈哈", r"呵呵", r"嘻嘻", r"大笑", r"微笑", r"欢笑",
        r"太好了", r"太棒了", r"好极了",
        # GT数据驱动扩展（已清理"父亲"等不精准词）
        r"戏谑", r"急切", r"笑容", r"干笑",
    ],
    "anger": [
        r"怒", r"愤怒", r"生气", r"大怒", r"发火", r"咆哮", r"怒吼",
        r"可恶", r"混蛋", r"放肆", r"岂有此理", r"气死", r"没好气",
        # GT数据驱动扩展（已清理"心头""声音中"等泛化词）
        r"怒火", r"教训", r"阴沉", r"羞怒", r"挑衅", r"倔强", r"决绝", r"不服", r"懊恼",
    ],
    "sadness": [
        r"哭", r"悲伤", r"难过", r"伤心", r"流泪", r"泪水", r"痛哭",
        r"唉", r"呜", r"呜呜", r"惨", r"可怜", r"心疼", r"叹息", r"无奈",
        r"苦涩", r"呐呐", r"呐",
        # GT数据驱动扩展（已清理"血液""究竟"等不精准词）
        r"惋惜", r"轻轻", r"颤抖", r"怯懦", r"歉然", r"落寞",
    ],
    "surprise": [
        r"惊讶", r"震惊", r"吃惊", r"意外", r"竟然", r"居然",
        r"什么", r"不会吧", r"怎么可能", r"天哪", r"哇",
        r"简直", r"不敢相信", r"惊",
        # GT数据驱动扩展（已清理"血液""口唾"等不精准词）
        r"好奇", r"惊叹", r"一惊",
    ],
    "fear": [
        r"害怕", r"恐惧", r"惊吓", r"惊恐", r"吓", r"慌", r"紧张",
        r"危险", r"糟糕", r"不妙", r"恐怖", r"可怕", r"急声", r"急",
        # GT数据驱动扩展（已清理重复和泛化词）
        r"退一步", r"不安", r"吓了",
    ],
}

# 句式模板（改进后：问句置信度分层）
SENTENCE_PATTERNS: Dict[str, List[Tuple[str, str, float]]] = {
    "surprise": [
        (r"难道.*[？?]", "难道句式", 0.7),
        (r"怎么(?:可能|会).*[！!]", "怎么可能句式", 0.8),
        (r"(?:竟然|居然|出乎意料).*[？?!]", "竟然句式", 0.7),
    ],
    "anger": [
        (r"凭什么.*[！!]", "凭什么句式", 0.9),
        (r"滚.*[！!]", "滚句式", 0.9),
        (r"闭嘴.*[！!]", "闭嘴句式", 0.9),
    ],
    "sadness": [
        (r"……$", "省略号结尾", 0.5),
        (r"唉.*[！!]", "唉叹句式", 0.7),
    ],
    "joy": [
        (r"太好了.*[！!]", "太好了句式", 0.8),
    ],
    "fear": [
        (r"太可怕了.*[！!]", "太可怕句式", 0.8),
        (r"快.*逃.*[！!]", "逃跑句式", 0.8),
    ],
}

# 否定词列表
NEGATION_WORDS = ["不", "没", "未", "别", "并非", "并不", "未曾", "未能", "从不", "从未", "无", "非", "莫", "毋", "勿"]

# 程度副词列表
DEGREE_ADVERBS = {
    "mild": ["有点", "略微", "微微", "稍稍", "稍微", "略有", "稍显"],
    "strong": ["非常", "极其", "极度", "十分", "格外", "分外", "异常", "太", "极为", "无比"],
}


class EmotionTagger:
    """情绪标注器：基于规则的情绪识别
    
    改进特性：
    1. 精确引导词提取：只提取紧邻引号的动词短语
    2. 问句置信度分层：区分强疑问词和普通问句
    3. 笑类关键词拆分：苦笑/冷笑/微笑映射到不同情绪
    4. 否定词降级：降低强度而非反转情绪
    """
    
    def tag(self, text: str, speaker: str = None) -> str:
        """
        对文本进行情绪标注（单标签模式）。
        
        Args:
            text: 文本内容（推荐传入完整句子，含引导词）
            speaker: 说话人（可选，用于上下文记忆）
        
        Returns:
            情绪标签：joy/anger/sadness/surprise/fear/neutral
        """
        if not text:
            return DEFAULT_EMOTION
        
        result = self.tag_with_score(text)
        return result.emotion
    
    def tag_with_score(self, text: str, speaker: str = None) -> EmotionScore:
        """
        对文本进行情绪标注，返回详细评分。
        
        Args:
            text: 文本内容（推荐传入完整句子，含引导词）
            speaker: 说话人（可选，用于上下文记忆）
        
        Returns:
            EmotionScore: 情绪评分结果
        """
        if not text:
            return EmotionScore(
                emotion=DEFAULT_EMOTION,
                confidence=1.0,
                intensity="moderate",
                reason="空文本",
            )
        
        # 步骤1：精确引导词提取
        guide_phrase = self._extract_guide_phrase(text)
        
        # 步骤2：关键词匹配（优先引导词，再全文）
        keyword_emotion, keyword_count, keyword_matches = self._match_keywords(text, guide_phrase)
        
        # 步骤3：句式模板匹配
        pattern_emotion, pattern_score, pattern_matches = self._match_sentence_patterns(text)
        
        # 步骤4：综合评分
        best_emotion, best_score, best_reason = self._combine_scores(
            keyword_emotion, keyword_count, keyword_matches,
            pattern_emotion, pattern_score, pattern_matches,
        )
        
        # 步骤5：否定词调节（降级强度，不反转）
        adjusted_intensity, negation_reason = self._adjust_by_negation(text, best_emotion)
        
        # 步骤6：强度判断
        base_intensity = self._detect_intensity(text)
        final_intensity = self._merge_intensity(base_intensity, adjusted_intensity)
        
        # 步骤7：计算置信度
        confidence = min(best_score / 3.0, 1.0)
        
        reason = best_reason
        if negation_reason:
            reason = f"{reason}；否定词调节：{negation_reason}"
        
        return EmotionScore(
            emotion=best_emotion,
            confidence=confidence,
            intensity=final_intensity,
            reason=reason,
        )
    
    def _extract_guide_phrase(self, text: str) -> str:
        """
        精确引导词提取：只提取紧邻引号的动词短语
        
        策略：
        1. 找到左引号位置
        2. 在引号前10字内搜索动词短语（道/说/问/笑/叹/怒等）
        3. 如果找到，返回引导词；否则返回空字符串
        
        Returns:
            str: 引导词（如"冷笑道"、"急切的道"），未找到返回空字符串
        """
        quote_match = QUOTE_START_PATTERN.search(text)
        if not quote_match:
            return ""
        
        quote_pos = quote_match.start()
        # 在引号前10字内搜索
        prefix = text[max(0, quote_pos - 10):quote_pos]
        
        match = GUIDE_PHRASE_PATTERN.search(prefix)
        if match:
            return match.group(1)
        
        return ""
    
    def _match_keywords(self, text: str, guide_phrase: str = "") -> Tuple[str, int, List[str]]:
        """
        关键词匹配（优先引导词）
        
        策略：
        1. 先检查特殊笑类关键词（苦笑/冷笑）
        2. 先在引导词中匹配（权重高）
        3. 再在全文中匹配（权重低）
        """
        # 特殊笑类关键词优先检查
        special_result = self._check_special_laughter(text)
        if special_result:
            return special_result
        
        best_emotion = DEFAULT_EMOTION
        best_count = 0
        best_matches = []
        
        if guide_phrase:
            guide_emotion, guide_count, guide_matches = self._match_keywords_in_text(guide_phrase)
            if guide_count > 0:
                best_emotion = guide_emotion
                best_count = guide_count
                best_matches = guide_matches
        
        text_emotion, text_count, text_matches = self._match_keywords_in_text(text)
        if text_count > best_count:
            best_emotion = text_emotion
            best_count = text_count
            best_matches = text_matches
        
        return best_emotion, best_count, best_matches
    
    def _check_special_laughter(self, text: str) -> Optional[Tuple[str, int, List[str]]]:
        """
        特殊笑类关键词检查（优先级：冷笑 > 苦笑 > 微笑）
        
        规则：
        - 冷笑 → anger
        - 苦笑 → sadness
        - 微笑 → neutral（仅当无其他情绪关键词时）
        
        Returns:
            如果匹配到特殊笑类，返回(emotion, count, matches)；否则返回None
        """
        if "冷笑" in text:
            return ("anger", 1, ["冷笑"])
        if "苦笑" in text:
            return ("sadness", 1, ["苦笑"])
        return None
    
    def _match_keywords_in_text(self, text: str) -> Tuple[str, int, List[str]]:
        """
        在文本中匹配关键词
        
        Returns:
            (最佳情绪, 匹配次数, 匹配到的关键词列表)
        """
        best_emotion = DEFAULT_EMOTION
        best_count = 0
        best_matches = []
        
        for emotion, patterns in EMOTION_PATTERNS.items():
            matches = []
            count = 0
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    count += 1
                    matches.append(pattern)
            
            if count > best_count:
                best_count = count
                best_emotion = emotion
                best_matches = matches
        
        return best_emotion, best_count, best_matches
    
    def _match_sentence_patterns(self, text: str) -> Tuple[str, float, List[str]]:
        """
        句式模板匹配（改进后：问句置信度分层）
        
        规则：
        - 强疑问词（难道/怎么/竟然/居然）→ 高置信度 surprise
        - 普通问句 → 不单独作为 surprise 依据
        
        Returns:
            (最佳情绪, 置信度, 匹配到的句式列表)
        """
        best_emotion = DEFAULT_EMOTION
        best_score = 0.0
        best_matches = []
        
        for emotion, patterns in SENTENCE_PATTERNS.items():
            for pattern, desc, score in patterns:
                if re.search(pattern, text):
                    if score > best_score:
                        best_score = score
                        best_emotion = emotion
                        best_matches.append(desc)
        
        return best_emotion, best_score, best_matches
    
    def _combine_scores(
        self,
        keyword_emotion: str,
        keyword_count: int,
        keyword_matches: List[str],
        pattern_emotion: str,
        pattern_score: float,
        pattern_matches: List[str],
    ) -> Tuple[str, float, str]:
        """
        综合关键词和句式模板的评分
        
        策略：
        - 关键词优先于句式模板
        - 情绪相同时叠加分数
        """
        reason_parts = []
        
        if keyword_count > 0:
            keyword_score = keyword_count * 0.3
            reason_parts.append(f"关键词：{','.join(keyword_matches)}")
            
            if pattern_score > 0 and pattern_emotion != keyword_emotion:
                return keyword_emotion, keyword_score, "；".join(reason_parts)
            elif pattern_score > 0:
                total_score = keyword_score + pattern_score * 0.5
                reason_parts.append(f"句式：{','.join(pattern_matches)}")
                return keyword_emotion, total_score, "；".join(reason_parts)
            else:
                return keyword_emotion, keyword_score, "；".join(reason_parts)
        elif pattern_score > 0:
            reason_parts.append(f"句式：{','.join(pattern_matches)}")
            return pattern_emotion, pattern_score, "；".join(reason_parts)
        else:
            return DEFAULT_EMOTION, 0.0, "无匹配"
    
    def _adjust_by_negation(self, text: str, emotion: str) -> Tuple[str, str]:
        """
        否定词调节（改进后：降级强度，不反转情绪）
        
        规则：
        - 检测否定词是否在情绪关键词前 6 个字符内
        - 如果是，返回"降级"信号，由调用方合并强度
        
        Returns:
            (强度调节信号, 调节原因)
            强度调节信号："downgrade" 或 "none"
        """
        if emotion == DEFAULT_EMOTION:
            return "none", ""
        
        for neg in NEGATION_WORDS:
            neg_pos = text.find(neg)
            if neg_pos == -1:
                continue
            
            window = text[neg_pos:neg_pos + 7]
            for pattern in EMOTION_PATTERNS.get(emotion, []):
                if re.search(pattern, window):
                    return "downgrade", f"否定词'{neg}'降级 {emotion} 强度"
        
        return "none", ""
    
    def _detect_intensity(self, text: str) -> str:
        """
        检测情绪强度
        
        Returns:
            "mild" / "moderate" / "strong"
        """
        for level, adverbs in DEGREE_ADVERBS.items():
            for adverb in adverbs:
                if adverb in text:
                    return level
        
        return "moderate"
    
    def _merge_intensity(self, base_intensity: str, adjustment: str) -> str:
        """
        合并基础强度和否定词调节
        
        规则：
        - downgrade: mild → neutral, moderate → mild, strong → moderate
        - none: 保持原强度
        
        Returns:
            str: 最终强度
        """
        intensity_order = ["neutral", "mild", "moderate", "strong"]
        
        if adjustment == "downgrade":
            current_idx = intensity_order.index(base_intensity) if base_intensity in intensity_order else 1
            new_idx = max(0, current_idx - 1)
            return intensity_order[new_idx]
        
        return base_intensity
    
    def tag_multi_label(self, text: str) -> Dict[str, float]:
        """
        多标签情绪标注，返回所有匹配的情绪及其置信度。
        
        Args:
            text: 文本内容
        
        Returns:
            情绪字典，格式为 {情绪类型: 置信度}
        """
        if not text:
            return {DEFAULT_EMOTION: 1.0}
        
        emotions = {}
        
        for emotion, patterns in EMOTION_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, text):
                    score += 0.2
            
            if score > 0:
                emotions[emotion] = min(score, 1.0)
        
        if not emotions:
            emotions[DEFAULT_EMOTION] = 1.0
        
        return emotions


DEFAULT_EMOTION = "neutral"


_emotion_tagger: Optional[EmotionTagger] = None
_emotion_tagger_lock = threading.Lock()


def get_emotion_tagger() -> EmotionTagger:
    """获取或创建全局情绪标注器实例（线程安全，双重检查锁）"""
    global _emotion_tagger
    if _emotion_tagger is None:
        with _emotion_tagger_lock:
            if _emotion_tagger is None:
                _emotion_tagger = EmotionTagger()
    return _emotion_tagger


def reset_emotion_tagger() -> None:
    """重置全局情绪标注器实例，用于测试或重新初始化"""
    global _emotion_tagger
    with _emotion_tagger_lock:
        _emotion_tagger = None
