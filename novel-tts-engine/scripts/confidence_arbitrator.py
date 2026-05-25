#!/usr/bin/env python
"""置信度仲裁器基准测试 - 快速验证当前参数配置的准确率。

用法:
    python scripts/confidence_arbitrator.py --quick          # 基准测试（当前参数）
    python scripts/confidence_arbitrator.py --grid           # 网格搜索
    python scripts/confidence_arbitrator.py --optimize       # 贝叶斯优化
"""
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


def load_gt_data(gt_path: Path) -> Tuple[List[Dict], List[Dict]]:
    """加载 Ground Truth 测试数据。

    Returns:
        (dialogues, characters) 元组
    """
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    dialogues = gt.get('dialogues', [])
    characters = gt.get('characters', [])
    return dialogues, characters


def register_characters(char_manager: CharacterManager, characters: List[Dict], project_id: int = 1):
    """将 GT 中的角色注册到 CharacterManager。"""
    for char in characters:
        name = char.get('name', '')
        aliases = char.get('aliases', [])
        if name:
            char_obj = char_manager.add_character(name, project_id)
            if char_obj and aliases:
                for alias in aliases:
                    char_manager.add_alias(char_obj.id, alias)


def run_single_config(
    test_data: List[Dict],
    matcher: SpeakerMatcher,
    config_overrides: Optional[Dict] = None,
) -> Dict:
    """用一组参数跑测试。

    Args:
        test_data: GT 数据（dialogues 列表）
        matcher: SpeakerMatcher 实例
        config_overrides: 覆盖默认配置的参数字典

    Returns:
        测试结果字典 {accuracy, correct, total, errors}
    """
    # 应用参数覆盖
    if config_overrides:
        for key, value in config_overrides.items():
            _apply_config(matcher, key, value)

    correct = 0
    errors = []

    for item in test_data:
        text = item.get('text', '')
        speaker_gt = item.get('speaker', '')
        note = item.get('note', '')

        # note 字段包含旁白信息（如"疲惫的李经理抬头"）
        # 将旁白和对话组合成完整句子，模拟小说中的格式
        # 格式：旁白 + 对话
        context_text = note

        result = matcher.match_speaker(DialogueContext(
            text=f"{context_text}：「{text}」" if context_text else text,
        ))

        if result and result.character:
            predicted = result.character.name
        else:
            predicted = None

        if predicted == speaker_gt:
            correct += 1
        else:
            errors.append({
                'line': item.get('line', '?'),
                'text': text[:50],
                'speaker_gt': speaker_gt,
                'predicted': predicted,
                'note': note[:50],
            })

    total = len(test_data)
    return {
        'accuracy': correct / total if total > 0 else 0,
        'correct': correct,
        'total': total,
        'errors': errors,
    }


def _apply_config(matcher: SpeakerMatcher, key: str, value: float):
    """将参数应用到 SpeakerMatcher 实例。"""
    # 近因衰减
    decay_map = {
        'RECENCY_DECAY_RECENT': 'recency_decay_recent',
        'RECENCY_DECAY_SECOND': 'recency_decay_second',
        'RECENCY_DECAY_OTHER': 'recency_decay_other',
        'ACTIVITY_DECAY_FACTOR': 'activity_decay_factor',
        'ACTIVITY_INCREMENT': 'activity_increment',
        'CHARACTER_ELIGIBLE_MIN_FREQ': 'character_eligible_min_freq',
    }
    attr = decay_map.get(key)
    if attr and hasattr(matcher, attr):
        setattr(matcher, attr, value)


def run_benchmark(gt_files: List[Path]) -> Dict:
    """运行基准测试。"""
    results = {}
    for gt_file in gt_files:
        if not gt_file.exists():
            print(f"[跳过] {gt_file.name} 不存在")
            continue

        test_data, characters = load_gt_data(gt_file)
        if not test_data:
            print(f"[跳过] {gt_file.name} 无数据")
            continue

        char_manager = CharacterManager()
        register_characters(char_manager, characters)
        matcher = SpeakerMatcher(char_manager)
        matcher.current_project_id = '1'

        print(f"\n{'='*60}")
        print(f"测试集: {gt_file.name}")
        print(f"角色数: {len(characters)}")
        print(f"对话数: {len(test_data)}")

        result = run_single_config(test_data, matcher)

        print(f"准确率: {result['accuracy']:.2%} ({result['correct']}/{result['total']})")
        if result['errors']:
            print(f"\n错误样例 Top 5:")
            for err in result['errors'][:5]:
                print(f"  L{err['line']}: GT={err['speaker_gt']}, 预测={err['predicted']}")
                print(f"    文本: {err['text']}")

        results[gt_file.name] = result

    return results


def run_grid_search(gt_file: Path) -> List[Dict]:
    """网格搜索：遍历近因衰减参数组合。"""
    test_data, characters = load_gt_data(gt_file)

    if not test_data:
        return []

    print(f"\n网格搜索: {gt_file.name}")
    print(f"角色数: {len(characters)}")
    print(f"对话数: {len(test_data)}")
    print(f"参数空间: RECENCY_DECAY_RECENT=[0.10,0.15,0.20,0.25,0.30], "
          f"RECENCY_DECAY_SECOND=[0.05,0.10,0.15,0.20], "
          f"RECENCY_DECAY_OTHER=[0.02,0.05,0.08,0.10]")

    results = []
    recent_values = [0.10, 0.15, 0.20, 0.25, 0.30]
    second_values = [0.05, 0.10, 0.15, 0.20]
    other_values = [0.02, 0.05, 0.08, 0.10]

    for r in recent_values:
        for s in second_values:
            for o in other_values:
                config = {
                    'RECENCY_DECAY_RECENT': r,
                    'RECENCY_DECAY_SECOND': s,
                    'RECENCY_DECAY_OTHER': o,
                }
                char_manager = CharacterManager()
                register_characters(char_manager, characters)
                matcher = SpeakerMatcher(char_manager)
                matcher.current_project_id = '1'
                result = run_single_config(test_data, matcher, config)
                result['config'] = config
                results.append(result)

    # 排序
    results.sort(key=lambda x: x['accuracy'], reverse=True)

    print(f"\nTop 10 参数组合:")
    for i, r in enumerate(results[:10]):
        c = r['config']
        print(f"  #{i+1}: acc={r['accuracy']:.2%} "
              f"RECENT={c['RECENCY_DECAY_RECENT']}, "
              f"SECOND={c['RECENCY_DECAY_SECOND']}, "
              f"OTHER={c['RECENCY_DECAY_OTHER']}")

    return results


def main():
    gt_dir = Path(__file__).parent.parent / 'tests' / 'data' / 'ground_truth'

    # 仅使用有对话+旁白格式的 GT（gt_urban_long 有 91 条对话+note）
    gt_files = [
        gt_dir / 'gt_urban_long.json',
    ]

    if '--grid' in sys.argv:
        # 网格搜索（只用都市长文本）
        run_grid_search(gt_dir / 'gt_urban_long.json')
    else:
        # 基准测试
        results = run_benchmark(gt_files)

        # 汇总
        print(f"\n{'='*60}")
        print("汇总:")
        for name, r in results.items():
            print(f"  {name}: {r['accuracy']:.2%} ({r['correct']}/{r['total']})")


if __name__ == '__main__':
    main()
