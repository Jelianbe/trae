#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
方案C：LLM 情绪标注离线验证

目标：用 LLM 对测试文本的对话做情绪标注，建立情绪 F1 基线。
如果 LLM 能做到 50%+ F1，说明规则系统有改进空间；
如果 LLM 也做不到 30%，说明文本情绪标注本身就是极难任务。

用法：
    1. 需要安装 openai 库: pip install openai
    2. 配置 LLM API（支持 OpenAI 兼容 API，如 Ollama、vLLM、本地部署等）
    3. 运行: python scripts/llm_emotion_baseline.py
    
    或者用纯规则系统对比（不需要 LLM）:
    python scripts/llm_emotion_baseline.py --no-llm
"""
import sys
import os
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_tagger import get_emotion_tagger
from pipeline.pipeline_runner import PipelineRunner

BASE_DIR = Path(__file__).parent.parent
TEST_DIR = BASE_DIR / "tests"

TEST_CASES = [
    ("都市", TEST_DIR / "test_novel_urban.txt", TEST_DIR / "test_novel_urban_ground_truth.json"),
    ("西幻", TEST_DIR / "test_novel_western.txt", TEST_DIR / "test_novel_western_ground_truth.json"),
    ("斗破", TEST_DIR / "test_novel_doupo_ch1-10.txt", TEST_DIR / "test_novel_doupo_ground_truth.json"),
]

EMOTIONS = {"joy", "anger", "sadness", "surprise", "fear", "neutral"}


def extract_dialogues_with_gt(novel_text, gt_data):
    """从测试文本中提取对话，并对照 GT 获取正确说话人"""
    # 提取所有引号内的对话
    quotes = re.findall(r'[""\u201c\u201d\u300c\u300d]([^""\u201c\u201d\u300c\u300d]+?)[""\u201c\u201d\u300c\u300d]', novel_text)
    
    # 从 GT 获取对话-说话人映射
    gt_speakers = {}
    if "dialogue_speakers" in gt_data:
        for item in gt_data["dialogue_speakers"]:
            gt_speakers[item["text"][:30]] = item["speaker"]
    
    return quotes[:50]  # 取前50条对话做标注


def rule_based_emotion_tagging(dialogues):
    """用现有规则系统标注情绪"""
    tagger = get_emotion_tagger()
    results = []
    
    for dialogue in dialogues:
        # 当前管道：emotion_tagger 拿到的是经过处理的句子（不含引导词）
        emotion = tagger.tag(dialogue)
        results.append({
            "text": dialogue[:60],
            "emotion": emotion,
            "method": "rule",
        })
    
    return results


def llm_emotion_tagging(dialogues, api_base=None, api_key=None, model=None):
    """用 LLM 标注情绪"""
    try:
        from openai import OpenAI
    except ImportError:
        print("⚠️ 需要安装 openai 库: pip install openai")
        print("   或使用 --no-llm 跳过 LLM 标注")
        return []
    
    client = OpenAI(
        base_url=api_base or "http://localhost:11434/v1",
        api_key=api_key or "ollama",
    )
    model = model or "qwen2.5:3b"
    
    system_prompt = """你是一个情绪标注专家。请对给定的小说对话片段标注情绪。

情绪类别（六选一）：
- joy（喜悦）：开心、高兴、欢笑、戏谑
- anger（愤怒）：生气、怒吼、冷笑、不耐烦
- sadness（悲伤）：哭泣、难过、无奈、叹息
- surprise（惊讶）：震惊、意外、好奇、不可思议
- fear（恐惧）：害怕、紧张、不安、慌乱
- neutral（中性）：平淡叙述、无明显情绪

