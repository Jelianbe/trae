# -*- coding: utf-8 -*-
"""LLM 说话人识别 Benchmark - 约束选择题

目标：评估 Qwen2.5-1.5B-Instruct 在小说对话说话人识别任务上的能力。

任务设计：
- 从100条中筛选 speaker 非"未知"的条目（约40-50条）
- 构造候选人列表（从上下文中提取PER实体 + GT speaker + "其他角色"）
- 让LLM从候选人中选择最可能的说话人

用法：
    python scripts/llm_speaker_benchmark.py
"""

# === 必须在导入 transformers 之前设置镜像 ===
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
import re
import sys
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


VERB_CHARS = '推拉打跑跳走说问道喊叫看听想笑哭站立坐睡拿放开关进出望凝视盯瞥瞪望注视观察发现察觉感觉觉得以为认为知道明白清楚理解懂得了解认识熟悉掌握精通擅长善于习惯适应适应接受承受承担担当负责管理控制掌握操纵摆布支配影响改变调整修改修正完善补充加强增强提高提升增加减少降低缩小扩大扩展延伸发展进步成长成熟衰老死亡消失出现存在保持维持继续持续停止中断暂停休息放松睡眠醒来起床洗漱穿戴打扮装饰化妆打扮整理收拾清理打扫清洗擦拭擦抹涂抹擦刷洗浸泡浸泡晾干晒干烘干烘烤烧烤烹调烹饪炒煮炖熬煎炸蒸烤焗焖烧煨炖煲煸爆炒烹炸烩烧焖炖熬煮煎炒烹炸'

PER_EXCLUDE = {'众人', '他们', '我们', '你们', '大家', '有人', '那人', '这人',
               '一人', '两人', '三人', '四人', '五人', '所有人', '任何人',
               '中年', '青年', '老年', '年轻', '黑色', '白色', '红色', '蓝色',
               '突然', '然后', '虽然', '但是', '已经', '正在', '终于',
               '其他角色', '路人', '旁观者', '旁白'}


