# -*- coding: utf-8 -*-
"""
角色识别评分系统（Evaluator）

用途：量化评估说话人识别准确率，提供可对比的评分指标
来源：无外部依赖，基于 pipeline 内部接口
边界：仅评估说话人归属，不评估 TTS 质量或情绪标注

评分指标：
  - 准确率（Accuracy）：正确识别的对话数 / 总对话数
  - 精确率（Precision）：对某角色，正确识别为该角色的次数 / 被识别为该角色的总次数
  - 召回率（Recall）：对某角色，正确识别为该角色的次数 / 该角色应为说话人的总次数
  - F1 分数（F1-Score）：2 * (Precision * Recall) / (Precision + Recall)
  - 未知率（Unknown Rate）：未能识别出说话人的对话数 / 总对话数

使用方式：
  from pipeline.evaluator import Evaluator, DialogueTestCase
  
  # 定义测试用例集
  test_cases = [
      DialogueTestCase(
          text='林轩说道："你好。"',
          expected_speaker='林轩',
          expected_count=1,
      ),
  ]
  
  # 运行评估
  evaluator = Evaluator(character_manager, speaker_matcher)
  result = evaluator.evaluate(test_cases)
  print(result.report())
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from collections import defaultdict


@dataclass
class DialogueTestCase:
    """单个对话测试用例
    
    Attributes:
        text: 包含对话的完整文本
        expected_speaker: 期望的说话人名称（None 表示期望未知）
        expected_count: 期望识别出的对话数（默认 1）
        description: 可选，用例描述
    """
    text: str
    expected_speaker: Optional[str] = None
    expected_count: int = 1
    description: str = ''


@dataclass
class SingleResult:
    """单个对话的评估结果"""
    dialogue: str
    expected: Optional[str]
    actual: Optional[str]
    match_type: str
    is_correct: bool


@dataclass
class CharMetric:
    """角色级评分指标"""
    name: str
    correct: int = 0
    predicted: int = 0    # 被识别为该角色的总次数
    actual: int = 0       # 该角色应为说话人的总次数
    
    @property
    def precision(self) -> float:
        """精确率 = 正确识别次数 / 被识别为该角色的总次数"""
        if self.predicted == 0:
            return 0.0
        return self.correct / self.predicted
    
    @property
    def recall(self) -> float:
        """召回率 = 正确识别次数 / 该角色应为说话人的总次数"""
        if self.actual == 0:
            return 0.0
        return self.correct / self.actual
    
    @property
    def f1(self) -> float:
        """F1 分数"""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)


@dataclass
class EvaluationResult:
    """评估结果"""
    test_cases: int = 0
    total_dialogues: int = 0
    correct: int = 0
    unknown: int = 0
    character_metrics: Dict[str, CharMetric] = field(default_factory=dict)
    case_results: List[SingleResult] = field(default_factory=list)
    
    @property
    def accuracy(self) -> float:
        """总体准确率"""
        if self.total_dialogues == 0:
            return 0.0
        return self.correct / self.total_dialogues
    
    @property
    def unknown_rate(self) -> float:
        """未知率"""
        if self.total_dialogues == 0:
            return 0.0
        return self.unknown / self.total_dialogues
    
    def report(self, title: str = '评估报告') -> str:
        """生成格式化的评估报告"""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f" {title}")
        lines.append(f"{'=' * 60}")
        lines.append(f"")
        lines.append(f" 📊 总体指标")
        lines.append(f" {'─' * 40}")
        lines.append(f"   测试用例: {self.test_cases}")
        lines.append(f"   总对话数: {self.total_dialogues}")
        lines.append(f"   正确识别: {self.correct}")
        lines.append(f"   未知:     {self.unknown}")
        lines.append(f"   准确率:   {self.accuracy:.1%}")
        lines.append(f"   未知率:   {self.unknown_rate:.1%}")
        lines.append(f"")
        
        if self.character_metrics:
            lines.append(f" 📊 角色级指标")
            lines.append(f" {'─' * 60}")
            lines.append(f" {'角色':<12s} {'正确':>5s} {'预测':>5s} {'实际':>5s} {'精确率':>8s} {'召回率':>8s} {'F1':>8s}")
            lines.append(f" {'─' * 60}")
            for name in sorted(self.character_metrics.keys()):
                m = self.character_metrics[name]
                lines.append(f" {name:<12s} {m.correct:>5d} {m.predicted:>5d} {m.actual:>5d} {m.precision:>7.1%} {m.recall:>7.1%} {m.f1:>7.1%}")
            lines.append(f" {'─' * 60}")
            lines.append(f"")
        
        if self.case_results:
            lines.append(f" 📋 逐条明细")
            lines.append(f" {'─' * 60}")
            for i, r in enumerate(self.case_results):
                mark = '✅' if r.is_correct else '❌'
                lines.append(f" {mark} [{i+1:2d}] 期望={r.expected or '未知':<8s} 实际={r.actual or '未知':<8s} 方式={r.match_type:<20s} {r.dialogue}")
        
        return '\n'.join(lines)
    
    def summary_line(self) -> str:
        """单行摘要"""
        return f"准确率={self.accuracy:.1%} 未知率={self.unknown_rate:.1%} 正确={self.correct}/{self.total_dialogues}"


class Evaluator:
    """角色识别评估器"""
    
    def __init__(self, character_manager, speaker_matcher):
        self.cm = character_manager
        self.sm = speaker_matcher
    
    def evaluate(self, test_cases: List[DialogueTestCase]) -> EvaluationResult:
        """运行评估
        
        Args:
            test_cases: 测试用例列表
        
        Returns:
            EvaluationResult 包含所有评分指标
        """
        from pipeline.speaker_matcher import DIALOGUE_PATTERNS
        
        result = EvaluationResult(test_cases=len(test_cases))
        char_metrics = defaultdict(lambda: CharMetric(name=''))
        
        for tc in test_cases:
            result.total_dialogues += tc.expected_count
            
            # 提取对话位置
            dialogues = []
            seen_positions = set()
            for pattern in DIALOGUE_PATTERNS:
                for match in pattern.finditer(tc.text):
                    start, end = match.start(), match.end()
                    if start not in seen_positions:
                        dialogues.append((start, end, match.group(2)))
                        seen_positions.add(start)
            dialogues.sort(key=lambda x: x[0])
            
            if not dialogues:
                # 无对话的情况，期望应匹配
                is_correct = tc.expected_speaker is None
                if is_correct:
                    result.correct += 1
                single = SingleResult(
                    dialogue='(无对话)',
                    expected=tc.expected_speaker,
                    actual=None,
                    match_type='no_dialogue',
                    is_correct=is_correct,
                )
                result.case_results.append(single)
                continue
            
            self.sm.reset_activity()
            prev_speaker = None
            
            for i, (start, end, dialogue) in enumerate(dialogues):
                prev_end = dialogues[i-1][1] if i > 0 else 0
                prefix = tc.text[prev_end:start].strip()
                next_start = dialogues[i+1][0] if i < len(dialogues) - 1 else len(tc.text)
                suffix = tc.text[end:next_start].strip()
                
                from pipeline.speaker_matcher import DialogueContext
                context = DialogueContext(
                    text=prefix + " " + suffix,
                    prev_speaker=prev_speaker,
                    context_before=prefix,
                    context_after=suffix,
                )
                
                match_result = self.sm.match_speaker(context)
                actual = match_result.character.name if match_result and match_result.character and match_result.character.name != '未知' else None
                match_type = match_result.match_type if match_result else 'fallback'
                
                prev_speaker = actual
                
                # 只评估第 0 个对话（如果 expected_count=1）
                if i >= tc.expected_count:
                    break
                
                expected = tc.expected_speaker if i == 0 else None
                is_correct = (actual == expected) if expected else (actual is None)
                
                if is_correct:
                    result.correct += 1
                
                if actual is None or actual == '未知':
                    result.unknown += 1
                
                # 更新角色级指标
                if expected:
                    name = expected
                    if name not in char_metrics:
                        char_metrics[name] = CharMetric(name=name)
                    char_metrics[name].actual += 1
                    if is_correct:
                        char_metrics[name].correct += 1
                
                if actual:
                    name = actual
                    if name not in char_metrics:
                        char_metrics[name] = CharMetric(name=name)
                    char_metrics[name].predicted += 1
                    if is_correct and expected and actual == expected:
                        pass  # correct 已计数
                
                single = SingleResult(
                    dialogue=dialogue[:30],
                    expected=expected,
                    actual=actual,
                    match_type=match_type,
                    is_correct=is_correct,
                )
                result.case_results.append(single)
        
        # 填充角色级指标
        result.character_metrics = dict(char_metrics)
        
        return result
    
    def compare_modes(self, test_cases: List[DialogueTestCase],
                       mode_a_label: str = '模式A：无角色库',
                       mode_b_label: str = '模式B：预创建角色库') -> Tuple[EvaluationResult, EvaluationResult, str]:
        """对比两种模式的评估结果
        
        Returns:
            (result_a, result_b, comparison_report)
        """
        # 模式A：无角色库
        result_a = self.evaluate(test_cases)
        
        # 模式B：预创建角色库（角色已在 self.cm 中）
        result_b = self.evaluate(test_cases)
        
        # 生成对比报告
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f" 双模式对比评估")
        lines.append(f"{'=' * 60}")
        lines.append(f"")
        lines.append(f" {'指标':<20s} {mode_a_label:<25s} {mode_b_label:<25s} {'差值':>10s}")
        lines.append(f" {'─' * 80}")
        
        delta_acc = result_b.accuracy - result_a.accuracy
        delta_unk = result_b.unknown_rate - result_a.unknown_rate
        lines.append(f" {'准确率':<20s} {result_a.accuracy:>10.1%}{'':>15s} {result_b.accuracy:>10.1%}{'':>15s} {delta_acc:>+9.1%}")
        lines.append(f" {'未知率':<20s} {result_a.unknown_rate:>10.1%}{'':>15s} {result_b.unknown_rate:>10.1%}{'':>15s} {delta_unk:>+9.1%}")
        lines.append(f" {'正确数':<20s} {result_a.correct:>5d}/{result_a.total_dialogues:<5d}{'':>15s} {result_b.correct:>5d}/{result_b.total_dialogues:<5d}")
        lines.append(f"")
        
        if result_a.character_metrics or result_b.character_metrics:
            all_chars = set(result_a.character_metrics.keys()) | set(result_b.character_metrics.keys())
            lines.append(f" {'角色':<12s} {'指标':<8s} {mode_a_label:<25s} {mode_b_label:<25s}")
            lines.append(f" {'─' * 70}")
            for name in sorted(all_chars):
                ma = result_a.character_metrics.get(name)
                mb = result_b.character_metrics.get(name)
                a_f1 = ma.f1 if ma else 0.0
                b_f1 = mb.f1 if mb else 0.0
                lines.append(f" {name:<12s} {'F1':<8s} {a_f1:>10.1%}{'':>15s} {b_f1:>10.1%}{'':>15s}")
                lines.append(f" {'':<12s} {'实际':<8s} {ma.actual if ma else 0:>5d}{'':>20s} {mb.actual if mb else 0:>5d}")
                lines.append(f" {'':<12s} {'正确':<8s} {ma.correct if ma else 0:>5d}{'':>20s} {mb.correct if mb else 0:>5d}")
        
        lines.append(f" {'─' * 80}")
        if delta_acc > 0:
            lines.append(f" ➡ 结论：角色库模式准确率提升 {delta_acc:.1%}")
        elif delta_acc < 0:
            lines.append(f" ➡ 结论：角色库模式准确率下降 {abs(delta_acc):.1%}")
        else:
            lines.append(f" ➡ 结论：两种模式准确率持平")
        
        return result_a, result_b, '\n'.join(lines)
