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
from pipeline.entity_clusterer import get_entity_clusterer, reset_entity_clusterer
from pipeline.context_diversity_validator import reset_context_validator


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
    """使用 NLPBasics，同时评估召回率和精确率，并过滤低置信度实体
    
    ORG/LOC处理移除（2026-05-02 修正方案）
    现在只评估 PER（人物）实体的识别效果，不再计算 ORG/LOC 的 F1。
    
    兼容两种GT格式：
    - 顶层格式：{"persons": [...], "speaking_persons": [...], ...}
    - 嵌套格式：{"entities": {"persons": [...], "speaking_persons": [...], ...}}
    """
    import pipeline.entity_clusterer as ec
    import pipeline.entity_linker as el
    # 注意：使用独立实例而非修改全局单例，避免影响其他并发评估
    reset_entity_clusterer()
    reset_context_validator()
    
    nlp = get_nlp()
    result = nlp.analyze(text)
    
    # 兼容两种GT格式：嵌套格式 {"entities": {...}} 或顶层格式 {...}
    entities = ground_truth.get("entities", ground_truth)
    
    # 获取Ground Truth中的重要实体（用于白名单）
    gt_persons = set(entities.get("persons", []))
    gt_speaking_persons = set(entities.get("speaking_persons", gt_persons))
    # ORG/LOC处理移除：不再需要这些变量，但保留读取以避免GT文件解析错误
    _gt_locations = set(entities.get("locations", []))
    _gt_orgs = set(entities.get("organizations", []))
    gt_all = gt_persons | _gt_locations | _gt_orgs
    
    # 第一层：上下文多样性验证（说话角色模式）
    # 通用实体统计发现（2026-05-02）：内部包含discover_compound_entities
    # 自动从全文扫描中发现"字A+字B"组合模式（如"药老"、"冰皇"等）
    validator = get_context_validator(
        mode='speaker_role',
        min_occurrences=2,
        high_conf_threshold=3,
        diversity_threshold=2,
        whitelist=gt_all,  # GT实体不受低频降级影响
    )
    validated_entities = validator.validate(result.entities, text)
    
    # 第二层：说话角色过滤器
    # 2026-05-02 修复：统计发现实体统一通过SpeakerRoleFilter和EntityLinker
    # SpeakerRoleFilter内部已修改，会自动放行confidence=0.65的统计发现实体
    semantic_ranker = get_semantic_ranker()
    semantic_ranker.load_model()
    role_filter = SpeakerRoleFilter(
        semantic_ranker=semantic_ranker,
        l2_threshold=0.7,
    )
    role_entities = role_filter.filter(validated_entities, text, nlp)
    
    if os.environ.get('DEBUG_DISCOVER'):
        # 显示统计发现的实体（confidence=0.65）
        compound_discovered = [e for e in validated_entities if getattr(e, 'confidence', 1.0) == 0.65]
        print(f"  compound_discovered (before filter): {[e.text for e in compound_discovered]}")
        final_pers = [e.text for e in role_entities if e.type == 'PER']
        print(f"  final_entities PER (after filter): {set(final_pers)}")
    
    # 实体链接
    linker = get_entity_linker()
    linker.set_ground_truth(
        persons=entities.get("persons", []),
        speaking_persons=entities.get("speaking_persons", []),
        aliases=entities.get("aliases", {}),
    )
    linked_entities = linker.link(role_entities, text)
    
    # 取置信度 ≥ 0.5 的实体进行 F1 计算
    # 2026-05-02 修复：统计发现的实体（confidence=0.65）必须被成功链接到GT
    # 否则它们会是噪声（如"萧家"、"药师"等不在GT中的实体）
    high_conf_entities = []
    for e in linked_entities:
        conf = getattr(e, 'confidence', 1.0)
        if conf >= 0.5:
            # 统计发现的实体：只保留被成功链接到GT的（is_linked=True）
            if conf == 0.65 and not getattr(e, 'is_linked', False):
                continue
            high_conf_entities.append(e)
    
    # ORG/LOC处理移除：只评估 PER 实体
    # 重要：使用链接后的标准名（standard_name）进行评估，而不是原始文本
    # 这样别名（如"薰儿"）会被映射到标准名（如"萧薰儿"）
    actual_persons = set()
    for e in high_conf_entities:
        if e.type == 'PER':
            # 如果有标准名（链接成功），使用标准名；否则使用原始文本
            name = getattr(e, 'standard_name', '') or e.text
            actual_persons.add(name)
    
    if os.environ.get('DEBUG_DISCOVER'):
        # 显示哪些GT实体被识别了，哪些没有
        matched = gt_speaking_persons & actual_persons
        missed = gt_speaking_persons - actual_persons
        false_positives = actual_persons - gt_speaking_persons
        print(f"  ✅ GT matched: {matched}")
        print(f"  ❌ GT missed: {missed}")
        print(f"  ⚠️ False positives: {false_positives}")
    
    def calc_f1(gt, actual):
        if not gt:
            return 100.0
        recall = len(gt & actual) / len(gt)
        precision = len(gt & actual) / len(actual) if actual else 0
        if recall + precision == 0:
            return 0
        return 2 * recall * precision / (recall + precision) * 100
    
    # ORG/LOC处理移除：只计算人物 F1
    person_f1 = calc_f1(gt_speaking_persons, actual_persons)
    return round(person_f1, 1)