def load_gt_data(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _is_valid_name(text: str) -> bool:
    """检查一个字符串是否是有效的人名。

    过滤规则：
    1. 不能是停用词
    2. 不能包含动词/形容词后缀（如"林雪看"、"病床上的"）
    3. 长度 2-4 个汉字
    """
    if text in PER_EXCLUDE:
        return False

    if not re.match(r'^[\u4e00-\u9fff]{2,4}$', text):
        return False

    for char in text:
        if char in VERB_CHARS:
            return False

    bad_suffixixes = ['的', '了', '着', '过', '被', '把', '给', '和', '与', '及', '或']
    for suffix in bad_suffixixes:
        if text.endswith(suffix) and len(text) > 2:
            return False

    return True


def extract_per_entities(text: str) -> list:
    """从文本中提取中文人名（PER实体）。

    改进：使用严格的动词后缀过滤，避免把"林雪看"、"病床上的"等混入候选人。
    """
    if not text:
        return []

    names = set()

    title_words = {
        '将军', '骑士', '修士', '弟子', '丫鬟', '总管', '丞相', '陛下', '王爷',
        '公子', '小姐', '先生', '前辈', '老者', '老人', '杀手', '道士', '法师',
        '剑客', '刺客', '卫士', '士兵', '队长', '侍卫', '护卫', '武士', '侠客',
        '英雄', '魔尊', '教主', '帮主', '掌门', '长老', '执事', '堂主', '舵主',
        '镖师', '郎中', '大夫', '掌柜', '小二', '酒客', '村民', '农夫', '猎户',
        '樵夫', '渔夫', '船夫', '车夫', '马夫', '轿夫', '和尚', '尼姑', '书生',
        '秀才', '举人', '进士', '状元', '探花', '榜眼', '宰相', '太监', '贵妃',
        '皇后', '太子', '皇子', '公主', '郡主', '王妃', '夫人', '太太',
        '妈妈', '爸爸', '儿子', '女儿', '哥哥', '弟弟', '姐姐', '妹妹',
        '叔叔', '阿姨', '舅舅', '姑姑', '伯伯', '婆婆', '公公', '媳妇', '女婿',
        '孙子', '孙女', '侄子', '侄女', '外甥', '外甥女', '徒弟', '师傅', '师父',
        '师娘', '师兄', '师弟', '师姐', '师妹', '师伯', '师叔', '师祖', '徒孙',
        '教头', '教练', '裁判', '医生', '护士', '药师', '医师', '医官', '太医',
        '御医', '军医', '统帅', '元帅', '大将', '副将', '偏将', '先锋', '斥候',
        '探子', '间谍', '密探', '信使', '使者', '特使', '钦差', '宦官', '宫人',
        '宫女', '保镖', '打手', '喽啰', '小卒', '小兵', '军人', '武官', '文官',
        '官员', '大臣', '尚书', '侍郎', '御史', '知府', '县令', '知县', '知州',
        '刺史', '巡抚', '总督', '巡按', '按察', '提督', '总兵', '参将', '游击',
        '都司', '守备', '千总', '把总', '主席', '总统', '总理', '部长', '局长',
        '处长', '科长', '主任', '副主任', '委员', '代表', '议员', '参事', '顾问',
        '专家', '学者', '教授', '副教授', '讲师', '助教', '研究员', '副研究员',
        '助理', '秘书', '干事', '职员', '员工', '工人', '农民', '商人', '老板',
        '经理', '总裁', '董事', '股东', '合伙人', '创始人', '发起人', '管家',
        '老爷', '夫人', '少爷', '姑娘', '掌柜', '执事', '导师', '学长', '姑娘',
        '男子', '女子', '男人', '女人', '少年', '青年', '中年', '老年',
    }

    for title in title_words:
        pattern = re.compile(r'([\u4e00-\u9fff]{1,4})' + re.escape(title))
        for match in pattern.finditer(text):
            core = match.group(1)
            if _is_valid_name(core):
                names.add(core)
            full = core + title
            if _is_valid_name(full):
                names.add(full)

    verbs = '说|道|问|答|回答|喊|叫|喊道|叫道|喝道|说道|问道|答道|笑着|哭着|叹气|叹息|摇头|点头|摆手|挥手|转身|回头|望着|看着|盯着|瞧着|听着'
    pattern2 = re.compile(r'([\u4e00-\u9fff]{2,4})(?:' + verbs + ')')
    for match in pattern2.finditer(text):
        name = match.group(1)
        if _is_valid_name(name):
            names.add(name)

    pattern3 = re.findall(r'[\u4e00-\u9fff]{2,4}·[\u4e00-\u9fff]{2,4}(?:·[\u4e00-\u9fff]{2,4})?', text)
    for match in pattern3:
        names.add(match)

    return list(names)


def build_candidate_list(item: dict) -> list:
    """构造候选人列表"""
    candidates = set()

    # 1. 从上下文中提取PER实体
    context_before = item.get('context_before', '')
    context_after = item.get('context_after', '')
    
    extracted_names = extract_per_entities(context_before) + extract_per_entities(context_after)
    candidates.update(extracted_names)

    # 2. 添加GT speaker
    gt_speaker = item.get('speaker', '')
    if gt_speaker and gt_speaker != '未知' and '/' not in gt_speaker:
        candidates.add(gt_speaker)

    # 3. 添加"其他角色"选项
    candidates.add('其他角色')

    # 4. 限制在3-6人
    candidate_list = list(candidates)
    if len(candidate_list) > 6:
        # 保留GT speaker和"其他角色"，随机删除多余的
        must_keep = [gt_speaker, '其他角色'] if gt_speaker != '未知' else ['其他角色']
        must_keep = [c for c in must_keep if c in candidate_list]
        others = [c for c in candidate_list if c not in must_keep]
        random.shuffle(others)
        needed = 6 - len(must_keep)
        candidate_list = must_keep + others[:needed]
    elif len(candidate_list) < 3:
        # 补足到3个
        # 可以添加一些常见角色名
        fill_names = ['路人', '旁观者', '旁白']
        for name in fill_names:
            if len(candidate_list) >= 3:
                break
            if name not in candidate_list:
                candidate_list.append(name)

    # 5. 随机打乱（避免位置偏见）
    random.shuffle(candidate_list)

    return candidate_list


def filter_items(gt_data: list) -> list:
    """筛选出适合LLM测试的条目"""
    filtered = []
    for item in gt_data:
        speaker = item.get('speaker', '')
        
        # 排除speaker为"未知"或"未知_XXX"的
        if speaker.startswith('未知'):
            continue
        
        # 对于包含"/"的（如"店小二/酒客"），GT取第一个
        if '/' in speaker:
            item['speaker'] = speaker.split('/')[0]
        
        filtered.append(item)
    
    return filtered


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


def build_system_prompt() -> str:
    return """你是一个小说对话解析引擎。你的任务是根据上下文和对话内容，推断最可能的说话人。

规则：
1. 只能从候选人列表中选择
2. 仔细分析上下文中的动作、称呼、心理活动等线索
3. 如果候选人都不像，选择"其他角色"

示例1（都市）：
上文：苏夜站在门口，脸色铁青。
对话：「你给我滚出去！」
下文：林雪愣住了，她从没见过苏夜这样。

可能的说话人：
1. 林雪
2. 苏夜
3. 其他角色

答案：2. 苏夜

示例2（修仙）：
上文：林轩单膝跪地，已经站不起来了。
对话：「不必管我！你们快走！」
下文：身后的追兵杀声越来越近。

可能的说话人：
1. 同伴
2. 林轩
3. 其他角色

答案：2. 林轩"""


def build_user_prompt(item: dict, candidates: list) -> str:
    context_before = item.get('context_before', '')
    context_after = item.get('context_after', '')
    text = item['text']

    context_parts = []
    if context_before:
        context_parts.append(context_before)
    context_parts.append(f"[对话] {text}")
    if context_after:
        context_parts.append(context_after)

    context_str = "\n".join(context_parts)

    candidate_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])

    return f"""上下文：
{context_str}

可能的说话人：
{candidate_str}

请选择最可能的说话人（只输出编号和姓名，如"3. 萧炎"）。"""


