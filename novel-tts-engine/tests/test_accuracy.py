import sys
import os
import time
import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import get_persons, get_locations, get_organizations


@dataclass
class DimensionScore:
    value: float
    score: float
    weight: float
    weighted_score: float


@dataclass
class ErrorInfo:
    count: int
    penalty: float
    details: List[str]


@dataclass
class ModuleReport:
    module: str
    total_score: float
    base_score: float
    penalty: float
    grade: str
    dimensions: Dict[str, Any]
    errors: Dict[str, Any]
    issues: List[str]
    suggestions: List[str]
    passed: bool


class ScoringEngine:
    WEIGHTS = {
        'recall': 0.25,
        'precision': 0.25,
        'f1': 0.15,
        'speed': 0.10,
        'format_accuracy': 0.15,
        'coverage': 0.10,
    }
    
    PENALTY = {
        'missed': -3,
        'false_positive': -2,
        'wrong_type': -2,
        'overlap': -5,
        'content_loss': -5,
        'content_duplicate': -10,
    }
    
    @staticmethod
    def score_recall(value: float) -> float:
        if value >= 0.95: return 1.0
        if value >= 0.90: return 0.9
        if value >= 0.85: return 0.8
        if value >= 0.80: return 0.7
        if value >= 0.75: return 0.6
        if value >= 0.70: return 0.5
        return 0.3
    
    @staticmethod
    def score_precision(value: float) -> float:
        if value >= 0.95: return 1.0
        if value >= 0.90: return 0.9
        if value >= 0.85: return 0.8
        if value >= 0.80: return 0.7
        if value >= 0.75: return 0.6
        if value >= 0.70: return 0.5
        return 0.3
    
    @staticmethod
    def score_f1(value: float) -> float:
        if value >= 0.90: return 1.0
        if value >= 0.85: return 0.9
        if value >= 0.80: return 0.8
        if value >= 0.75: return 0.7
        if value >= 0.70: return 0.6
        return 0.4
    
    @staticmethod
    def score_speed(chars_per_second: float) -> float:
        if chars_per_second >= 10000: return 1.0
        if chars_per_second >= 5000: return 0.9
        if chars_per_second >= 1000: return 0.8
        if chars_per_second >= 500: return 0.7
        if chars_per_second >= 100: return 0.6
        return 0.4
    
    @staticmethod
    def score_format_accuracy(value: float) -> float:
        if value >= 1.0: return 1.0
        if value >= 0.95: return 0.9
        if value >= 0.90: return 0.8
        if value >= 0.85: return 0.7
        return 0.5
    
    @staticmethod
    def score_coverage(value: float) -> float:
        if value >= 1.0: return 1.0
        if value >= 0.95: return 0.9
        if value >= 0.90: return 0.8
        if value >= 0.85: return 0.7
        return 0.5
    
    @staticmethod
    def get_grade(score: float) -> str:
        if score >= 90: return "A+ 优秀"
        if score >= 80: return "A 良好"
        if score >= 70: return "B 合格"
        if score >= 60: return "C 待改进"
        return "D 不合格"
    
    @staticmethod
    def is_passed(score: float, min_score: float = 70.0) -> bool:
        return score >= min_score
    
    def calculate_dimension(self, name: str, value: float) -> DimensionScore:
        score_methods = {
            'recall': self.score_recall,
            'precision': self.score_precision,
            'f1': self.score_f1,
            'speed': self.score_speed,
            'format_accuracy': self.score_format_accuracy,
            'coverage': self.score_coverage,
        }
        
        score = score_methods[name](value)
        weight = self.WEIGHTS[name]
        
        return DimensionScore(
            value=value,
            score=score,
            weight=weight,
            weighted_score=score * weight
        )
    
    def calculate_base_score(self, dimensions: Dict[str, DimensionScore]) -> float:
        return sum(d.weighted_score for d in dimensions.values()) * 100
    
    def calculate_penalty(self, missed: int, false_positive: int) -> float:
        penalty = 0
        penalty += missed * self.PENALTY['missed']
        penalty += false_positive * self.PENALTY['false_positive']
        return max(penalty, -30)