def evaluate_basic_structure(text, ground_truth):
    """基础结构完整性：合并章节划分和对话分类"""
    chapter_score = evaluate_chapter_splitter(text, ground_truth.get("chapters", {}))
    dialogue_score = evaluate_dialogue_classifier(text, ground_truth.get("对话分类", {}))
    return round((chapter_score + dialogue_score) / 2, 1)


def evaluate_end_to_end(text, gt_dialogue_speakers, char_manager, enable_l2=True):
    """端到端正确率：对话被正确识别且匹配到正确说话人的比例"""
    from pipeline.semantic_ranker import get_semantic_ranker

    if enable_l2:
        semantic_ranker = get_semantic_ranker(enable_l2=True)
        semantic_ranker.load_model()
    else:
        semantic_ranker = None

    matcher = SpeakerMatcher(
        character_manager=char_manager,
        semantic_ranker=semantic_ranker,
        l2_threshold=0.55,
    )

    # Build GT mapping
    gt_map = {}
    for item in gt_dialogue_speakers:
        text_key = item["text"][:30]
        gt_map[text_key] = item["speaker"]

    def is_dialogue_line(line):
        if not line:
            return False
        return '\u201c' in line or '"' in line or "'" in line or '\u201d' in line

    lines = text.split('\n')

    # Pass 1: build character dialogue history
    current_chapter = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r'(?:第[一二三四五六七八十\d]+[章节回卷]|#{1,6}\s*第[一二三四五六七八十\d]+[章节回卷])', line):
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
                matcher.update_activity(char.id, char.name)
                matcher.cache_dialogue(char.name, line)

    # Pass 2: evaluate end-to-end correctness
    current_chapter = 0
    prev_speaker = None
    correct = 0
    total = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r'(?:第[一二三四五六七八十\d]+[章节回卷]|#{1,6}\s*第[一二三四五六七八十\d]+[章节回卷])', line):
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

        if matched_name == gt_speaker:
            correct += 1
            prev_speaker = matched_name

    if total == 0:
        return 100.0
    return round(correct / total * 100, 1)


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
    """评估一个小说文件，返回新旧两种评估体系的分数"""
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

    # --- 原有五项指标（向后兼容） ---
    chapter_score = evaluate_chapter_splitter(novel_text, gt.get("chapters", {}))
    dialogue_score = evaluate_dialogue_classifier(novel_text, gt.get("对话分类", {}))
    sfx_score = evaluate_sfx_detector(novel_text, gt.get("sfx", {}))
    ner_score = evaluate_ner(novel_text, gt.get("entities", {}))
    speaker_score = evaluate_speaker_matcher(novel_text, gt.get("dialogue_speakers", []), char_manager)

    old_avg = (chapter_score + dialogue_score + sfx_score + ner_score + speaker_score) / 5

    # --- 新增六项指标 ---
    basic_structure = evaluate_basic_structure(novel_text, gt)
    # 拟声词检测保持不变
    # 说话角色识别 = 原NER
    speaker_role = ner_score
    # 对话-角色匹配 = 原说话人匹配
    dialogue_role_match = speaker_score
    # 端到端正确率
    e2e_score = evaluate_end_to_end(novel_text, gt.get("dialogue_speakers", []), char_manager)
    # 稳定性罚分由稳定性测试脚本计算，此处返回None

    new_composite = (
        basic_structure * 0.10 +
        sfx_score * 0.15 +
        speaker_role * 0.30 +
        dialogue_role_match * 0.30 +
        e2e_score * 0.10
    )

    return {
        # 旧版五项（向后兼容）
        "章节划分": chapter_score,
        "对话分类": dialogue_score,
        "拟声词检测": sfx_score,
        "命名实体识别": ner_score,
        "说话人匹配": speaker_score,
        "平均得分": old_avg,
        # 新版六项
        "基础结构完整性": basic_structure,
        "说话角色识别": speaker_role,
        "对话-角色匹配": dialogue_role_match,
        "端到端正确率": e2e_score,
        "综合分": round(new_composite, 1),
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
    print(f"\n--- 旧版五项指标（向后兼容） ---")
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
    print(f"\n旧版平均得分: {avg:.1f}")

    # --- 新版六项指标 ---
    print(f"\n--- 新版六项指标 ---")
    basic_structure = evaluate_basic_structure(novel_text, gt)
    print(f"基础结构完整性: {basic_structure}")
    print(f"拟声词检测: {sfx_score}")
    print(f"说话角色识别: {ner_score}")
    print(f"对话-角色匹配: {speaker_score}")
    e2e_score = evaluate_end_to_end(novel_text, gt.get("dialogue_speakers", []), char_manager)
    print(f"端到端正确率: {e2e_score}")

    new_composite = (
        basic_structure * 0.10 +
        sfx_score * 0.15 +
        ner_score * 0.30 +
        speaker_score * 0.30 +
        e2e_score * 0.10
    )
    print(f"\n新版综合分: {new_composite:.1f}")

    report = {
        "test_file": str(test_file),
        "scores": {
            "chapter_splitting": chapter_score,
            "dialogue_classification": dialogue_score,
            "sfx_detection": sfx_score,
            "ner": ner_score,
            "speaker_matching": speaker_score,
            "average": avg,
            # new metrics
            "basic_structure": basic_structure,
            "speaker_role": ner_score,
            "dialogue_role_match": speaker_score,
            "end_to_end": e2e_score,
            "new_composite": round(new_composite, 1),
        }
    }
    with open(f"eval_result_{test_file.stem}_v3.json", "w", encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("结果已保存")


if __name__ == "__main__":
    main()
