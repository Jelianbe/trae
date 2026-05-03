#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
情绪标注交叉验证：对比DeepSeek标注与EmotionTagger规则标注

用途：
1. 提取50句真实对话
2. 使用EmotionTagger自动标注
3. 与DeepSeek标注对比
4. 分析差异和系统改进方向

使用方法：
    python scripts/cross_validate_emotions.py
"""

import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emotion_tagger import get_emotion_tagger


@dataclass
class DeepSeekAnnotation:
    """DeepSeek标注结果"""
    index: int
    emotion: str
    intensity: str  # mild/moderate/strong
    tone: str  # 语气描述
    notes: str  # 备注
    reason: str  # 判断依据


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    index: int
    dialogue: str
    context: str
    deepseek_emotion: str
    our_emotion: str
    match: bool
    notes: str


def parse_deepseek_annotations(filepath: str) -> List[DeepSeekAnnotation]:
    """解析DeepSeek标注文件"""
    annotations = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析表格行（从第12行开始）
    lines = content.strip().split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('| # |'):
            in_table = True
            continue
        
        if in_table and line.startswith('|'):
            # 解析表格行
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 6 and parts[0].isdigit():
                annotation = DeepSeekAnnotation(
                    index=int(parts[0]),
                    emotion=parts[1],
                    intensity=parts[2],
                    tone=parts[3],
                    notes=parts[4],
                    reason=parts[5],
                )
                annotations.append(annotation)
    
    return annotations


def extract_dialogues_from_test_file(filepath: str) -> Dict[int, str]:
    """从测试文本文件提取50句对话（提取引导词+对话，不包含远处前文情绪描写）
    
    策略：
    1. 提取【目标对话】下方的完整行
    2. 如果该行很长（>100字），只保留引号前后的关键引导词（±20字）
    3. 目的是捕获"xx冷笑道"、"xx急切的道"等引导词，但排除远处的动作描写
    """
    dialogues = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    current_index = None
    next_line_is_dialogue = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # 匹配 #N 标题（如 #1, #2 等）
        if line_stripped.startswith('#') and line_stripped[1:].isdigit():
            current_index = int(line_stripped[1:])
            continue
        
        # 匹配【目标对话】标记
        if '【目标对话】' in line_stripped:
            next_line_is_dialogue = True
            continue
        
        # 下一行就是目标对话
        if next_line_is_dialogue and current_index and line_stripped:
            if len(line_stripped) > 80:
                quote_start = line_stripped.find('"')
                quote_end = line_stripped.rfind('"')
                
                if quote_start != -1 and quote_end != -1 and quote_start < quote_end:
                    start = max(0, quote_start - 15)
                    end = min(len(line_stripped), quote_end + 1)
                    dialogues[current_index] = line_stripped[start:end]
                else:
                    dialogues[current_index] = line_stripped[:80]
            else:
                dialogues[current_index] = line_stripped
            
            next_line_is_dialogue = False
    
    return dialogues


def cross_validate(
    deepseek_file: str,
    test_text_file: str,
    output_file: str = None,
) -> List[CrossValidationResult]:
    """执行交叉验证"""
    # 解析标注
    ds_annotations = parse_deepseek_annotations(deepseek_file)
    dialogues = extract_dialogues_from_test_file(test_text_file)
    
    # 获取标注器
    tagger = get_emotion_tagger()
    
    results = []
    match_count = 0
    mismatch_count = 0
    
    print(f"{'='*80}")
    print(f"情绪标注交叉验证")
    print(f"{'='*80}\n")
    print(f"DeepSeek标注: {len(ds_annotations)} 条")
    print(f"提取到的对话: {len(dialogues)} 条")
    print()
    
    for ds in ds_annotations:
        dialogue = dialogues.get(ds.index, "")
        
        if not dialogue:
            results.append(CrossValidationResult(
                index=ds.index,
                dialogue="(未提取到)",
                context="",
                deepseek_emotion=ds.emotion,
                our_emotion="N/A",
                match=False,
                notes="未提取到对话文本",
            ))
            continue
        
        # 使用EmotionTagger标注
        our_emotion = tagger.tag(dialogue)
        match = our_emotion == ds.emotion
        
        if match:
            match_count += 1
        else:
            mismatch_count += 1
        
        result = CrossValidationResult(
            index=ds.index,
            dialogue=dialogue[:50],
            context="",
            deepseek_emotion=ds.emotion,
            our_emotion=our_emotion,
            match=match,
            notes=f"DeepSeek: {ds.tone}",
        )
        results.append(result)
    
    # 输出统计
    accuracy = match_count / len(ds_annotations) if ds_annotations else 0
    
    print(f"{'='*80}")
    print(f"统计结果")
    print(f"{'='*80}")
    print(f"总数: {len(ds_annotations)}")
    print(f"一致: {match_count}")
    print(f"不一致: {mismatch_count}")
    print(f"准确率: {accuracy:.1%}")
    print()
    
    # 输出详细对比
    print(f"{'='*80}")
    print(f"详细对比")
    print(f"{'='*80}\n")
    
    for r in results:
        status = "✅" if r.match else "❌"
        print(f"{r.index:2d}. {status} DeepSeek: {r.deepseek_emotion:<10} | "
              f"我们: {r.our_emotion:<10} | {r.dialogue[:40]}")
        if not r.match:
            print(f"    备注: {r.notes}")
    
    # 输出不匹配分析
    print(f"\n{'='*80}")
    print(f"不匹配分析")
    print(f"{'='*80}\n")
    
    mismatches = [r for r in results if not r.match]
    if mismatches:
        for r in mismatches:
            print(f"#{r.index}: DeepSeek={r.deepseek_emotion}, 我们={r.our_emotion}")
            print(f"   对话: {r.dialogue}")
            print(f"   原因: {r.notes}")
            print()
    else:
        print("无不匹配项")
    
    # 保存详细报告
    if output_file:
        save_report(results, output_file)
    
    return results


def save_report(results: List[CrossValidationResult], output_file: str):
    """保存详细报告"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 情绪标注交叉验证报告\n\n")
        f.write(f"总数: {len(results)}\n")
        
        match_count = sum(1 for r in results if r.match)
        f.write(f"一致: {match_count}\n")
        f.write(f"不一致: {len(results) - match_count}\n")
        f.write(f"准确率: {match_count/len(results):.1%}\n\n")
        
        f.write("## 详细对比\n\n")
        f.write("| # | 对话 | DeepSeek | 我们 | 一致 |\n")
        f.write("|---|------|----------|------|------|\n")
        
        for r in results:
            status = "✅" if r.match else "❌"
            f.write(f"| {r.index} | {r.dialogue[:30]} | {r.deepseek_emotion} | {r.our_emotion} | {status} |\n")


def main():
    """主函数"""
    deepseek_file = str(PROJECT_ROOT / "tests" / "deepseek标注文件.txt")
    test_text_file = str(PROJECT_ROOT / "tests" / "emotion_test_sentences_with_context.txt")
    output_file = str(PROJECT_ROOT / "analysis_reports" / "情绪交叉验证报告.md")
    
    results = cross_validate(deepseek_file, test_text_file, output_file)
    
    print(f"\n详细报告已保存到: {output_file}")


if __name__ == '__main__':
    main()