def load_test_novel():
    novel_path = os.path.join(os.path.dirname(__file__), 'test_novel.txt')
    with open(novel_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_chapter_splitting():
    print("\n" + "=" * 70)
    print("一、章节划分模块测试")
    print("=" * 70)
    
    text = load_test_novel()
    engine = ScoringEngine()
    
    start_time = time.time()
    structure = split_with_volumes(text)
    elapsed = time.time() - start_time
    
    expected_volumes = 2
    expected_chapters = 5
    
    recall = 1.0 if structure.total_chapters == expected_chapters else structure.total_chapters / expected_chapters
    precision = 1.0 if structure.total_chapters == expected_chapters else expected_chapters / max(structure.total_chapters, 1)
    f1 = 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0
    speed = len(text) / elapsed if elapsed > 0.0001 else 1000000
    format_accuracy = 1.0
    
    total_content_len = sum(len(ch.content) for vol in structure.volumes for ch in vol.chapters)
    
    volume_title_len = sum(len(vol.title) + 2 for vol in structure.volumes)
    chapter_title_len = sum(len(ch.title) + 2 for vol in structure.volumes for ch in vol.chapters)
    structure_len = volume_title_len + chapter_title_len
    effective_text_len = len(text) - structure_len
    coverage = total_content_len / effective_text_len if effective_text_len > 0 else 1.0
    
    positions = []
    for vol in structure.volumes:
        for ch in vol.chapters:
            positions.append((ch.start_pos, ch.end_pos, ch.title))
    positions.sort()
    overlaps = []
    for i in range(len(positions) - 1):
        if positions[i][1] > positions[i+1][0]:
            overlaps.append((positions[i], positions[i+1]))
    
    dimensions = {
        'recall': engine.calculate_dimension('recall', recall),
        'precision': engine.calculate_dimension('precision', precision),
        'f1': engine.calculate_dimension('f1', f1),
        'speed': engine.calculate_dimension('speed', speed),
        'format_accuracy': engine.calculate_dimension('format_accuracy', format_accuracy),
        'coverage': engine.calculate_dimension('coverage', coverage),
    }
    
    base_score = engine.calculate_base_score(dimensions)
    
    penalty = 0
    errors = {}
    issues = []
    
    if overlaps:
        overlap_penalty = len(overlaps) * engine.PENALTY['overlap']
        penalty += overlap_penalty
        errors['overlap'] = {'count': len(overlaps), 'penalty': overlap_penalty, 'details': [f"{o[0][2]}与{o[1][2]}" for o in overlaps]}
        issues.append(f"位置重叠: {len(overlaps)}处")
    
    if coverage < 1.0:
        loss_penalty = int((1 - coverage) * 100) * engine.PENALTY['content_loss']
        penalty += loss_penalty
        errors['content_loss'] = {'count': int((1 - coverage) * 100), 'penalty': loss_penalty, 'details': [f"丢失{(1-coverage)*100:.1f}%内容"]}
        issues.append(f"内容丢失: {(1-coverage)*100:.1f}%")
    
    total_score = max(base_score + penalty, 0)
    grade = engine.get_grade(total_score)
    passed = engine.is_passed(total_score) and len(overlaps) == 0
    
    print(f"\n识别结果:")
    print(f"  总卷数: {structure.total_volumes} (期望: {expected_volumes})")
    print(f"  总章节数: {structure.total_chapters} (期望: {expected_chapters})")
    print(f"  处理速度: {speed:.0f} 字符/秒")
    print(f"  内容覆盖率: {coverage*100:.1f}%")
    print(f"  位置重叠: {len(overlaps)}处")
    
    print(f"\n评分详情:")
    print(f"  基础分: {base_score:.1f}")
    print(f"  错误惩罚: {penalty}")
    print(f"  总分: {total_score:.1f} 分")
    print(f"  等级: {grade}")
    print(f"  状态: {'✓ 通过' if passed else '✗ 未通过'}")
    
    if issues:
        print(f"\n问题:")
        for issue in issues:
            print(f"  ⚠ {issue}")
    
    return ModuleReport(
        module="章节划分",
        total_score=total_score,
        base_score=base_score,
        penalty=penalty,
        grade=grade,
        dimensions={k: asdict(v) for k, v in dimensions.items()},
        errors=errors,
        issues=issues,
        suggestions=[],
        passed=passed
    )


def test_dialogue_classification():
    print("\n" + "=" * 70)
    print("二、对话/旁白分类模块测试")
    print("=" * 70)
    
    test_cases = [
        ("「少爷，您终于醒了！」", "dialogue"),
        ("林轩缓缓睁开双眼，眼中闪过一丝迷茫。", "narration"),
        ("他心想，这里是什么地方？", "narration"),
        ("\"小翠，我睡了多久？\"", "dialogue"),
        ("林轩转头看去，只见一个十四五岁的小丫鬟正站在床边。", "narration"),
        ("\"少爷，您昏迷了整整三天！\"", "dialogue"),
        ("咚咚咚，门外又传来敲门声。", "narration"),
        ("\"进来吧。\"", "dialogue"),
        ("林轩合上书籍，眼中闪过一丝坚定。", "narration"),
        ("\"既来之，则安之。\"", "dialogue"),
        ("哗啦！哗啦！院子里的水声不断响起。", "narration"),
        ("\"少爷，您休息一下吧。\"", "dialogue"),
        ("轰隆！天空中突然传来一声雷鸣。", "narration"),
        ("\"要下雨了。\"", "dialogue"),
        ("林轩走在街上，看着两旁的店铺，心中感慨万千。", "narration"),
        ("\"让开！让开！\"", "dialogue"),
        ("\"怎么？不敢说话？\"", "dialogue"),
        ("林轩面色平静，没有理会赵虎的挑衅。", "narration"),
        ("砰！一声闷响，测试石上显示出一个数字。", "narration"),
        ("\"恭喜你，林轩，你被录取了！\"", "dialogue"),
    ]
    
    classifier = DialogueClassifier()
    engine = ScoringEngine()
    
    total_chars = sum(len(t[0]) for t in test_cases)
    start_time = time.time()
    
    tp = 0
    fp = 0
    fn = 0
    correct = 0
    
    for text, expected in test_cases:
        result = classifier.classify(text)
        if result.sentence_type == expected:
            correct += 1
            tp += 1
        else:
            if result.sentence_type == "dialogue":
                fp += 1
            else:
                fn += 1
    
    elapsed = time.time() - start_time
    
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    speed = total_chars / elapsed if elapsed > 0.0001 else 1000000
    format_accuracy = 1.0
    coverage = 1.0
    
    dimensions = {
        'recall': engine.calculate_dimension('recall', recall),
        'precision': engine.calculate_dimension('precision', precision),
        'f1': engine.calculate_dimension('f1', f1),
        'speed': engine.calculate_dimension('speed', speed),
        'format_accuracy': engine.calculate_dimension('format_accuracy', format_accuracy),
        'coverage': engine.calculate_dimension('coverage', coverage),
    }
    
    base_score = engine.calculate_base_score(dimensions)
    penalty = engine.calculate_penalty(fn, fp)
    total_score = max(base_score + penalty, 0)
    grade = engine.get_grade(total_score)
    passed = engine.is_passed(total_score)
    
    errors = {
        'missed': {'count': fn, 'penalty': fn * engine.PENALTY['missed'], 'details': []},
        'false_positive': {'count': fp, 'penalty': fp * engine.PENALTY['false_positive'], 'details': []},
    }
    
    print(f"\n识别结果:")
    print(f"  正确分类: {correct}/{len(test_cases)}")
    print(f"  漏识别: {fn}, 误识别: {fp}")
    print(f"  处理速度: {speed:.0f} 字符/秒")
    
    print(f"\n评分详情:")
    print(f"  基础分: {base_score:.1f}")
    print(f"  错误惩罚: {penalty} (漏识别: {fn}×(-3), 误识别: {fp}×(-2))")
    print(f"  总分: {total_score:.1f} 分")
    print(f"  等级: {grade}")
    print(f"  状态: {'✓ 通过' if passed else '✗ 未通过'}")
    
    return ModuleReport(
        module="对话/旁白分类",
        total_score=total_score,
        base_score=base_score,
        penalty=penalty,
        grade=grade,
        dimensions={k: asdict(v) for k, v in dimensions.items()},
        errors=errors,
        issues=[],
        suggestions=[],
        passed=passed
    )


def test_sfx_detection():
    print("\n" + "=" * 70)
    print("三、拟声词检测模块测试")
    print("=" * 70)
    
    test_cases = [
        ("咚咚咚，门外又传来敲门声。", ["咚咚咚"]),
        ("哗啦！哗啦！院子里的水声不断响起。", ["哗啦"]),
        ("轰隆！天空中突然传来一声雷鸣。", ["轰隆"]),
        ("哗啦啦的雨声在窗外响起。", ["哗啦啦"]),
        ("砰！一声闷响，测试石上显示出一个数字。", ["砰"]),
        ("呼呼！拳风呼啸，林轩一遍遍地练习着基础拳法。", ["呼呼"]),
        ("叮叮当当！演武场上，兵器碰撞的声音不断响起。", ["叮叮当当"]),
        ("喵！一只小猫从墙头跳下。", ["喵"]),
    ]
    
    detector = SfxDetector()
    engine = ScoringEngine()
    
    total_chars = sum(len(t[0]) for t in test_cases)
    start_time = time.time()
    
    total_expected = 0
    total_found = 0
    correct = 0
    missed_details = []
    false_positive_details = []
    
    for text, expected_sfx in test_cases:
        results = detector.detect(text)
        found_sfx = [r.text for r in results]
        
        total_expected += len(expected_sfx)
        total_found += len(found_sfx)
        
        for sfx in expected_sfx:
            if sfx in found_sfx:
                correct += 1
            else:
                missed_details.append(sfx)
        
        for sfx in found_sfx:
            if sfx not in expected_sfx:
                false_positive_details.append(sfx)
    
    elapsed = time.time() - start_time
    
    missed = len(missed_details)
    false_positive = len(false_positive_details)
    
    recall = correct / total_expected if total_expected > 0 else 0
    precision = correct / total_found if total_found > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    speed = total_chars / elapsed if elapsed > 0.0001 else 1000000
    format_accuracy = 1.0
    coverage = 1.0
    
    dimensions = {
        'recall': engine.calculate_dimension('recall', recall),
        'precision': engine.calculate_dimension('precision', precision),
        'f1': engine.calculate_dimension('f1', f1),
        'speed': engine.calculate_dimension('speed', speed),
        'format_accuracy': engine.calculate_dimension('format_accuracy', format_accuracy),
        'coverage': engine.calculate_dimension('coverage', coverage),
    }
    
    base_score = engine.calculate_base_score(dimensions)
    penalty = engine.calculate_penalty(missed, false_positive)
    total_score = max(base_score + penalty, 0)
    grade = engine.get_grade(total_score)
    passed = engine.is_passed(total_score)
    
    errors = {
        'missed': {'count': missed, 'penalty': missed * engine.PENALTY['missed'], 'details': missed_details},
        'false_positive': {'count': false_positive, 'penalty': false_positive * engine.PENALTY['false_positive'], 'details': false_positive_details},
    }
    
    issues = []
    if missed_details:
        issues.append(f"漏识别: {missed_details}")
    if false_positive_details:
        issues.append(f"误识别: {false_positive_details}")
    
    print(f"\n识别结果:")
    print(f"  正确识别: {correct}/{total_expected}")
    print(f"  漏识别: {missed} {missed_details}")
    print(f"  误识别: {false_positive} {false_positive_details}")
    print(f"  处理速度: {speed:.0f} 字符/秒")
    
    print(f"\n评分详情:")
    print(f"  基础分: {base_score:.1f}")
    print(f"  错误惩罚: {penalty} (漏识别: {missed}×(-3), 误识别: {false_positive}×(-2))")
    print(f"  总分: {total_score:.1f} 分")
    print(f"  等级: {grade}")
    print(f"  状态: {'✓ 通过' if passed else '✗ 未通过'}")
    
    return ModuleReport(
        module="拟声词检测",
        total_score=total_score,
        base_score=base_score,
        penalty=penalty,
        grade=grade,
        dimensions={k: asdict(v) for k, v in dimensions.items()},
        errors=errors,
        issues=issues,
        suggestions=["优化正则表达式，减少误报"] if false_positive > 0 else [],
        passed=passed
    )


def test_ner():
    print("\n" + "=" * 70)
    print("四、命名实体识别模块测试")
    print("=" * 70)
    
    test_cases = [
        ("林轩缓缓睁开双眼。", ["林轩"], "PER"),
        ("小翠是林府的贴身丫鬟。", ["小翠", "林府"], "PER/LOC"),
        ("林天豪走到床边。", ["林天豪"], "PER"),
        ("王管家是林府的老人了。", ["王管家", "林府"], "PER/LOC"),
        ("赵虎是赵家的少爷。", ["赵虎", "赵家"], "PER/ORG"),
        ("天元城是方圆百里内最大的城市。", ["天元城"], "LOC"),
        ("林轩来到天元武馆。", ["林轩", "天元武馆"], "PER/ORG"),
        ("李铁是林轩的朋友。", ["李铁", "林轩"], "PER"),
        ("陈风是淬体境九重的高手。", ["陈风"], "PER"),
    ]
    
    engine = ScoringEngine()
    
    total_chars = sum(len(t[0]) for t in test_cases)
    start_time = time.time()
    
    total_expected = 0
    correct = 0
    missed_details = []
    false_positive_details = []
    
    for text, expected_entities, entity_types in test_cases:
        persons = get_persons(text)
        locations = get_locations(text)
        organizations = get_organizations(text)
        all_found = persons + locations + organizations
        
        total_expected += len(expected_entities)
        
        for entity in expected_entities:
            if entity in all_found:
                correct += 1
            else:
                missed_details.append(entity)
        
        for entity in all_found:
            if entity not in expected_entities:
                false_positive_details.append(entity)
    
    elapsed = time.time() - start_time
    
    missed = len(missed_details)
    false_positive = len(false_positive_details)
    total_found = correct + false_positive
    
    recall = correct / total_expected if total_expected > 0 else 0
    precision = correct / total_found if total_found > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    speed = total_chars / elapsed if elapsed > 0.0001 else 1000000
    format_accuracy = 1.0
    coverage = 1.0
    
    dimensions = {
        'recall': engine.calculate_dimension('recall', recall),
        'precision': engine.calculate_dimension('precision', precision),
        'f1': engine.calculate_dimension('f1', f1),
        'speed': engine.calculate_dimension('speed', speed),
        'format_accuracy': engine.calculate_dimension('format_accuracy', format_accuracy),
        'coverage': engine.calculate_dimension('coverage', coverage),
    }
    
    base_score = engine.calculate_base_score(dimensions)
    penalty = engine.calculate_penalty(missed, false_positive)
    total_score = max(base_score + penalty, 0)
    grade = engine.get_grade(total_score)
    passed = engine.is_passed(total_score, min_score=60)
    
    errors = {
        'missed': {'count': missed, 'penalty': missed * engine.PENALTY['missed'], 'details': missed_details},
        'false_positive': {'count': false_positive, 'penalty': false_positive * engine.PENALTY['false_positive'], 'details': false_positive_details},
    }
    
    issues = []
    if missed_details:
        issues.append(f"漏识别: {missed_details}")
    if false_positive_details:
        issues.append(f"误识别: {false_positive_details}")
    
    print(f"\n识别结果:")
    print(f"  正确识别: {correct}/{total_expected}")
    print(f"  漏识别: {missed} {missed_details}")
    print(f"  误识别: {false_positive} {false_positive_details}")
    print(f"  处理速度: {speed:.0f} 字符/秒")
    
    print(f"\n评分详情:")
    print(f"  基础分: {base_score:.1f}")
    print(f"  错误惩罚: {penalty} (漏识别: {missed}×(-3), 误识别: {false_positive}×(-2))")
    print(f"  总分: {total_score:.1f} 分")
    print(f"  等级: {grade}")
    print(f"  状态: {'✓ 通过' if passed else '✗ 未通过'}")
    
    return ModuleReport(
        module="命名实体识别",
        total_score=total_score,
        base_score=base_score,
        penalty=penalty,
        grade=grade,
        dimensions={k: asdict(v) for k, v in dimensions.items()},
        errors=errors,
        issues=issues,
        suggestions=["优化NER规则，减少漏识别和误识别"] if missed > 0 or false_positive > 0 else [],
        passed=passed
    )


def run_all_tests():
    print("\n" + "=" * 70)
    print("网文风格测试文本分析功能评分报告 v2.0")
    print("=" * 70)
    print("\n评分公式: 总分 = 基础分 - 错误惩罚")
    print("错误惩罚: 漏识别(-3分/个), 误识别(-2分/个)")
    
    reports = [
        test_chapter_splitting(),
        test_dialogue_classification(),
        test_sfx_detection(),
        test_ner(),
    ]
    
    print("\n" + "=" * 70)
    print("综合评分汇总")
    print("=" * 70)
    
    print(f"\n{'模块':<15} {'基础分':>8} {'惩罚':>8} {'总分':>8} {'等级':<12} {'状态':<8}")
    print("-" * 65)
    
    total_score = 0
    all_passed = True
    
    for report in reports:
        status = "✓ 通过" if report.passed else "✗ 未通过"
        print(f"{report.module:<15} {report.base_score:>8.1f} {report.penalty:>8.1f} {report.total_score:>8.1f} {report.grade:<12} {status:<8}")
        total_score += report.total_score
        if not report.passed:
            all_passed = False
    
    avg_score = total_score / len(reports)
    print("-" * 65)
    print(f"{'平均分':<15} {'':<8} {'':<8} {avg_score:>8.1f}")
    
    print("\n" + "=" * 70)
    print("错误详情")
    print("=" * 70)
    
    for report in reports:
        if report.errors:
            print(f"\n【{report.module}】")
            for error_type, error_info in report.errors.items():
                if error_info['count'] > 0:
                    print(f"  {error_type}: {error_info['count']}个 (惩罚: {error_info['penalty']}分)")
                    if error_info['details']:
                        print(f"    详情: {error_info['details'][:5]}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 所有模块测试通过！")
    else:
        print("⚠️ 部分模块未达标，请根据错误详情优化")
    print("=" * 70)
    
    return reports


if __name__ == "__main__":
    run_all_tests()
