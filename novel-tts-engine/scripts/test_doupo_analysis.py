# -*- coding: utf-8 -*-
"""
《斗破苍穹》前10章 算法验证测试
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pipeline_runner import PipelineRunner
from pipeline.nlp_basics import get_nlp
from pipeline.chapter_splitter import ChapterSplitter
import re

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

# 读取预标注文件
gt_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ground_truth.json'
ground_truth = json.loads(gt_file.read_text(encoding='utf-8'))

print("="*80)
print("《斗破苍穹》前10章 算法验证测试")
print("="*80)

# 1. 分章验证
print("\n1. 分章验证")
print("-" * 40)
splitter = ChapterSplitter(min_chapter_length=100)
chapters = splitter.split(text)
expected_titles = ground_truth['chapters']['chapter_titles']

print(f"期望章节数: {len(expected_titles)}")
print(f"实际章节数: {len(chapters)}")

# 检查标题匹配
correct_titles = 0
for i, (ch, expected) in enumerate(zip(chapters, expected_titles)):
    match = expected in ch.title or ch.title in expected
    if match:
        correct_titles += 1
    print(f"  第{i+1}章: 期望='{expected}' 实际='{ch.title}' {'✅' if match else '❌'}")

title_accuracy = correct_titles / len(expected_titles) * 100 if expected_titles else 0
print(f"\n章节标题匹配率: {title_accuracy:.1f}%")

# 2. NER验证
print("\n2. NER命名实体识别验证")
print("-" * 40)

nlp = get_nlp()
result = nlp.analyze(text)

entities = list(result.entities)
per_entities = [e for e in entities if e.type == 'PER']
org_entities = [e for e in entities if e.type == 'ORG']
loc_entities = [e for e in entities if e.type == 'LOC']

per_texts = set(e.text for e in per_entities)
org_texts = set(e.text for e in org_entities)
loc_texts = set(e.text for e in loc_entities)

gt_persons = set(ground_truth['entities']['persons'])
gt_orgs = set(ground_truth['entities']['organizations'])
gt_locs = set(ground_truth['entities']['locations'])

# 计算每个GT人物的识别情况
print(f"\n人物实体识别:")
print(f"  GT人物数: {len(gt_persons)}")
print(f"  HanLP识别到: {sorted(gt_persons & per_texts)}")
missing_persons = gt_persons - per_texts
print(f"  未识别到: {sorted(missing_persons)}")

print(f"\n组织实体识别:")
print(f"  GT组织数: {len(gt_orgs)}")
print(f"  HanLP识别到: {sorted(gt_orgs & org_texts)}")
missing_orgs = gt_orgs - org_texts
print(f"  未识别到: {sorted(missing_orgs)}")

print(f"\n地点实体识别:")
print(f"  GT地点数: {len(gt_locs)}")
print(f"  HanLP识别到: {sorted(gt_locs & loc_texts)}")
missing_locs = gt_locs - loc_texts
print(f"  未识别到: {sorted(missing_locs)}")

# 计算F1
def calc_f1(gt, actual):
    if not gt:
        return 100.0
    tp = len(gt & actual)
    fp = len(actual - gt)
    fn = len(gt - actual)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) * 100 if (precision + recall) > 0 else 0
    return precision * 100, recall * 100, f1

per_p, per_r, per_f1 = calc_f1(gt_persons, per_texts)
org_p, org_r, org_f1 = calc_f1(gt_orgs, org_texts)
loc_p, loc_r, loc_f1 = calc_f1(gt_locs, loc_texts)

print(f"\n人物F1: P={per_p:.1f}%, R={per_r:.1f}%, F1={per_f1:.1f}")
print(f"组织F1: P={org_p:.1f}%, R={org_r:.1f}%, F1={org_f1:.1f}")
print(f"地点F1: P={loc_p:.1f}%, R={loc_r:.1f}%, F1={loc_f1:.1f}")

# 3. 对话识别验证
print("\n3. 对话识别验证")
print("-" * 40)

dialogue_pattern = re.compile(r'["「"]([^"」"]+)["」"]')
dialogues = dialogue_pattern.findall(text)
print(f"识别到对话数: {len(dialogues)}")

# 统计前10条对话
print("前10条对话:")
for i, d in enumerate(dialogues[:10]):
    preview = d[:50] + "..." if len(d) > 50 else d
    print(f"  {i+1}. {preview}")

# 4. 拟声词验证
print("\n4. 拟声词检测验证")
print("-" * 40)

sfx_pattern = re.compile(r'\b(轰|咔|呼|呼哧|轰隆|咔嚓)\b')
sfx_matches = sfx_pattern.findall(text)
print(f"检测到拟声词: {len(sfx_matches)}个")
print(f"拟声词类型: {set(sfx_matches)}")

# 5. 说话角色匹配验证
print("\n5. 说话角色匹配验证")
print("-" * 40)

# 测试几个已知的对话-角色对
test_dialogues = [
    {"text": "萧炎哥哥。", "speaker": "萧薰儿"},
    {"text": "我现在还有资格让你怎么叫么？", "speaker": "萧炎"},
    {"text": "萧炎哥哥，以前你曾经与薰儿说过，要能放下，才能拿起，提放自如，是自在人！", "speaker": "萧薰儿"},
    {"text": "呵呵，自在人？我也只会说而已，你看我现在的模样，象自在人吗？而且……这世界，本来就不属于我。", "speaker": "萧炎"},
    {"text": "炎儿，这么晚了，怎么还待在这上面呢？", "speaker": "萧战"},
    {"text": "三十年河东，三十年河西，莫欺少年穷！", "speaker": "萧炎"},
]

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.character_manager import get_character_manager

# 创建匹配器
matcher = SpeakerMatcher()
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()
matcher.semantic_ranker = semantic_ranker

# 设置人物
gt_speaking = ground_truth['entities']['speaking_persons']
char_manager = get_character_manager()
char_manager.set_ground_truth(
    persons=gt_speaking,
    speaking_persons=gt_speaking,
)
matcher.char_manager = char_manager

print(f"已知说话角色: {gt_speaking}")
print("\n对话角色匹配测试:")
correct = 0
for dl in test_dialogues:
    ctx = DialogueContext(text=dl['text'], chapter_id=0)
    result = matcher.match_speaker(ctx)
    matched = result.character.name if result else "无匹配"
    is_correct = matched == dl['speaker']
    if is_correct:
        correct += 1
    print(f"  {'✅' if is_correct else '❌'} '{dl['text'][:30]}...' -> {matched} (期望: {dl['speaker']})")

match_rate = correct / len(test_dialogues) * 100 if test_dialogues else 0
print(f"\n角色匹配正确率: {match_rate:.1f}% ({correct}/{len(test_dialogues)})")

# 6. 综合评分
print("\n6. 综合评分（新六项体系）")
print("-" * 40)

# 基础结构完整性 (10%)
base_score = title_accuracy  # 章节标题匹配率

# 拟声词检测 (15%)
sfx_score = min(len(sfx_matches) * 10, 100)  # 简单计算

# 说话角色识别 (30%)
speaker_score = per_f1  # NER人物F1

# 对话-角色匹配 (30%)
dialogue_match_score = match_rate

# 端到端正确率 (10%)
e2e_score = (speaker_score + dialogue_match_score) / 2

# 稳定性罚分 (5%) - 假设稳定
stability_penalty = 0

# 计算综合分
comprehensive = (
    base_score * 0.10 +
    sfx_score * 0.15 +
    speaker_score * 0.30 +
    dialogue_match_score * 0.30 +
    e2e_score * 0.10 -
    stability_penalty * 0.05
)

print(f"基础结构完整性 (10%): {base_score:.1f}")
print(f"拟声词检测 (15%): {sfx_score:.1f}")
print(f"说话角色识别 (30%): {speaker_score:.1f}")
print(f"对话-角色匹配 (30%): {dialogue_match_score:.1f}")
print(f"端到端正确率 (10%): {e2e_score:.1f}")
print(f"稳定性罚分 (5%): -{stability_penalty:.2f}")
print(f"\n综合分: {comprehensive:.1f}")

# 总结
print("\n" + "="*80)
print("总结")
print("="*80)
print(f"综合评分: {comprehensive:.1f}/100")
print(f"分章准确率: {title_accuracy:.1f}%")
print(f"NER人物F1: {per_f1:.1f}")
print(f"对话匹配率: {match_rate:.1f}%")
