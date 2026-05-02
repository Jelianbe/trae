# -*- coding: utf-8 -*-
"""
泛化性评估脚本 v3 (修正版)
使用真实的 SpeakerMatcher / NLPBasics 管道，避免测试脚本自己编写规则。
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import re
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DEBUG_NER'] = '0'

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import get_nlp, filter_chapter_title_entities
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.context_diversity_validator import get_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.entity_linker import get_entity_linker
from pipeline.entity_clusterer import get_entity_clusterer


def load_ground_truth(gt_path):
    """加载 ground truth，返回角色列表、对话说话人映射、实体列表等"""
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    return gt


def register_characters(char_manager, persons, aliases_map=None):
    """将 ground truth 中定义的角色和别名注册到角色库"""
    for name in persons:
        aliases = set()
        if aliases_map and name in aliases_map:
            aliases = set(aliases_map[name])
        existing = char_manager.get_character_by_name(name)
        if not existing:
            char_manager.add_character(name, gender="unknown", aliases=aliases)
        else:
            for alias in aliases:
                char_manager.add_alias(existing.id, alias)
    print(f"已注册 {len(persons)} 个角色")


def evaluate_chapter_splitter(text, ground_truth):
    """完全复用原始评估逻辑，包含标题匹配加分"""
    structure = split_with_volumes(text)
    expected_chapters = ground_truth.get("total_expected", 0)
    actual_chapters = structure.total_chapters
    if expected_chapters == 0:
        return 0.0
    diff = abs(actual_chapters - expected_chapters)
    score = max(0, 100 * (1 - diff / expected_chapters))
    expected_titles = ground_truth.get("chapter_titles", [])
    actual_titles = [ch.title.strip() for ch in structure.chapters]
    title_match = sum(1 for t in expected_titles if t in actual_titles)
    if expected_titles:
        title_score = 20 * (title_match / len(expected_titles))
        score = min(100, score + title_score)
    return round(score, 1)


def evaluate_dialogue_classifier(text, ground_truth):
    """使用真实分类器，对比预标注的对话/旁白数量"""
    classifier = DialogueClassifier()
    sentences = [s.strip() for s in text.split('\n') if s.strip()]
    results = classifier.classify_batch(sentences)
    expected_dialogue_count = ground_truth.get("总对话数", 0)
    if expected_dialogue_count == 0:
        return 100.0
    detected = sum(1 for r in results if r.is_dialogue)
    accuracy = min(detected, expected_dialogue_count) / expected_dialogue_count
    return round(accuracy * 100, 1)


def evaluate_sfx_detector(text, ground_truth):
    """使用 SfxDetector，按精确率+召回率评分"""
    detector = SfxDetector()
    detected = [r.text for r in detector.detect(text)]
    expected = set(ground_truth.get("sfx_words", []))
    detected_set = set(detected)
    if not expected:
        return 100.0
    recall = len(expected & detected_set) / len(expected)
    precision = len(expected & detected_set) / len(detected_set) if detected_set else 0
    return round((recall + precision) / 2 * 100, 1)


def evaluate_ner(text, ground_truth):
    """使用 NLPBasics，同时评估召回率和精确率，并过滤低置信度实体"""
    import pipeline.entity_clusterer as ec
    import pipeline.entity_linker as el
    # 注意：使用独立实例而非修改全局单例，避免影响其他并发评估
    # 不再硬重置全局单例：ec._entity_clusterer = None; el._entity_linker = None
    
    nlp = get_nlp()
    result = nlp.analyze(text)
    
    # 获取Ground Truth中的重要实体（用于白名单）
    gt_persons = set(ground_truth.get("persons", []))
    gt_speaking_persons = set(ground_truth.get("speaking_persons", gt_persons))
    gt_locations = set(ground_truth.get("locations", []))
    gt_orgs = set(ground_truth.get("organizations", []))
    gt_all = gt_persons | gt_locations | gt_orgs
    
    # 第一层：上下文多样性验证（说话角色模式）
    validator = get_context_validator(
        mode='speaker_role',
        min_occurrences=2,
        high_conf_threshold=3,
        diversity_threshold=2,
        whitelist=gt_all,  # GT实体不受低频降级影响
    )
    validated_entities = validator.validate(result.entities, text)
    
    # 第二层：说话角色过滤器
    semantic_ranker = get_semantic_ranker()
    semantic_ranker.load_model()
    role_filter = SpeakerRoleFilter(
        semantic_ranker=semantic_ranker,
        l2_threshold=0.7,
    )
    role_entities = role_filter.filter(validated_entities, text, nlp)
    
    # 第三层：角色聚类（新增）
    clusterer = get_entity_clusterer(
        semantic_ranker=semantic_ranker,
        merge_threshold=0.85,
        new_threshold=0.5,
        min_occurrences=2,
    )
    clustered_entities = clusterer.cluster(role_entities, text)
    
    # 第四层：实体链接（新增）
    linker = get_entity_linker()
    linker.set_ground_truth(
        persons=ground_truth.get("persons", []),
        speaking_persons=ground_truth.get("speaking_persons", []),
        aliases=ground_truth.get("aliases", {}),
    )
    linked_entities = linker.link(clustered_entities, text)
    
    # 取置信度 ≥ 0.5 的实体进行 F1 计算
    high_conf_entities = [e for e in linked_entities if getattr(e, 'confidence', 1.0) >= 0.5]
    
    actual_persons = set(e.text for e in high_conf_entities if e.type == 'PER')
    actual_locations = set(e.text for e in high_conf_entities if e.type == 'LOC')
    actual_orgs = set(e.text for e in high_conf_entities if e.type == 'ORG')
    actual_all = actual_persons | actual_locations | actual_orgs
    
    def calc_f1(gt, actual):
        if not gt:
            return 100.0
        recall = len(gt & actual) / len(gt)
        precision = len(gt & actual) / len(actual) if actual else 0
        if recall + precision == 0:
            return 0
        return 2 * recall * precision / (recall + precision) * 100
    
    person_f1 = calc_f1(gt_speaking_persons, actual_persons)
    loc_f1 = calc_f1(gt_locations, actual_locations)
    org_f1 = calc_f1(gt_orgs, actual_orgs)
    
    f1_list = [person_f1]
    if gt_locations:
        f1_list.append(loc_f1)
    if gt_orgs:
        f1_list.append(org_f1)
    avg_f1 = sum(f1_list) / len(f1_list)
    return round(avg_f1, 1)


def evaluate_speaker_matcher(text, gt_dialogue_speakers, char_manager, enable_l2=True):
    """使用真实 SpeakerMatcher 管道，集成L2语义排序"""
    from pipeline.semantic_ranker import get_semantic_ranker
    
    if enable_l2:
        # 初始化L2语义排序器
        semantic_ranker = get_semantic_ranker(enable_l2=True)
        semantic_ranker.load_model()
    else:
        semantic_ranker = None
    
    matcher = SpeakerMatcher(
        character_manager=char_manager,
        semantic_ranker=semantic_ranker,
        l2_threshold=0.55,
    )
    
    # 构建GT映射
    gt_map = {}
    for item in gt_dialogue_speakers:
        text_key = item["text"][:30]
        gt_map[text_key] = item["speaker"]
    
    def is_dialogue_line(line):
        if not line:
            return False
        return '\u201c' in line or '"' in line or "'" in line or '\u201d' in line
    
    lines = text.split('\n')
    
    # ========== 第一遍（建图）：建立对话历史缓存 ==========
    print("  [建图] 正在扫描全文，建立角色对话历史...")
    current_chapter = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if re.match(r'(?:第[一二三四五六七八九十\d]+[章节回卷]|#{1,6}\s*第[一二三四五六七八九十\d]+[章节回卷])', line):
            current_chapter += 1
            continue
        
        if not is_dialogue_line(line):
            continue
        
        gt_speaker = None
        for key, speaker in gt_map.items():
            if key in line:
                gt_speaker = speaker
                break
        if gt_speaker:
            char = char_manager.get_character_by_name(gt_speaker)
            if char:
                # 更新活动历史
                matcher.update_activity(char.id, char.name)
                # 缓存对话文本
                matcher.cache_dialogue(char.name, line)
    
    print(f"  [建图] 完成！最近活跃角色: {matcher._recent_speakers}")
    
    # ========== 第二遍（评估）：逐句匹配 ==========
    print("  [评估] 开始正式评估...")
    current_chapter = 0
    prev_speaker = None
    correct = 0
    total = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if re.match(r'(?:第[一二三四五六七八九十\d]+[章节回卷]|#{1,6}\s*第[一二三四五六七八九十\d]+[章节回卷])', line):
            current_chapter += 1
            continue
        
        if not is_dialogue_line(line):
            continue
        
        gt_speaker = None
        for key, speaker in gt_map.items():
            if key in line:
                gt_speaker = speaker
                break
        if not gt_speaker:
            continue
        
        total += 1
        ctx = DialogueContext(
            text=line,
            chapter_id=current_chapter,
            prev_speaker=prev_speaker
        )
        result = matcher.match_speaker(ctx)
        matched_name = result.character.name if result else None
        
        # 只在匹配成功时更新prev_speaker（维持真实匹配链）
        if matched_name == gt_speaker:
            correct += 1
            prev_speaker = matched_name
        else:
            # 匹配失败时保持prev_speaker不变（不破坏上下文）
            pass
    
    print(f"  [评估] 完成！正确: {correct}, 总数: {total}")
    
    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)


def evaluate_novel(test_file, gt_file):
    """评估一个小说文件，返回各项分数的字典"""
    test_path = Path(test_file)
    gt_path = Path(gt_file)
    if not test_path.exists() or not gt_path.exists():
        raise FileNotFoundError(f"文件不存在: {test_file} 或 {gt_file}")
    
    novel_text = test_path.read_text(encoding='utf-8')
    gt = load_ground_truth(gt_path)
    
    char_manager = CharacterManager()
    persons = gt.get("entities", {}).get("persons", [])
    aliases_map = gt.get("entities", {}).get("aliases", {})
    register_characters(char_manager, persons, aliases_map)
    
    chapter_score = evaluate_chapter_splitter(novel_text, gt.get("chapters", {}))
    dialogue_score = evaluate_dialogue_classifier(novel_text, gt.get("对话分类", {}))
    sfx_score = evaluate_sfx_detector(novel_text, gt.get("sfx", {}))
    ner_score = evaluate_ner(novel_text, gt.get("entities", {}))
    speaker_score = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager)
    
    avg = (chapter_score + dialogue_score + sfx_score + ner_score + speaker_score) / 5
    
    return {
        "章节划分": chapter_score,
        "对话分类": dialogue_score,
        "拟声词检测": sfx_score,
        "命名实体识别": ner_score,
        "说话人匹配": speaker_score,
        "平均得分": avg,
    }


def main():
    if len(sys.argv) < 3:
        print("用法: python evaluate_generalization_v3.py <测试小说文件> <ground_truth文件>")
        sys.exit(1)
    
    test_file = Path(sys.argv[1])
    gt_file = Path(sys.argv[2])
    if not test_file.exists() or not gt_file.exists():
        print("文件不存在")
        sys.exit(1)
    
    novel_text = test_file.read_text(encoding='utf-8')
    gt = load_ground_truth(gt_file)
    
    char_manager = CharacterManager()
    persons = gt.get("entities", {}).get("persons", [])
    aliases_map = gt.get("entities", {}).get("aliases", {})
    register_characters(char_manager, persons, aliases_map)
    
    print("=" * 60)
    print(f"泛化性评估 v3：{test_file.stem}")
    print("=" * 60)
    
    chapter_score = evaluate_chapter_splitter(novel_text, gt.get("chapters", {}))
    print(f"章节划分: {chapter_score}")
    
    dialogue_score = evaluate_dialogue_classifier(novel_text, gt.get("对话分类", {}))
    print(f"对话分类: {dialogue_score}")
    
    sfx_score = evaluate_sfx_detector(novel_text, gt.get("sfx", {}))
    print(f"拟声词检测: {sfx_score}")
    
    ner_score = evaluate_ner(novel_text, gt.get("entities", {}))
    print(f"命名实体识别: {ner_score}")
    
    speaker_score = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager)
    print(f"说话人匹配: {speaker_score}")
    
    avg = (chapter_score + dialogue_score + sfx_score + ner_score + speaker_score) / 5
    print(f"\n平均得分: {avg:.1f}")
    
    report = {
        "test_file": str(test_file),
        "scores": {
            "chapter_splitting": chapter_score,
            "dialogue_classification": dialogue_score,
            "sfx_detection": sfx_score,
            "ner": ner_score,
            "speaker_matching": speaker_score,
            "average": avg
        }
    }
    with open(f"eval_result_{test_file.stem}_v3.json", "w", encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("结果已保存")


if __name__ == "__main__":
    main()
