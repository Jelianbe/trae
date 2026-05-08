# -*- coding: utf-8 -*-
"""
引号内容分类器 (QuotationClassifier)

用途：区分引号内文本的类型，以便TTS引擎使用不同的处理方式。

分类类型：
- DIALOGUE: 角色对话（由角色声带发出）
- WRITTEN: 书面内容（石碑刻字、书信、布告等）
- THOUGHT: 内心独白（角色心里的想法）
- UNKNOWN: 未知类型

使用方式：
    from pipeline.quotation_classifier import QuotationClassifier, QuotationType
    
    classifier = QuotationClassifier()
    result = classifier.classify(text, quotation_start=100, quotation_end=120)
    
    if result.type == QuotationType.WRITTEN:
        # 使用旁白/念读音效处理
        pass
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class QuotationType(Enum):
    """引号内容类型"""
    DIALOGUE = "dialogue"        # 角色对话
    WRITTEN = "written"          # 书面内容（石碑、书信等）
    THOUGHT = "thought"          # 内心独白
    UNKNOWN = "unknown"          # 未知类型


@dataclass
class QuotationResult:
    """分类结果"""
    type: QuotationType
    confidence: float            # 置信度 (0.0 - 1.0)
    reason: str                  # 分类原因（用于调试）
    quotation_text: str          # 引号内文本
    context_before: str          # 引号前上下文
    context_after: str           # 引号后上下文


class QuotationClassifier:
    """
    引号内容分类器
    
    通过多维度特征判断引号内文本的类型：
    1. 关键词规则（"上面写着"、"信中说"等）
    2. 动词/动作分析（心理活动动词、"XX道/说"等）
    3. 上下文窗口分析
    """
    
    # 书面内容标识词
    WRITTEN_KEYWORDS = [
        '上面写着', '上写着', '写道', '信中写道', '刻着', '刻有', '写着', '信中', '书信',
        '布告', '公告', '碑文', '铭文', '卷轴', '书页', '信件', '纸条',
        '信上', '碑上', '纸上', '墙上', '门上', '牌匾', '横幅',
    ]
    
    # 内心独白动词（优先长词，避免单个字匹配）
    THOUGHT_VERBS = [
        '心中暗道', '心中想', '暗自思忖', '心中琢磨', '暗自盘算',
        '暗想', '暗忖', '寻思', '琢磨', '盘算', '思忖', '心道', '暗道',
        '心想', '思索', '沉思', '思虑', '寻思着', '思索着',
    ]
    
    # 对话引导词（角色声带发声，排除书面语境中的'道'）
    DIALOGUE_VERBS = [
        '喝道', '吼道', '答道', '笑道', '叹道', '低声道', '轻声道',
        '沉声道', '大声道', '厉声道', '柔声道', '缓缓道', '喃喃道',
        '嚷道', '斥道', '骂道', '嘲讽道', '说道', '言道',
        '冷笑道', '微笑道', '苦笑道', '干笑道', '狞笑道', '大笑道',
        '问道', '喊道', '叫道', '回应道', '开口道',
        # '道'单独放在最后，仅当没有更长匹配时才用
        '道',
    ]
    
    # 非对话动词（心理、动作等）
    NON_DIALOGUE_VERBS = [
        '想', '思考', '沉思', '思索', '回忆', '想起', '记起',
        '看', '望', '盯', '注视', '扫视', '环顾',
        '走', '跑', '跳', '坐', '站', '躺',
        '笑', '哭', '叹', '摇头', '点头', '皱眉',
    ]
    
    def __init__(self, context_window: int = 50):
        """
        初始化分类器
        
        Args:
            context_window: 上下文窗口大小（字符数）
        """
        self.context_window = context_window
    
    def classify(
        self,
        text: str,
        quotation_start: int,
        quotation_end: int,
    ) -> QuotationResult:
        """
        分类引号内容
        
        Args:
            text: 完整文本
            quotation_start: 引号开始位置
            quotation_end: 引号结束位置
            
        Returns:
            QuotationResult: 分类结果
        """
        # 提取引号内文本
        quotation_text = text[quotation_start:quotation_end]
        
        # 提取上下文
        context_before = text[max(0, quotation_start - self.context_window):quotation_start]
        context_after = text[quotation_end:min(len(text), quotation_end + self.context_window)]
        
        # 多维度特征分析
        features = self._analyze_features(text, quotation_start, quotation_end, 
                                         quotation_text, context_before, context_after)
        
        # 分类决策
        quotation_type, confidence, reason = self._decide_type(features, quotation_text)
        
        return QuotationResult(
            type=quotation_type,
            confidence=confidence,
            reason=reason,
            quotation_text=quotation_text,
            context_before=context_before,
            context_after=context_after,
        )
    
    def classify_all(self, text: str) -> List[QuotationResult]:
        """
        分类文本中所有引号内容
        
        Args:
            text: 完整文本
            
        Returns:
            List[QuotationResult]: 所有引号的分类结果
        """
        results = []
        
        # 查找所有引号对（优先中文引号，其次英文引号）
        quotation_patterns = [
            ('"', '"'),  # 中文双引号
            ('"', '"'),  # 中文双引号（另一种）
            ('"', '"'),  # 英文双引号（左）
            ('"', '"'),  # 英文双引号（右）
        ]
        
        # 使用正则查找所有引号内容
        # 匹配中文引号或英文引号，使用反向引用确保引号配对
        pattern = r'([""])(.*?)\1'
        matches = list(re.finditer(pattern, text))
        
        for match in matches:
            start = match.start()
            end = match.end()
            
            # 跳过嵌套引号（只处理最外层）
            if any(start > r.start() and end < r.end() for r in matches):
                continue
            
            result = self.classify(text, start, end)
            results.append(result)
        
        return results
    
    def _find_closest_match(self, context: str, candidates: List[str]) -> Tuple[Optional[str], int]:
        """
        查找上下文中最近的匹配词（优先最长匹配）
        
        Returns:
            Tuple[str, int]: (匹配的关键词, 距离引号的位置)，未匹配返回(None, -1)
        """
        best_match = None
        best_distance = -1
        best_length = 0  # 优先选择更长的匹配
        
        for candidate in candidates:
            pos = context.rfind(candidate)  # 从右往左找，找最近的
            if pos != -1:
                distance = len(context) - pos  # 距离引号的位置
                candidate_length = len(candidate)
                
                # 优先选择长度更长的匹配（避免"道"覆盖"暗忖"）
                if candidate_length > best_length or (candidate_length == best_length and (best_distance == -1 or distance < best_distance)):
                    best_match = candidate
                    best_distance = distance
                    best_length = candidate_length
        
        return best_match, best_distance
    
    def _analyze_features(
        self,
        text: str,
        quotation_start: int,
        quotation_end: int,
        quotation_text: str,
        context_before: str,
        context_after: str,
    ) -> dict:
        """
        分析多维度特征
        
        Returns:
            dict: 特征字典
        """
        features = {}
        
        # 特征1：引号前是否有书面内容标识词（记录最近距离）
        written_keyword, written_distance = self._find_closest_match(
            context_before, self.WRITTEN_KEYWORDS
        )
        features['has_written_keyword'] = written_keyword is not None
        if written_keyword:
            features['written_keyword'] = written_keyword
            features['written_keyword_distance'] = written_distance
        
        # 特征2：引号前是否有内心独白动词（记录最近距离）
        thought_verb, thought_distance = self._find_closest_match(
            context_before, self.THOUGHT_VERBS
        )
        features['has_thought_verb'] = thought_verb is not None
        if thought_verb:
            features['thought_verb'] = thought_verb
            features['thought_verb_distance'] = thought_distance
        
        # 特征3：引号前是否有对话引导词（记录最近距离）
        dialogue_verb, dialogue_distance = self._find_closest_match(
            context_before, self.DIALOGUE_VERBS
        )
        features['has_dialogue_verb'] = dialogue_verb is not None
        if dialogue_verb:
            features['dialogue_verb'] = dialogue_verb
            features['dialogue_verb_distance'] = dialogue_distance
        
        # 特征4：引号内文本长度
        features['quotation_length'] = len(quotation_text)
        
        # 特征5：引号内是否包含书面语特征
        features['has_written_style'] = any(
            word in quotation_text 
            for word in ['之', '乎', '者', '也', '曰', '云', '此乃', '谨记']
        )
        
        # 特征6：引号后是否有动作描述（暗示不是对话）
        features['has_action_after'] = any(
            verb in context_after[:20]
            for verb in ['转身', '离开', '走去', '站起', '坐下', '摇头', '点头', '皱眉']
        )
        
        return features
    
    def _decide_type(
        self,
        features: dict,
        quotation_text: str,
    ) -> Tuple[QuotationType, float, str]:
        """
        根据特征做出分类决策
        
        策略：综合关键词长度和距离，选择特异性最高的
        评分公式：score = keyword_length * 10 - distance
        这样既考虑特异性（长词加分），也考虑 proximity（近距离加分）
        
        Returns:
            Tuple[QuotationType, float, str]: (类型, 置信度, 原因)
        """
        # 收集所有匹配的特征
        candidates = []
        
        if features.get('has_written_keyword'):
            distance = features.get('written_keyword_distance', 999)
            keyword = features.get('written_keyword', '')
            score = len(keyword) * 10 - distance
            candidates.append(('WRITTEN', distance, keyword, '书面内容标识词', score))
        
        if features.get('has_thought_verb'):
            distance = features.get('thought_verb_distance', 999)
            verb = features.get('thought_verb', '')
            score = len(verb) * 10 - distance
            candidates.append(('THOUGHT', distance, verb, '内心独白动词', score))
        
        if features.get('has_dialogue_verb'):
            distance = features.get('dialogue_verb_distance', 999)
            verb = features.get('dialogue_verb', '')
            score = len(verb) * 10 - distance
            candidates.append(('DIALOGUE', distance, verb, '对话引导词', score))
        
        # 选择综合得分最高的关键词
        if candidates:
            # 按综合得分降序排序
            candidates.sort(key=lambda x: -x[4])
            best_type, best_distance, best_keyword, best_label, best_score = candidates[0]
            
            # 置信度基于得分
            confidence = max(0.95 - (best_distance / 100), 0.70)
            
            type_enum = QuotationType(best_type.lower())
            return (
                type_enum,
                confidence,
                f"引号前有{best_label}：'{best_keyword}'（距离{best_distance}字符）"
            )
        
        # 规则4：引号内有书面语特征，倾向于WRITTEN
        if features.get('has_written_style'):
            return (
                QuotationType.WRITTEN,
                0.70,
                "引号内包含书面语特征（之、乎、者、也等）"
            )
        
        # 规则5：引号后有动作描述，倾向于非对话
        if features.get('has_action_after'):
            return (
                QuotationType.THOUGHT,
                0.60,
                "引号后有动作描述，可能是内心独白"
            )
        
        # 默认：未知类型
        return (
            QuotationType.UNKNOWN,
            0.50,
            "无明确特征，无法确定类型"
        )


# 全局实例
_classifier = None


def get_quotation_classifier() -> QuotationClassifier:
    """获取全局分类器实例"""
    global _classifier
    if _classifier is None:
        _classifier = QuotationClassifier()
    return _classifier
