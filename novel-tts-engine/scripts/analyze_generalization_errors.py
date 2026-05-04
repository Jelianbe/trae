# -*- coding: utf-8 -*-
"""逐条回溯 20 条泛化错误，分析误判原因"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.emotion_extractor import EmotionExtractor


def analyze_scores(extractor: EmotionExtractor, text: str):
    """分析文本的得分情况"""
    features = extractor.extract_features(text)
    
    scores = {
        'joy': 0.0,
        'anger': 0.0,
        'sadness': 0.0,
        'surprise': 0.0,
        'fear': 0.0,
        'neutral': 0.0,
    }
    
    import re
    
    # ANGER
    if features.has_dirty_words:
        scores['anger'] += 0.5
    if features.exclamation_density > 0.3 and features.is_imperative:
        scores['anger'] += 0.3
    if features.is_imperative and features.exclamation_count >= 1:
        if '过来' not in text and '伤害' not in text and '别伤害' not in text:
            scores['anger'] += 0.15
    if features.has_emotion_verb:
        scores['anger'] += 0.2
    if features.has_short_sentences and features.exclamation_count >= 2:
        scores['anger'] += 0.2
    if re.search(r'(河东|河西|放肆|狂妄|大胆|岂敢)', text):
        scores['anger'] += 0.4
    if re.search(r'(死无葬身之地|自寻死路|找死|活腻|不得好死|碎尸万段|千刀万剐)', text):
        scores['anger'] += 0.5
    if re.search(r'(背叛|叛徒|逆贼|谋反|造反)', text):
        scores['anger'] += 0.4
    if re.search(r'(恨|仇恨|仇人|仇家|血债|血海深仇)', text):
        scores['anger'] += 0.4
    
    # FEAR
    if features.has_emotion_verb and ('颤抖' in text or '发抖' in text or '哆嗦' in text):
        scores['fear'] += 0.4
    if features.ellipsis_count >= 2:
        scores['fear'] += 0.2
    if features.has_short_sentences and features.question_count >= 1:
        scores['fear'] += 0.2
    if '害怕' in text or '恐惧' in text or '别伤害' in text:
        scores['fear'] += 0.3
    if ('不要' in text or '别' in text) and (features.ellipsis_count >= 1 or features.question_count >= 1):
        if '离开' in text or '对不起' in text or '难过' in text:
            scores['sadness'] += 0.3
        else:
            scores['fear'] += 0.3
    if '不要过来' in text or '别过来' in text:
        scores['fear'] += 0.4
    if '恐怖' in text:
        scores['fear'] += 0.4
    if re.search(r'(饶命|求饶|饶了我|放过|不要杀|别杀|救命|求求)', text):
        scores['fear'] += 0.5
    if re.search(r'(危险|快跑|逃命|躲开|小心)', text):
        scores['fear'] += 0.4
    
    # SADNESS
    if text.startswith(('唉', '呜', '呜呜', '唉声叹气')):
        scores['sadness'] += 0.3
    if features.ellipsis_count >= 1:
        scores['sadness'] += 0.2
    if features.has_emotion_adverb and ('不禁' in text or '不由' in text):
        scores['sadness'] += 0.2
    if '难过' in text or '离开' in text or '对不起' in text:
        scores['sadness'] += 0.2
    if re.search(r'(最后一面|见不到|回不去|再也见|永别|死别|生离)', text):
        scores['sadness'] += 0.5
    if re.search(r'(遗憾|后悔|来不及|没能|本该|早知道)', text):
        scores['sadness'] += 0.4
    if re.search(r'(哭|泪|泣|泪流|泪如|泪下|落泪|掉泪)', text):
        scores['sadness'] += 0.4
    if re.search(r'(我的儿|我的孩|我的女|我的妻|我的夫|儿啊|孩儿|女儿啊)', text):
        scores['sadness'] += 0.5
    if re.search(r'(走吧|放手|成全|趁我|别管我)', text):
        scores['sadness'] += 0.3
    
    # SURPRISE
    if features.is_rhetorical:
        scores['surprise'] += 0.3
    if features.question_count >= 2:
        scores['surprise'] += 0.2
    if re.search(r'(怎么|居然|竟然|天哪|什[么幺]|竟然复活)', text):
        scores['surprise'] += 0.4
    if features.exclamation_count >= 2 and not features.has_dirty_words:
        scores['surprise'] += 0.2
    if re.search(r'这.*[！!]', text) and features.exclamation_count >= 1:
        scores['surprise'] += 0.1
    if re.search(r'太(可怕|厉害|惊人|恐怖|强大)了', text):
        scores['surprise'] += 0.4
    if '还活着' in text or '没死' in text or '不敢相信' in text:
        scores['surprise'] += 0.4
    if re.search(r'(竟然|居然)', text):
        scores['surprise'] += 0.3
    if re.search(r'(难道|怎会|怎可能|怎么可能)', text):
        scores['surprise'] += 0.4
    if re.search(r'真的[……?？]', text):
        scores['surprise'] += 0.3
    
    # JOY
    if features.is_exclamatory:
        scores['joy'] += 0.4
    if features.exclamation_density > 0.3 and not features.has_dirty_words and not features.is_imperative:
        scores['joy'] += 0.2
    if re.search(r'(哈哈|呵呵|嘻嘻|大笑|微笑)', text):
        scores['joy'] += 0.3
    if features.has_repetition:
        scores['joy'] += 0.1
    if re.search(r'(完美|赢了|太好了|太棒了)', text):
        scores['joy'] += 0.3
    if text.startswith('哼') and ('本事' in text or '就这' in text or '这点' in text):
        scores['joy'] += 0.4
    if '笑' in text and not ('冷笑' in text or '嘲笑' in text):
        scores['joy'] += 0.2
    if re.search(r'(冠军|胜利|赢了|成功|终于|梦寐以求|喜事|好消息)', text):
        scores['joy'] += 0.5
    if re.search(r'(恭喜|祝贺|庆祝|万岁|干杯|庆祝)', text):
        scores['joy'] += 0.4
    if re.search(r'(幸福|满足|开心|高兴|快乐|美好)', text):
        scores['joy'] += 0.4
    
    # NEUTRAL
    neutral_score = 0.0
    if text.endswith('。') and features.exclamation_count == 0 and features.question_count == 0:
        neutral_score += 0.2
    has_emotion_signals = (
        features.has_dirty_words or 
        features.has_emotion_verb or 
        features.has_emotion_adverb or
        features.is_exclamatory or
        features.is_rhetorical or
        features.is_imperative
    )
    if not has_emotion_signals:
        neutral_score += 0.2
    neutral_score = min(neutral_score, 0.5)
    scores['neutral'] = neutral_score
    
    return scores, features


def main():
    gt_path = Path(__file__).parent.parent / 'tests' / 'emotion_gt_generalization.json'
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    
    extractor = EmotionExtractor()
    
    print("=" * 100)
    print("20条泛化样本逐条错误分析")
    print("=" * 100)
    
    error_types = {
        'neutral_抢分': [],
        'surprise_误触发': [],
        'anger_误触发': [],
        '情绪词缺失': [],
        '上下文依赖': [],
    }
    
    for item in gt_data:
        text = item['text']
        gt_l1 = item['emotion_class']
        gt_l2 = item['emotion_label']
        
        result = extractor.classify(text)
        pred_l1 = result.emotion_class
        pred_l2 = result.emotion_label
        
        scores, features = analyze_scores(extractor, text)
        
        is_error = (gt_l1 != pred_l1 or gt_l2 != pred_l2)
        
        if is_error:
            print(f"\n{'─' * 100}")
            print(f"ID: {item['id']}")
            print(f"文本: {text}")
            print(f"GT: {gt_l1}/{gt_l2}  →  预测: {pred_l1}/{pred_l2}")
            print(f"挑战点: {item.get('challenge', 'N/A')}")
            print(f"\n特征:")
            print(f"  - 感叹号: {features.exclamation_count}, 问号: {features.question_count}, 省略号: {features.ellipsis_count}")
            print(f"  - 脏话: {features.has_dirty_words}, 情绪动词: {features.has_emotion_verb}, 情绪副词: {features.has_emotion_adverb}")
            print(f"  - 感叹句: {features.is_exclamatory}, 反问句: {features.is_rhetorical}, 祈使句: {features.is_imperative}")
            print(f"\n得分:")
            for emo, score in sorted(scores.items(), key=lambda x: -x[1]):
                marker = " ← 最高" if emo == pred_l2 else ""
                gt_marker = " ← GT" if emo == gt_l2 else ""
                print(f"  {emo}: {score:.2f}{marker}{gt_marker}")
            
            # 错误分类
            if scores['neutral'] >= 0.2 and pred_l2 == 'neutral':
                error_types['neutral_抢分'].append(item['id'])
            if scores['surprise'] > 0 and pred_l2 == 'surprise' and gt_l2 != 'surprise':
                error_types['surprise_误触发'].append(item['id'])
            if scores['anger'] > 0 and pred_l2 == 'anger' and gt_l2 != 'anger':
                error_types['anger_误触发'].append(item['id'])
            
            # 检查是否情绪词缺失
            max_other_score = max(scores[gt_l2], scores['neutral'])
            if max_other_score < 0.3:
                error_types['情绪词缺失'].append(item['id'])
            
            # 检查是否上下文依赖
            if '表面' in item.get('challenge', '') or '上下文' in item.get('challenge', '') or '语境' in item.get('challenge', ''):
                error_types['上下文依赖'].append(item['id'])
    
    print(f"\n{'=' * 100}")
    print("错误类型统计")
    print("=" * 100)
    for error_type, ids in error_types.items():
        print(f"{error_type}: {len(ids)} 条")
        if ids:
            print(f"  样本: {ids}")


if __name__ == '__main__':
    main()
