# -*- coding: utf-8 -*-
"""LLM 情绪标注 Benchmark V2 - 3类情绪 + 角色上下文

目标：用 Qwen2.5-1.5B-Instruct 对 100 条 GT 数据做情绪标注。
与 V1 的不同：
1. 使用3类情绪分类（excited/subdued/neutral）
2. 提供角色上下文锚点（speaker_hint）
3. 使用100条测试集（role_emotion_gt_100.json）

用法：
    python scripts/llm_emotion_benchmark_v2.py
"""

# === 必须在导入 transformers 之前设置镜像 ===
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# L2→L1 映射
L2_TO_L1 = {
    'joy': 'excited',
    'anger': 'excited',
    'surprise': 'excited',
    'sadness': 'subdued',
    'fear': 'subdued',
    'neutral': 'neutral',
}


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


def llm_classify_emotion_v2(model, tokenizer, device, text: str, speaker_hint: str = "") -> tuple:
    """用 LLM 标注单条对话的情绪（同时输出L1和L2）
    
    Args:
        text: 对话文本
        speaker_hint: 说话人提示（角色上下文锚点）
    
    Returns:
        (l1_label, l2_label) - L1(3类)和L2(6类)情绪
    """
    import torch
    
    system_prompt = """你是一个情绪标注专家。请对给定的小说对话片段标注情绪。

情绪类别：
L2 细分类（六选一）：
- joy（喜悦）：开心、高兴、欢笑、戏谑、嘲讽的笑
- anger（愤怒）：生气、怒吼、冷笑、不耐烦、呵斥
- sadness（悲伤）：哭泣、难过、无奈、叹息、遗憾
- surprise（惊讶）：震惊、意外、好奇、不可思议
- fear（恐惧）：害怕、紧张、不安、慌乱、惊恐
- neutral（中性）：平淡叙述、无明显情绪

L1 粗分类（三选一）：
- excited（激动）：joy/anger/surprise → 高唤醒情绪
- subdued（压抑）：sadness/fear → 低唤醒情绪
- neutral（中性）：平静、无明显情绪

输出格式（仅输出两行）：
L2: <情绪>
L1: <情绪>

示例：
L2: anger
L1: excited"""

    speaker_info = f"\n说话人: {speaker_hint}" if speaker_hint and speaker_hint != "未知" and "未知" not in speaker_hint else ""
    user_prompt = f"请标注以下对话的情绪：{speaker_info}\n\n对话：{text}\n\n情绪："
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_input, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=30,
            do_sample=False,
            temperature=0.1,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    response = response.strip()
    
    # 解析 L2
    l2_label = "neutral"
    l2_emotions = ["joy", "anger", "sadness", "surprise", "fear", "neutral"]
    for line in response.split('\n'):
        if line.strip().startswith("L2:"):
            val = line.strip()[3:].strip().lower()
            for em in l2_emotions:
                if em in val:
                    l2_label = em
                    break
    
    # 解析 L1
    l1_label = "neutral"
    l1_emotions = ["excited", "subdued", "neutral"]
    for line in response.split('\n'):
        if line.strip().startswith("L1:"):
            val = line.strip()[3:].strip().lower()
            for em in l1_emotions:
                if em in val:
                    l1_label = em
                    break
    
    # 如果L1解析失败，用L2映射
    if l1_label not in L2_TO_L1:
        l1_label = L2_TO_L1.get(l2_label, "neutral")
    
    return l1_label, l2_label


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
    print("LLM 情绪标注 Benchmark V2")
    print("模型: Qwen2.5-1.5B-Instruct")
    print("情绪分类: L1(3类: excited/subdued/neutral) + L2(6类)")
    print("测试集: 100条 (含角色上下文)")
    print("=" * 70)
    print()
    
    # 加载GT数据
    gt_path = Path(__file__).parent.parent / "tests" / "role_emotion_gt_100.json"
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
    
    l1_predictions = []
    l2_predictions = []
    gt_l1_labels = []
    gt_l2_labels = []
    
    total_time = 0
    for i, item in enumerate(gt_data):
        text = item['text']
        gt_l2 = item['emotion_label']
        gt_l1 = L2_TO_L1.get(gt_l2, 'neutral')
        speaker_hint = item.get('speaker', '')
        
        start_time = time.time()
        pred_l1, pred_l2 = llm_classify_emotion_v2(model, tokenizer, device, text, speaker_hint)
        elapsed = time.time() - start_time
        total_time += elapsed
        
        l1_predictions.append(pred_l1)
        l2_predictions.append(pred_l2)
        gt_l1_labels.append(gt_l1)
        gt_l2_labels.append(gt_l2)
        
        l2_match = "✅" if pred_l2 == gt_l2 else "❌"
        l1_match = "✅" if pred_l1 == gt_l1 else "❌"
        print(f"  [{i+1:3d}/100] {text[:20]:<20} GT_L2={gt_l2:<8} LLM_L2={pred_l2:<8} {l2_match} | GT_L1={gt_l1:<8} LLM_L1={pred_l1:<8} {l1_match} ({elapsed:.1f}s)")
    
    print()
    print(f"总耗时: {total_time:.1f}s, 平均: {total_time/len(gt_data):.1f}s/条")
    print()
    
    # L2 评估
    print("=" * 70)
    print("LLM 评估结果 - L2(6类)")
    print("=" * 70)
    
    l2_labels = ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral']
    f1s_l2, macro_f1_l2 = calc_f1(l2_predictions, gt_l2_labels, l2_labels)
    accuracy_l2 = calc_accuracy(l2_predictions, gt_l2_labels)
    
    print(f"{'类别':<12} {'F1':>8} {'GT数量':>8}")
    print("-" * 35)
    for label in l2_labels:
        gt_count = sum(1 for g in gt_l2_labels if g == label)
        print(f"{label:<12} {f1s_l2[label]:>8.3f} {gt_count:>8}")
    print("-" * 35)
    print(f"{'Macro F1':<12} {macro_f1_l2:>8.3f}")
    print(f"{'准确率':<12} {accuracy_l2:>8.3f}")
    print()
    
    # L1 评估
    print("=" * 70)
    print("LLM 评估结果 - L1(3类)")
    print("=" * 70)
    
    l1_labels = ['excited', 'subdued', 'neutral']
    f1s_l1, macro_f1_l1 = calc_f1(l1_predictions, gt_l1_labels, l1_labels)
    accuracy_l1 = calc_accuracy(l1_predictions, gt_l1_labels)
    
    print(f"{'类别':<12} {'F1':>8} {'GT数量':>8}")
    print("-" * 35)
    for label in l1_labels:
        gt_count = sum(1 for g in gt_l1_labels if g == label)
        print(f"{label:<12} {f1s_l1[label]:>8.3f} {gt_count:>8}")
    print("-" * 35)
    print(f"{'Macro F1':<12} {macro_f1_l1:>8.3f}")
    print(f"{'准确率':<12} {accuracy_l1:>8.3f}")
    print()
    
    # 与规则系统对比
    print("=" * 70)
    print("对比：LLM vs 规则系统")
    print("=" * 70)
    print(f"规则系统 L2(6类) 准确率: 32.0%")
    print(f"LLM        L2(6类) 准确率: {accuracy_l2:.1%}")
    print(f"规则系统 L1(3类) 准确率: 33.0%")
    print(f"LLM        L1(3类) 准确率: {accuracy_l1:.1%}")
    print()
    
    if accuracy_l1 >= 0.70:
        print("✅ LLM 在 L1(3类) 上达到 70%+，建议用 LLM 替代规则系统")
    elif accuracy_l1 >= 0.60:
        print("⚠️ LLM 在 L1(3类) 上达到 60%+，有提升但仍需优化")
    else:
        print("❌ LLM 在 L1(3类) 上未达 60%，情绪标注是极难任务，3类+规则系统已足够")
    
    print()
    
    # 错误分析
    print("=" * 70)
    print("L1 错误 case 分析")
    print("=" * 70)
    
    errors = [(i, gt_data[i]['text'], gt_l1_labels[i], l1_predictions[i], gt_l2_labels[i], l2_predictions[i]) 
              for i in range(len(gt_data)) if l1_predictions[i] != gt_l1_labels[i]]
    
    if errors:
        print(f"共 {len(errors)} 条错误：")
        for i, text, gt_l1, pred_l1, gt_l2, pred_l2 in errors[:15]:
            print(f"  [{i+1:3d}] {text[:30]:<30} GT_L1={gt_l1:<8} LLM_L1={pred_l1:<8} GT_L2={gt_l2:<8} LLM_L2={pred_l2:<8}")
    else:
        print("全部正确！")
    
    print()
    
    # 保存结果
    result_path = Path(__file__).parent.parent / "tests" / "llm_benchmark_v2_result.json"
    result = {
        "model": "Qwen2.5-1.5B-Instruct",
        "total_time": round(total_time, 1),
        "avg_time_per_item": round(total_time / len(gt_data), 2),
        "l1_accuracy": accuracy_l1,
        "l2_accuracy": accuracy_l2,
        "l1_macro_f1": macro_f1_l1,
        "l2_macro_f1": macro_f1_l2,
        "l1_f1_by_class": f1s_l1,
        "l2_f1_by_class": f1s_l2,
        "predictions": [{"id": gt_data[i]['id'], "text": gt_data[i]['text'], 
                         "speaker": gt_data[i].get('speaker', ''),
                         "gt_l2": gt_l2_labels[i], "pred_l2": l2_predictions[i],
                         "gt_l1": gt_l1_labels[i], "pred_l1": l1_predictions[i],
                         "l1_correct": gt_l1_labels[i] == l1_predictions[i],
                         "l2_correct": gt_l2_labels[i] == l2_predictions[i]}
                        for i in range(len(gt_data))],
    }
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {result_path}")
    
    return macro_f1_l1, accuracy_l1


if __name__ == "__main__":
    main()