def parse_speaker_prediction(response: str, candidates: list) -> str:
    """解析LLM的输出，提取选择的说话人。

    优先级：
    1. 如果LLM输出匹配"编号. 姓名"格式，用姓名字段精确匹配候选人
    2. 精确匹配失败后，尝试最长前缀匹配（避免"巡"吃掉"巡逻队长"）
    3. 用编号索引兜底
    4. 默认"其他角色"
    """
    response = response.strip()

    match = re.match(r'^(\d+)\.\s*(.+)', response)
    if match:
        index = int(match.group(1))
        name = match.group(2).strip()

        # 1. 精确匹配
        for c in candidates:
            if c == name:
                return c

        # 2. 最长前缀匹配（按候选人长度降序，避免短前缀吞掉长名字）
        sorted_candidates = sorted(candidates, key=len, reverse=True)
        for c in sorted_candidates:
            if c.startswith(name) or name.startswith(c):
                return c

        # 3. 兜底：用编号
        if 1 <= index <= len(candidates):
            return candidates[index - 1]

    # 4. 直接匹配候选人名字（最长匹配优先）
    sorted_candidates = sorted(candidates, key=len, reverse=True)
    for candidate in sorted_candidates:
        if candidate in response:
            return candidate

    return "其他角色"


def llm_predict_speaker(model, tokenizer, device, item: dict, candidates: list) -> str:
    import torch

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(item, candidates)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_input, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False,
            temperature=0.0,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    response = response.strip()

    return parse_speaker_prediction(response, candidates), response


