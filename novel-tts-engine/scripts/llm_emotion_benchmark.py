# -*- coding: utf-8 -*-
"""LLM 情绪标注 Benchmark（选项B：transformers 直接加载模型）

目标：用 Qwen2.5-1.5B-Instruct 对 50 条 GT 数据做情绪标注，探测情绪标注任务的天花板。

用法：
    python scripts/llm_emotion_benchmark.py
    
环境要求：
    - transformers >= 4.35.0
    - torch >= 2.0
    - 首次运行会自动下载模型（约 3GB）
"""

# === 必须在导入 transformers 之前设置镜像 ===
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_gt_data(filepath: str) -> list:
    """加载GT数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_model():
    """加载 Qwen2.5-1.5B-Instruct 模型"""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    
    print(f"正在加载模型: {model_name}")
    print(f"使用镜像: {os.environ.get('HF_ENDPOINT', 'default')}")
    print("首次运行会自动下载模型（约 3GB），请耐心等待...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # 检测设备
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    
    if device == "cpu":
        model = model.to("cpu")
    
    print(f"模型加载完成")
    return model, tokenizer, device


def llm_classify_emotion(model, tokenizer, device, text: str) -> str:
    """用 LLM 标注单条对话的情绪"""
    import torch
    
    system_prompt = """你是一个情绪标注专家。请对给定的小说对话片段标注情绪。

情绪类别（六选一）：
- joy（喜悦）：开心、高兴、欢笑、戏谑、嘲讽的笑
- anger（愤怒）：生气、怒吼、冷笑、不耐烦、呵斥
- sadness（悲伤）：哭泣、难过、无奈、叹息、遗憾
- surprise（惊讶）：震惊、意外、好奇、不可思议
- fear（恐惧）：害怕、紧张、不安、慌乱、惊恐
- neutral（中性）：平淡叙述、无明显情绪

只输出一个情绪类别（joy/anger/sadness/surprise/fear/neutral），不要解释。"""

    user_prompt = f"请标注以下对话的情绪：\n\n对话：{text}\n\n情绪："
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_input, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=10,
            do_sample=False,
            temperature=0.1,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    response = response.strip().lower()
    
    # 解析情绪
    emotions = ["joy", "anger", "sadness", "surprise", "fear", "neutral"]
    for em in emotions:
        if em in response:
            return em
    
    return "neutral"


def calc_accuracy(predictions: list, ground_truth: list) -> float:
    """计算准确率"""
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(ground_truth) if ground_truth else 0.0


def calc_f1(predictions: list, ground_truth: list, labels: list) -> dict:
    """计算每个类别的 F1 和 Macro F1"""
    f1s = {}
    for label in labels:
        tp = sum(1 for p, g in zip(predictions, ground_truth) if p == label and g == label)
        fp = sum(1 for p, g in zip(predictions, ground_truth) if p == label and g != label)
        fn = sum(1 for p, g in zip(predictions, ground_truth) if p != label and g == label)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        f1s[label] = round(f1, 3)
    
    macro_f1 = sum(f1s.values()) / len(f1s)
    return f1s, round(macro_f1, 3)


def main():
    import torch
    
    print("=" * 70)
    print("LLM 情绪标注 Benchmark")
    print("模型: Qwen2.5-1.5B-Instruct")
    print("=" * 70)
    print()
    
    # 加载GT数据
    gt_path = Path(__file__).parent.parent / "tests" / "emotion_gt_50.json"
    gt_data = load_gt_data(gt_path)
    
    print(f"数据集: {len(gt_data)} 条")
    print(f"文体分布: 都市{sum(1 for d in gt_data if d['style'] == '都市')} + "
          f"西幻{sum(1 for d in gt_data if d['style'] == '西幻')} + "
          f"修仙{sum(1 for d in gt_data if d['style'] == '修仙')} + "
          f"历史{sum(1 for d in gt_data if d['style'] == '历史')}")
    print()
    
    # 加载模型
    model, tokenizer, device = load_model()
    print()
    
    # LLM 标注
    print("=" * 70)
    print("开始 LLM 标注...")
    print("=" * 70)
    
    predictions = []
    gt_labels = []
    
    total_time = 0
    for i, item in enumerate(gt_data):
        text = item['text']
        gt_label = item['emotion_label']
        
        start_time = time.time()
        pred_label = llm_classify_emotion(model, tokenizer, device, text)
        elapsed = time.time() - start_time
        total_time += elapsed
        
        predictions.append(pred_label)
        gt_labels.append(gt_label)
        
        match = "✅" if pred_label == gt_label else "❌"
        print(f"  [{i+1:2d}/50] {text[:25]:<25} GT={gt_label:<8} LLM={pred_label:<8} {match} ({elapsed:.1f}s)")
    
    print()
    print(f"总耗时: {total_time:.1f}s, 平均: {total_time/len(gt_data):.1f}s/条")
    print()
    
    # 计算 F1
    print("=" * 70)
    print("LLM 评估结果")
    print("=" * 70)
    
    l2_labels = ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral']
    f1s, macro_f1 = calc_f1(predictions, gt_labels, l2_labels)
    accuracy = calc_accuracy(predictions, gt_labels)
    
    print(f"{'类别':<12} {'F1':>8} {'GT数量':>8}")
    print("-" * 35)
    for label in l2_labels:
        gt_count = sum(1 for g in gt_labels if g == label)
        print(f"{label:<12} {f1s[label]:>8.3f} {gt_count:>8}")
    print("-" * 35)
    print(f"{'Macro F1':<12} {macro_f1:>8.3f}")
    print(f"{'准确率':<12} {accuracy:>8.3f}")
    print()
    
    # 错误分析
    print("=" * 70)
    print("错误 case 分析")
    print("=" * 70)
    
    errors = [(i, gt_data[i]['text'], gt_labels[i], predictions[i]) 
              for i in range(len(gt_data)) if predictions[i] != gt_labels[i]]
    
    if errors:
        print(f"共 {len(errors)} 条错误：")
        for i, text, gt, pred in errors[:15]:
            print(f"  [{i+1:2d}] {text[:30]:<30} GT={gt:<8} LLM={pred:<8}")
    else:
        print("全部正确！")
    
    print()
    
    # 保存结果
    result_path = Path(__file__).parent.parent / "tests" / "llm_benchmark_result.json"
    result = {
        "model": "Qwen2.5-1.5B-Instruct",
        "total_time": round(total_time, 1),
        "avg_time_per_item": round(total_time / len(gt_data), 2),
        "macro_f1": macro_f1,
        "accuracy": accuracy,
        "f1_by_class": f1s,
        "predictions": [{"id": gt_data[i]['id'], "text": gt_data[i]['text'], 
                         "gt": gt_labels[i], "pred": predictions[i],
                         "correct": gt_labels[i] == predictions[i]}
                        for i in range(len(gt_data))],
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {result_path}")
    
    return macro_f1, accuracy


if __name__ == "__main__":
    main()
