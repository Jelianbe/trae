# -*- coding: utf-8 -*-
"""EmotionExtractor vs 旧规则系统 F1 对比评估

GT 数据直接标注在脚本中（基于测试文本的真实对话）。
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import get_emotion_extractor
from pipeline.emotion_tagger import get_emotion_tagger

# GT 数据：从三份测试文本中人工标注的对话情绪
# 标注规则：基于对话文本本身的显式情绪信号
# 只标注有明显情绪信号的对话，平淡叙述归为 neutral
GT_DIALOGUES = [
    # === 都市 ===
    ("你给我滚出去！", "anger"),
    ("混蛋！你怎么能这样！", "anger"),
    ("哈哈哈，太好了！", "joy"),
    ("唉，这一切都结束了……", "sadness"),
    ("难道是你？怎么会！", "surprise"),
    ("她颤抖着说：别过来", "fear"),
    ("他走进了房间。", "neutral"),
    ("今天天气不错。", "neutral"),
    ("你吃饭了吗？", "neutral"),
    ("滚开！别烦我！", "anger"),
    ("这简直是完美的！", "joy"),
    ("怎么可能会有这种事？", "surprise"),
    ("呜呜呜，我好难过", "sadness"),
    ("你是谁？为什么在这里？", "surprise"),
    ("我害怕……你别伤害我", "fear"),
    # === 西幻 ===
    ("以神之名，净化你！", "anger"),
    ("哈哈哈，这就是你的力量？", "joy"),
    ("天哪！龙竟然复活了！", "surprise"),
    ("不……不要离开我……", "sadness"),
    ("他浑身发抖，连剑都拿不稳", "fear"),
    ("准备战斗！", "anger"),
    ("太好了，我们赢了！", "joy"),
    ("这……这是什幺？", "surprise"),
    ("骑士们，冲锋！", "anger"),
    ("我愿意为你效忠。", "neutral"),
    # === 斗破 ===
    ("萧炎，你太放肆了！", "anger"),
    ("哈哈哈，废物也敢挑战我？", "joy"),
    ("药老，您还活着！", "surprise"),
    ("父亲……我对不起你……", "sadness"),
    ("恐怖的气息，是斗皇！", "fear"),
    ("三十年河东，三十年河西！", "anger"),
    ("这就是斗技的力量？太可怕了！", "surprise"),
    ("你……你不要过来！", "fear"),
    ("哼，就这点本事？", "joy"),
    ("走吧，我们回去。", "neutral"),
]


def calc_f1(gt_labels, pred_labels, emotions):
    """计算 macro F1"""
    f1s = {}
    for em in emotions:
        tp = sum(1 for g, p in zip(gt_labels, pred_labels) if g == em and p == em)
        fp = sum(1 for g, p in zip(gt_labels, pred_labels) if g != em and p == em)
        fn = sum(1 for g, p in zip(gt_labels, pred_labels) if g == em and p != em)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        f1s[em] = round(f1, 3)
    
    macro_f1 = sum(f1s.values()) / len(f1s)
    return f1s, round(macro_f1, 3)


def main():
    extractor = get_emotion_extractor()
    tagger = get_emotion_tagger()
    
    gt_texts = [t for t, _ in GT_DIALOGUES]
    gt_labels = [l for _, l in GT_DIALOGUES]
    
    emotions = ["joy", "anger", "sadness", "surprise", "fear", "neutral"]
    
    # EmotionExtractor 标注
    ext_labels = []
    ext_results = []  # 保存完整结果
    for t in gt_texts:
        result = extractor.classify(t)
        ext_labels.append(result.emotion_label)
        ext_results.append(result)
    
    # 旧规则系统标注
    old_labels = []
    for t in gt_texts:
        em = tagger.tag(t)
        old_labels.append(em)
    
    # 计算 F1
    ext_f1s, ext_macro = calc_f1(gt_labels, ext_labels, emotions)
    old_f1s, old_macro = calc_f1(gt_labels, old_labels, emotions)
    
    print("=" * 65)
    print("EmotionExtractor vs 旧规则系统 F1 对比")
    print("=" * 65)
    print(f"{'情绪':<10} {'旧规则':>8} {'EmotionExtractor':>18} {'提升':>8}")
    print("-" * 50)
    
    for em in emotions:
        old = old_f1s.get(em, 0)
        ext = ext_f1s.get(em, 0)
        diff = ext - old
        sign = "+" if diff >= 0 else ""
        print(f"{em:<10} {old:>8.3f} {ext:>18.3f} {sign}{diff:>7.3f}")
    
    print("-" * 50)
    print(f"{'Macro F1':<10} {old_macro:>8.3f} {ext_macro:>18.3f} {sign}{ext_macro - old_macro:>7.3f}")
    
    # 逐条对比（全部）
    print(f"\n=== 逐条对比（全部 {len(gt_texts)} 条） ===")
    for i in range(len(gt_texts)):
        text = gt_texts[i][:30]
        gt = gt_labels[i]
        old = old_labels[i]
        ext = ext_labels[i]
        old_ok = "✅" if old == gt else "❌"
        ext_ok = "✅" if ext == gt else "❌"
        print(f"  [{i+1:2d}] {text:<30} GT={gt:<10} 旧={old:<10}{old_ok}  新={ext:<10}{ext_ok}")


if __name__ == "__main__":
    main()