def main():
    import torch

    print("=" * 70)
    print("LLM 说话人识别 Benchmark")
    print("模型: Qwen2.5-1.5B-Instruct")
    print("任务: 约束选择题（从候选人中选择说话人）")
    print("测试集: role_emotion_gt_100.json（筛选后）")
    print("=" * 70)
    print()

    # 加载数据
    project_root = Path(__file__).parent.parent
    gt_path = project_root / "tests" / "role_emotion_gt_100.json"

    gt_data = load_gt_data(gt_path)
    print(f"原始数据集: {len(gt_data)} 条")

    # 筛选
    filtered_data = filter_items(gt_data)
    print(f"筛选后数据集: {len(filtered_data)} 条")
    print(f"文体分布: 都市{sum(1 for d in filtered_data if d['style'] == '都市')} + "
          f"西幻{sum(1 for d in filtered_data if d['style'] == '西幻')} + "
          f"修仙{sum(1 for d in filtered_data if d['style'] == '修仙')} + "
          f"历史{sum(1 for d in filtered_data if d['style'] == '历史')}")
    print()

    # 加载模型
    model, tokenizer, device = load_model()
    print()

    # 开始测试
    print("=" * 70)
    print("开始 LLM 说话人识别测试...")
    print("=" * 70)

    results = []
    correct_count = 0
    total_time = 0

    # 按文体分类统计
    style_stats = {}
    # 按难度分类统计
    difficulty_stats = {}

    for i, item in enumerate(filtered_data):
        gt_speaker = item['speaker']
        text = item['text']

        # 构造候选人列表
        candidates = build_candidate_list(item)

        start_time = time.time()
        pred_speaker, raw_response = llm_predict_speaker(model, tokenizer, device, item, candidates)
        elapsed = time.time() - start_time
        total_time += elapsed

        is_correct = (pred_speaker == gt_speaker)
        if is_correct:
            correct_count += 1

        # 文体统计
        style = item.get('style', '未知')
        if style not in style_stats:
            style_stats[style] = {'correct': 0, 'total': 0}
        style_stats[style]['total'] += 1
        if is_correct:
            style_stats[style]['correct'] += 1

        # 难度统计（基于role_challenge）
        role_challenge = item.get('role_challenge', '')
        if '代词消解' in role_challenge:
            diff_key = '代词消解'
        elif '显式提示' in role_challenge:
            diff_key = '显式提示'
        elif '别名' in role_challenge or '映射' in role_challenge:
            diff_key = '别名映射'
        else:
            diff_key = '其他'

        if diff_key not in difficulty_stats:
            difficulty_stats[diff_key] = {'correct': 0, 'total': 0}
        difficulty_stats[diff_key]['total'] += 1
        if is_correct:
            difficulty_stats[diff_key]['correct'] += 1

        match = "✅" if is_correct else "❌"
        print(f"  [{i+1:3d}/{len(filtered_data)}] {text[:20]:<20} GT={gt_speaker:<10} LLM={pred_speaker:<10} {match} ({elapsed:.1f}s)")

        results.append({
            "id": item['id'],
            "text": text,
            "style": style,
            "gt_speaker": gt_speaker,
            "pred_speaker": pred_speaker,
            "candidates": candidates,
            "raw_response": raw_response,
            "correct": is_correct,
            "role_challenge": role_challenge,
        })

    # 计算准确率
    accuracy = correct_count / len(filtered_data) if filtered_data else 0
    avg_time = total_time / len(filtered_data) if filtered_data else 0

    print()
    print(f"总耗时: {total_time:.1f}s, 平均: {avg_time:.1f}s/条")
    print()

    # 汇总结果
    print("=" * 70)
    print("LLM 说话人识别评估结果")
    print("=" * 70)
    print(f"测试条目数: {len(filtered_data)}")
    print(f"正确数: {correct_count}")
    print(f"错误数: {len(filtered_data) - correct_count}")
    print(f"准确率: {accuracy:.1%}")
    print()

    # 与规则系统对比
    print("=" * 70)
    print("对比：LLM vs 规则系统")
    print("=" * 70)
    print(f"规则系统准确率: 63.0%")
    print(f"LLM 准确率:       {accuracy:.1%}")
    
    if accuracy >= 0.63:
        diff = accuracy - 0.63
        print(f"LLM 优势: +{diff:.1%}")
    else:
        diff = 0.63 - accuracy
        print(f"LLM 劣势: -{diff:.1%}")
    print()

    # 按文体细分
    print("=" * 70)
    print("按文体细分")
    print("=" * 70)
    print(f"{'文体':<8} {'正确':>6} {'总数':>6} {'准确率':>8}")
    print("-" * 30)
    for style, stats in sorted(style_stats.items()):
        style_acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"{style:<8} {stats['correct']:>6} {stats['total']:>6} {style_acc:>7.1%}")
    print()

    # 按难度细分
    print("=" * 70)
    print("按难度细分")
    print("=" * 70)
    print(f"{'难度类型':<12} {'正确':>6} {'总数':>6} {'准确率':>8}")
    print("-" * 30)
    for diff, stats in sorted(difficulty_stats.items()):
        diff_acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"{diff:<12} {stats['correct']:>6} {stats['total']:>6} {diff_acc:>7.1%}")
    print()

    # 错误分析 + 分类
    print("=" * 70)
    print("错误分析")
    print("=" * 70)
    errors = [r for r in results if not r['correct']]
    error_categories = {'解析Bug': 0, '候选人污染': 0, 'LLM推理错误': 0}
    for err in errors:
        gt = err['gt_speaker']
        raw = err['raw_response']
        pred = err['pred_speaker']
        candidates = err['candidates']

        # 分类1: 解析Bug — raw_response 中包含 GT speaker 但解析结果不是 GT
        if gt in raw:
            err['error_type'] = '解析Bug'
            error_categories['解析Bug'] += 1
        # 分类2: 候选人污染 — GT speaker 不在候选人列表中
        elif gt not in candidates:
            err['error_type'] = '候选人污染'
            error_categories['候选人污染'] += 1
        else:
            err['error_type'] = 'LLM推理错误'
            error_categories['LLM推理错误'] += 1

    print(f"共 {len(errors)} 条错误：")
    print(f"  解析Bug（LLM答对但脚本解析错）: {error_categories['解析Bug']}")
    print(f"  候选人污染（GT不在候选列表中）: {error_categories['候选人污染']}")
    print(f"  LLM真正推理错误: {error_categories['LLM推理错误']}")
    print()
    print("错误详情：")
    for err in errors:
        tag = f"[{err['error_type']}]"
        print(f"  {tag} [{err['id']}] {err['text'][:25]:<25} GT={err['gt_speaker']:<10} LLM={err['pred_speaker']:<10}")
        print(f"    候选人: {', '.join(err['candidates'])}")
        print(f"    原始输出: {err['raw_response'][:60]}")
    print()

    corrected_errors = error_categories['解析Bug'] + error_categories['候选人污染']
    corrected_correct = correct_count + error_categories['解析Bug']
    corrected_accuracy = corrected_correct / len(filtered_data) if filtered_data else 0

    # 保存结果
    result_path = project_root / "tests" / "llm_speaker_benchmark_result.json"
    output = {
        "model": "Qwen2.5-1.5B-Instruct",
        "total_items": len(filtered_data),
        "correct_count": correct_count,
        "error_count": len(filtered_data) - correct_count,
        "accuracy": accuracy,
        "error_classification": error_categories,
        "corrected_correct_count": corrected_correct,
        "corrected_accuracy": round(corrected_accuracy, 3),
        "avg_time_per_item": round(avg_time, 2),
        "total_time": round(total_time, 1),
        "rule_system_accuracy": 0.63,
        "style_breakdown": {
            style: {
                "correct": stats['correct'],
                "total": stats['total'],
                "accuracy": round(stats['correct'] / stats['total'], 3) if stats['total'] > 0 else 0
            }
            for style, stats in style_stats.items()
        },
        "difficulty_breakdown": {
            diff: {
                "correct": stats['correct'],
                "total": stats['total'],
                "accuracy": round(stats['correct'] / stats['total'], 3) if stats['total'] > 0 else 0
            }
            for diff, stats in difficulty_stats.items()
        },
        "results": results,
    }

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"结果已保存到: {result_path}")


if __name__ == "__main__":
    main()