只输出情绪类别，不要解释。输出格式：joy/anger/sadness/surprise/fear/neutral"""
    
    results = []
    batch = []
    
    for i, dialogue in enumerate(dialogues):
        batch.append(dialogue)
        
        if len(batch) >= 5 or i == len(dialogues) - 1:
            # 批量标注
            texts = "\n".join(f"对话{j+1}: {t}" for j, t in enumerate(batch))
            prompt = f"请标注以下对话的情绪：\n\n{texts}\n\n按顺序输出情绪类别，每行一个。"
            
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=100,
                )
                
                emotions = response.choices[0].message.content.strip().split("\n")
                for j, em in enumerate(emotions):
                    em = em.strip().lower()
                    if em not in EMOTIONS:
                        em = "neutral"
                    if j < len(batch):
                        results.append({
                            "text": batch[j][:60],
                            "emotion": em,
                            "method": "llm",
                        })
            except Exception as e:
                print(f"  LLM 标注失败: {e}")
                for t in batch:
                    results.append({
                        "text": t[:60],
                        "emotion": "neutral",
                        "method": "llm",
                    })
            
            batch = []
    
    return results


def compare_with_gt(rule_results, llm_results, gt_data):
    """对比规则和 LLM 的情绪标注与 GT 的差异"""
    # 注意：当前 GT 文件中没有情绪标注字段，这里主要对比两种方法的一致性
    # 以及用人工抽查的方式评估
    
    print(f"\n规则系统情绪分布:")
    rule_emotions = {}
    for r in rule_results:
        rule_emotions[r["emotion"]] = rule_emotions.get(r["emotion"], 0) + 1
    for em, count in sorted(rule_emotions.items(), key=lambda x: -x[1]):
        print(f"  {em}: {count}")
    
    if llm_results:
        print(f"\nLLM 情绪分布:")
        llm_emotions = {}
        for r in llm_results:
            llm_emotions[r["emotion"]] = llm_emotions.get(r["emotion"], 0) + 1
        for em, count in sorted(llm_emotions.items(), key=lambda x: -x[1]):
            print(f"  {em}: {count}")
        
        # 对比两种方法的一致性
        agreement = 0
        total = min(len(rule_results), len(llm_results))
        for i in range(total):
            if rule_results[i]["emotion"] == llm_results[i]["emotion"]:
                agreement += 1
        print(f"\n规则 vs LLM 一致性: {agreement}/{total} ({agreement/total*100:.1f}%)")
    
    # 人工抽查示例
    print(f"\n=== 人工抽查（前10条） ===")
    for i in range(min(10, len(rule_results))):
        text = rule_results[i]["text"][:50]
        rule_em = rule_results[i]["emotion"]
        llm_em = llm_results[i]["emotion"] if llm_results else "N/A"
        match = "✅" if rule_em == llm_em else "❌"
        print(f"  [{i+1}] {text}")
        print(f"       规则: {rule_em}  |  LLM: {llm_em}  {match}")
        print()


def main():
    use_llm = "--no-llm" not in sys.argv
    
    print("=" * 60)
    print("方案C：LLM 情绪标注离线验证")
    print("=" * 60)
    
    all_rule_results = []
    all_llm_results = []
    
    for genre, test_file, gt_file in TEST_CASES:
        print(f"\n{'='*60}")
        print(f"【{genre}】")
        print(f"{'='*60}")
        
        if not test_file.exists():
            print(f"  跳过（文件不存在）")
            continue
        
        novel_text = test_file.read_text(encoding="utf-8")
        gt_data = json.loads(gt_file.read_text(encoding="utf-8")) if gt_file.exists() else {}
        
        dialogues = extract_dialogues_with_gt(novel_text, gt_data)
        print(f"  提取对话: {len(dialogues)} 条")
        
        # 规则系统标注
        rule_results = rule_based_emotion_tagging(dialogues)
        all_rule_results.extend(rule_results)
        
        # LLM 标注（可选）
        llm_results = []
        if use_llm:
            api_base = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
            api_key = os.environ.get("OPENAI_API_KEY", "ollama")
            model = os.environ.get("LLM_MODEL", "qwen2.5:3b")
            llm_results = llm_emotion_tagging(dialogues, api_base, api_key, model)
        
        all_llm_results.extend(llm_results)
        
        # 对比
        compare_with_gt(rule_results, llm_results, gt_data)
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"汇总")
    print(f"{'='*60}")
    print(f"规则系统总计标注: {len(all_rule_results)} 条对话")
    rule_total = {}
    for r in all_rule_results:
        rule_total[r["emotion"]] = rule_total.get(r["emotion"], 0) + 1
    for em, count in sorted(rule_total.items(), key=lambda x: -x[1]):
        print(f"  {em}: {count}")
    
    if all_llm_results:
        llm_total = {}
        for r in all_llm_results:
            llm_total[r["emotion"]] = llm_total.get(r["emotion"], 0) + 1
        print(f"\nLLM总计标注: {len(all_llm_results)} 条对话")
        for em, count in sorted(llm_total.items(), key=lambda x: -x[1]):
            print(f"  {em}: {count}")
        
        # 总一致性
        agreement = sum(1 for r, l in zip(all_rule_results, all_llm_results) if r["emotion"] == l["emotion"])
        total = len(all_rule_results)
        print(f"\n总一致性: {agreement}/{total} ({agreement/total*100:.1f}%)")
    
    print(f"\n结论:")
    neutral_ratio = rule_total.get("neutral", 0) / len(all_rule_results) * 100
    print(f"  规则系统 neutral 占比: {neutral_ratio:.1f}%")
    if neutral_ratio > 70:
        print(f"  → 规则系统过度偏向 neutral，需要引入更强情绪信号")
    else:
        print(f"  → 规则系统情绪分布相对均衡")
    
    if all_llm_results:
        llm_neutral = llm_total.get("neutral", 0) / len(all_llm_results) * 100
        print(f"  LLM neutral 占比: {llm_neutral:.1f}%")


if __name__ == "__main__":
    main()
