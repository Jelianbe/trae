# -*- coding: utf-8 -*-
"""LLM 情绪标注 Benchmark V3 - 上下文 + Few-Shot + 多温度

改进点（vs V2）：
1. 传递上下文（context_before / context_after）
2. Few-Shot 示例（每类取 V2 预测正确的第一条）
3. 只输出 L2(6类)，L1 通过映射得出
4. 多温度测试（0.0 / 0.3 / 0.5）
5. 与 V2 baseline 对比

用法：
    python scripts/llm_emotion_benchmark_v3.py
"""

# === 必须在导入 transformers 之前设置镜像 ===
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
import sys
import time
import random
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

L2_EMOTIONS = ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral']


def load_gt_data(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_v2_result(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    model_name = "Qwen/Qwen2.5-1.5B-Instruct"

    print(f"正在加载模型: {model_name}")
    print(f"使用镜像: {os.environ.get('HF_ENDPOINT', 'default')}")

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


def build_few_shot_examples(v2_result: dict, gt_data: list) -> str:
    """从 V2 结果中每类取第一个预测正确的条目作为 Few-Shot 示例"""
    gt_map = {item['id']: item for item in gt_data}

    correct_by_class = {}
    for pred in v2_result['predictions']:
        if pred.get('l2_correct', False):
            label = pred['gt_l2']
            if label not in correct_by_class:
                correct_by_class[label] = pred

    examples = []
    for emotion in L2_EMOTIONS:
        if emotion in correct_by_class:
            p = correct_by_class[emotion]
            item = gt_map.get(p['id'])
            if item:
                ctx_before = item.get('context_before', '')
                ctx_after = item.get('context_after', '')
                text = item['text']
                speaker = item.get('speaker', '')

                context_parts = []
                if ctx_before:
                    context_parts.append(f"上文：{ctx_before}")
                context_parts.append(f"对话：{text}")
                if ctx_after:
                    context_parts.append(f"下文：{ctx_after}")

                context_str = "\n".join(context_parts)
                speaker_str = f"（说话人：{speaker}）" if speaker and "未知" not in speaker else ""
                examples.append(f"{context_str}{speaker_str}\n情绪：{emotion}")

    if not examples:
        return ""

    few_shot_str = "以下是标注示例：\n\n" + "\n\n---\n\n".join(examples)
    return few_shot_str


def build_system_prompt(few_shot_examples: str) -> str:
    system_prompt = """你是一个小说对话情绪标注引擎。请对给定的小说对话片段标注情绪。

情绪类别（六选一）：
- joy（喜悦）：开心、欢笑、嘲讽的笑
- anger（愤怒）：生气、呵斥、冷笑、不耐烦
- sadness（悲伤）：难过、叹息、遗憾、无奈
- surprise（惊讶）：震惊、意外、好奇
- fear（恐惧）：害怕、紧张、不安、惊恐
- neutral（中性）：平淡叙述、无明显情绪

请只输出一个情绪类别名称，不要输出其他内容。"""

    if few_shot_examples:
        system_prompt += "\n\n" + few_shot_examples

    return system_prompt


def build_user_prompt(item: dict) -> str:
    context_before = item.get('context_before', '')
    context_after = item.get('context_after', '')
    text = item['text']
    speaker = item.get('speaker', '')

    parts = []
    if context_before:
        parts.append(f"上文：{context_before}")
    parts.append(f"对话：{text}")
    if context_after:
        parts.append(f"下文：{context_after}")

    context_str = "\n".join(parts)

    if speaker and "未知" not in speaker:
        context_str += f"\n\n当前说话人可能是：{speaker}"

    return f"请标注以下对话的情绪：\n\n{context_str}\n\n情绪："


def llm_classify_emotion_v3(model, tokenizer, device, item: dict, temperature: float) -> str:
    import torch

    system_prompt = build_system_prompt(item.get('_few_shot', ''))
    user_prompt = build_user_prompt(item)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_input, return_tensors="pt").to(device)

    if temperature == 0.0:
        generate_kwargs = {"do_sample": False}
    else:
        generate_kwargs = {"do_sample": True, "temperature": temperature}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=20,
            pad_token_id=tokenizer.eos_token_id,
            **generate_kwargs,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    response = response.strip()

    # 提取情绪
    for em in L2_EMOTIONS:
        if em in response.lower():
            return em
    return "neutral"


def calc_accuracy(predictions: list, ground_truth: list) -> float:
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(ground_truth) if ground_truth else 0.0


def calc_f1(predictions: list, ground_truth: list, labels: list) -> dict:
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
    print("LLM 情绪标注 Benchmark V3")
    print("模型: Qwen2.5-1.5B-Instruct")
    print("改进: 上下文 + Few-Shot + 只输出L2 + 多温度")
    print("测试集: 100条 (含角色上下文)")
    print("=" * 70)
    print()

    # 加载数据
    project_root = Path(__file__).parent.parent
    gt_path = project_root / "tests" / "role_emotion_gt_100.json"
    v2_result_path = project_root / "tests" / "llm_benchmark_v2_result.json"

    gt_data = load_gt_data(gt_path)
    v2_result = load_v2_result(v2_result_path)

    print(f"数据集: {len(gt_data)} 条")
    print(f"文体分布: 都市{sum(1 for d in gt_data if d['style'] == '都市')} + "
          f"西幻{sum(1 for d in gt_data if d['style'] == '西幻')} + "
          f"修仙{sum(1 for d in gt_data if d['style'] == '修仙')} + "
          f"历史{sum(1 for d in gt_data if d['style'] == '历史')}")
    print()

    # 构建 Few-Shot 示例
    few_shot_str = build_few_shot_examples(v2_result, gt_data)
    print("Few-Shot 示例:")
    print(few_shot_str[:500] + "...")
    print()

    # 将 Few-Shot 注入到每条数据中
    for item in gt_data:
        item['_few_shot'] = few_shot_str

    # 加载模型
    model, tokenizer, device = load_model()
    print()

    # 多温度测试
    temperatures = [0.0, 0.3, 0.5]
    all_results = {}

    for temp in temperatures:
        print("=" * 70)
        print(f"温度: {temp}")
        print("=" * 70)

        l2_predictions = []
        gt_l2_labels = []

        total_time = 0
        for i, item in enumerate(gt_data):
            gt_l2 = item['emotion_label']
            start_time = time.time()
            pred_l2 = llm_classify_emotion_v3(model, tokenizer, device, item, temp)
            elapsed = time.time() - start_time
            total_time += elapsed

            l2_predictions.append(pred_l2)
            gt_l2_labels.append(gt_l2)

            match = "[OK]" if pred_l2 == gt_l2 else "[XX]"
            print(f"  [{i+1:3d}/100] {item['text'][:20]:<20} GT={gt_l2:<8} LLM={pred_l2:<8} {match} ({elapsed:.1f}s)")

        print()
        print(f"总耗时: {total_time:.1f}s, 平均: {total_time/len(gt_data):.1f}s/条")

        # L2 评估
        f1s_l2, macro_f1_l2 = calc_f1(l2_predictions, gt_l2_labels, L2_EMOTIONS)
        accuracy_l2 = calc_accuracy(l2_predictions, gt_l2_labels)

        # L1 评估（通过映射）
        l1_predictions = [L2_TO_L1.get(p, 'neutral') for p in l2_predictions]
        gt_l1_labels = [L2_TO_L1.get(g, 'neutral') for g in gt_l2_labels]
        l1_labels = ['excited', 'subdued', 'neutral']
        f1s_l1, macro_f1_l1 = calc_f1(l1_predictions, gt_l1_labels, l1_labels)
        accuracy_l1 = calc_accuracy(l1_predictions, gt_l1_labels)

        # Neutral 占比
        neutral_count = sum(1 for p in l2_predictions if p == 'neutral')
        neutral_ratio = neutral_count / len(l2_predictions)

        print()
        print(f"L2(6类) 准确率: {accuracy_l2:.1%}")
        print(f"L2 Macro F1: {macro_f1_l2:.3f}")
        print(f"L1(3类) 准确率: {accuracy_l1:.1%}")
        print(f"L1 Macro F1: {macro_f1_l1:.3f}")
        print(f"Neutral 占比: {neutral_ratio:.1%}")

        print()
        print("L2 各类 F1:")
        for label in L2_EMOTIONS:
            gt_count = sum(1 for g in gt_l2_labels if g == label)
            print(f"  {label:<12} F1={f1s_l2[label]:.3f}  GT数量={gt_count}")

        # V2 对比
        v2_l2_accuracy = v2_result['l2_accuracy']
        v2_l1_accuracy = v2_result['l1_accuracy']
        v2_l2_macro_f1 = v2_result['l2_macro_f1']
        v2_l1_macro_f1 = v2_result['l1_macro_f1']

        print()
        print(f"与 V2 对比:")
        print(f"  V2 L2 准确率: {v2_l2_accuracy:.1%} -> V3 L2 准确率: {accuracy_l2:.1%} (变化: {accuracy_l2 - v2_l2_accuracy:+.1%})")
        print(f"  V2 L1 准确率: {v2_l1_accuracy:.1%} -> V3 L1 准确率: {accuracy_l1:.1%} (变化: {accuracy_l1 - v2_l1_accuracy:+.1%})")
        print(f"  V2 L2 Macro F1: {v2_l2_macro_f1:.3f} -> V3 L2 Macro F1: {macro_f1_l2:.3f} (变化: {macro_f1_l2 - v2_l2_macro_f1:+.3f})")
        print(f"  V2 L1 Macro F1: {v2_l1_macro_f1:.3f} -> V3 L1 Macro F1: {macro_f1_l1:.3f} (变化: {macro_f1_l1 - v2_l1_macro_f1:+.3f})")

        # 错误分析
        errors = [(i, gt_data[i]['text'], gt_l2_labels[i], l2_predictions[i])
                  for i in range(len(gt_data)) if l2_predictions[i] != gt_l2_labels[i]]

        print()
        print(f"错误 case 数量: {len(errors)}")

        all_results[str(temp)] = {
            "temperature": temp,
            "l1_accuracy": accuracy_l1,
            "l2_accuracy": accuracy_l2,
            "l1_macro_f1": macro_f1_l1,
            "l2_macro_f1": macro_f1_l2,
            "l1_f1_by_class": f1s_l1,
            "l2_f1_by_class": f1s_l2,
            "neutral_ratio": neutral_ratio,
            "total_time": round(total_time, 1),
            "avg_time_per_item": round(total_time / len(gt_data), 2),
            "predictions": [
                {
                    "id": gt_data[i]['id'],
                    "text": gt_data[i]['text'],
                    "speaker": gt_data[i].get('speaker', ''),
                    "gt_l2": gt_l2_labels[i],
                    "pred_l2": l2_predictions[i],
                    "gt_l1": gt_l1_labels[i],
                    "pred_l1": l1_predictions[i],
                    "l1_correct": gt_l1_labels[i] == l1_predictions[i],
                    "l2_correct": gt_l2_labels[i] == l2_predictions[i]
                }
                for i in range(len(gt_data))
            ],
            "error_count": len(errors),
        }

        print()
        print("-" * 70)

    # 汇总对比
    print("=" * 70)
    print("三组温度汇总对比")
    print("=" * 70)
    print(f"{'指标':<20} {'V2(baseline)':<15} {'T=0.0':<15} {'T=0.3':<15} {'T=0.5':<15}")
    print("-" * 80)

    v2_l2 = v2_result['l2_accuracy']
    v2_l1 = v2_result['l1_accuracy']
    v2_l2_f1 = v2_result['l2_macro_f1']
    v2_l1_f1 = v2_result['l1_macro_f1']

    for label, v2_v in [("L2 准确率", v2_l2), ("L1 准确率", v2_l1),
                         ("L2 Macro F1", v2_l2_f1), ("L1 Macro F1", v2_l1_f1)]:
        vals = [all_results[str(t)][label.lower().replace(" ", "_").replace("准确率", "accuracy").replace("macro_f1", "macro_f1")]
                for t in temperatures]
        # Fix key mapping
        key_map = {
            "L2 准确率": "l2_accuracy",
            "L1 准确率": "l1_accuracy",
            "L2 Macro F1": "l2_macro_f1",
            "L1 Macro F1": "l1_macro_f1",
        }
        key = key_map[label]
        t0 = all_results["0.0"][key]
        t3 = all_results["0.3"][key]
        t5 = all_results["0.5"][key]

        if "accuracy" in key:
            print(f"{label:<20} {v2_v:>13.1%}   {t0:>13.1%}   {t3:>13.1%}   {t5:>13.1%}")
        else:
            print(f"{label:<20} {v2_v:>13.3f}   {t0:>13.3f}   {t3:>13.3f}   {t5:>13.3f}")

    # 保存结果
    result_path = project_root / "tests" / "llm_benchmark_v3_result.json"
    output = {
        "model": "Qwen2.5-1.5B-Instruct",
        "v2_baseline": {
            "l1_accuracy": v2_result['l1_accuracy'],
            "l2_accuracy": v2_result['l2_accuracy'],
            "l1_macro_f1": v2_result['l1_macro_f1'],
            "l2_macro_f1": v2_result['l2_macro_f1'],
        },
        "temperatures": all_results,
    }

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print(f"结果已保存到: {result_path}")


if __name__ == "__main__":
    main()
