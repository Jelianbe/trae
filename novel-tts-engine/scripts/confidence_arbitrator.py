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
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import sm_config
from utils.config import DB_PATH


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


def clean_project(db_path: Path, project_id: str):
    """清理指定 project_id 的所有数据，防止历史污染。"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('DELETE FROM characters WHERE project_id = ?', (project_id,))
    try:
        cursor.execute('DELETE FROM dialogues WHERE project_id = ?', (project_id,))
    except sqlite3.OperationalError:
        pass  # dialogues 表可能不存在
    conn.commit()
    conn.close()


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
        context_before = item.get('context_before', '')
        context_after = item.get('context_after', '')
        note = item.get('note', '')

        # gt_urban_long 格式：有 note 字段，无 context_before/context_after
        # gt_speaker_312 格式：有 context_before/context_after，text 包含引号
        if context_before or context_after:
            # gt_speaker_312 格式：直接使用
            ctx = DialogueContext(
                text=text,
                context_before=context_before,
                context_after=context_after,
            )
        elif note:
            # gt_urban_long 格式：note 是旁白，组合成完整句子
            ctx = DialogueContext(
                text=f"{note}：「{text}」",
            )
        else:
            # 纯对话格式
            ctx = DialogueContext(text=text)

        result = matcher.match_speaker(ctx)

        if result and result.character:
            predicted = result.character.name
        else:
            predicted = None

        if predicted == speaker_gt:
            correct += 1
        else:
            errors.append({
                'line': item.get('line', item.get('id', '?')),
                'text': text[:50],
                'speaker_gt': speaker_gt,
                'predicted': predicted,
                'context_before': (context_before or note or '')[:50],
            })

    total = len(test_data)
    return {
        'accuracy': correct / total if total > 0 else 0,
        'correct': correct,
        'total': total,
        'errors': errors,
    }


def _apply_config(matcher: SpeakerMatcher, key: str, value: float):
    """将参数应用到 SpeakerMatcher 实例或 config 常量。"""
    # 信号源置信度（覆盖 config 常量）
    sm_config_map = {
        'CONFIDENCE_SRL_ARG0': 'CONFIDENCE_SRL_ARG0',
        'CONFIDENCE_NER_MULTIPLIER': 'CONFIDENCE_NER_MULTIPLIER',
        'CONFIDENCE_MENTIONED_CHARACTERS': 'CONFIDENCE_MENTIONED_CHARACTERS',
        'CONFIDENCE_CHARACTER_LIBRARY': 'CONFIDENCE_CHARACTER_LIBRARY',
    }
    if key in sm_config_map:
        setattr(sm_config, key, value)
        return

    # SpeakerMatcher 属性
    matcher_attr_map = {
        'RECENCY_DECAY_RECENT': 'recency_decay_recent',
        'RECENCY_DECAY_SECOND': 'recency_decay_second',
        'RECENCY_DECAY_OTHER': 'recency_decay_other',
        'ACTIVITY_DECAY_FACTOR': 'activity_decay_factor',
        'ACTIVITY_INCREMENT': 'activity_increment',
        'CHARACTER_ELIGIBLE_MIN_FREQ': 'character_eligible_min_freq',
        'PROMOTION_THRESHOLD': 'promotion_threshold',
        'CHARACTER_MIN_CONFIDENCE': 'character_min_confidence',
        'CONTEXT_HINT_CONFIDENCE_THRESHOLD': 'context_hint_confidence_threshold',
    }
    attr = matcher_attr_map.get(key)
    if attr and hasattr(matcher, attr):
        setattr(matcher, attr, value)


def run_benchmark(gt_files: List[Path]) -> Dict:
    """运行基准测试。"""
    import time
    project_id = f'arb_{int(time.time())}'  # 唯一project_id防止污染
    clean_project(DB_PATH, project_id)

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
        register_characters(char_manager, characters, project_id)
        matcher = SpeakerMatcher(char_manager)
        matcher.current_project_id = project_id

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
    """网格搜索：遍历多组关键参数。"""
    import time
    project_id = f'arb_grid_{int(time.time())}'
    clean_project(DB_PATH, project_id)

    test_data, characters = load_gt_data(gt_file)

    if not test_data:
        return []

    print(f"\n网格搜索: {gt_file.name}")
    print(f"角色数: {len(characters)}")
    print(f"对话数: {len(test_data)}")

    results = []
    configs_to_test = [
        # 组1: 近因衰减 (5×4×4=80)
        {
            'name': '近因衰减',
            'params': {
                'RECENCY_DECAY_RECENT': [0.10, 0.15, 0.20, 0.25, 0.30],
                'RECENCY_DECAY_SECOND': [0.05, 0.10, 0.15, 0.20],
                'RECENCY_DECAY_OTHER': [0.02, 0.05, 0.08, 0.10],
            }
        },
        # 组2: 活跃度衰减+增量 (5×5=25)
        {
            'name': '活跃度参数',
            'params': {
                'ACTIVITY_DECAY_FACTOR': [0.01, 0.03, 0.05, 0.08, 0.10],
                'ACTIVITY_INCREMENT': [0.5, 0.8, 1.0, 1.5, 2.0],
            }
        },
        # 组3: 角色资格频率+晋升阈值 (6×4=24)
        {
            'name': '角色门槛',
            'params': {
                'CHARACTER_ELIGIBLE_MIN_FREQ': [1, 2, 3, 5, 8, 10],
                'PROMOTION_THRESHOLD': [1, 2, 3, 5],
            }
        },
        # 组4: 置信度阈值 (5×5=25)
        {
            'name': '置信度阈值',
            'params': {
                'CHARACTER_MIN_CONFIDENCE': [0.3, 0.4, 0.5, 0.6, 0.7],
                'CONTEXT_HINT_CONFIDENCE_THRESHOLD': [0.1, 0.2, 0.3, 0.4, 0.5],
            }
        },
        # 组5: 信号源置信度（并行竞争核心参数）(4×5×3×3=180)
        {
            'name': '信号源置信度',
            'params': {
                'CONFIDENCE_SRL_ARG0': [0.70, 0.80, 0.85, 0.90, 0.95],
                'CONFIDENCE_NER_MULTIPLIER': [0.60, 0.70, 0.80, 0.85, 0.90],
                'CONFIDENCE_MENTIONED_CHARACTERS': [0.50, 0.60, 0.75],
                'CONFIDENCE_CHARACTER_LIBRARY': [0.40, 0.50, 0.60],
            }
        },
    ]

    # 保存默认配置（用于恢复）
    default_sm_config = {
        key: getattr(sm_config, key)
        for group in configs_to_test
        for key in group['params'].keys()
        if hasattr(sm_config, key)
    }

    for group in configs_to_test:
        group_name = group['name']
        param_space = group['params']

        # 生成参数组合
        from itertools import product
        keys = list(param_space.keys())
        values = list(param_space.values())

        combos = list(product(*values))
        print(f"\n{'='*50}")
        print(f"参数组: {group_name}")
        print(f"参数: {keys}")
        print(f"组合数: {len(combos)}")

        for combo in combos:
            config = dict(zip(keys, combo))
            # 应用信号源置信度
            for key, value in config.items():
                if hasattr(sm_config, key):
                    setattr(sm_config, key, value)

            char_manager = CharacterManager()
            register_characters(char_manager, characters, project_id)
            matcher = SpeakerMatcher(char_manager)
            matcher.current_project_id = project_id
            result = run_single_config(test_data, matcher, config)
            result['config'] = config
            result['group'] = group_name
            results.append(result)

        # 恢复默认配置
        for key, value in default_sm_config.items():
            if hasattr(sm_config, key):
                setattr(sm_config, key, value)

    # 全局排序
    results.sort(key=lambda x: x['accuracy'], reverse=True)

    print(f"\n{'='*50}")
    print(f"Top 20 参数组合（跨所有参数组）:")
    for i, r in enumerate(results[:20]):
        c = r['config']
        params_str = ', '.join(f'{k}={v}' for k, v in c.items())
        print(f"  #{i+1}: acc={r['accuracy']:.2%} [{r['group']}] {params_str}")

    return results


def main():
    gt_dir = Path(__file__).parent.parent / 'tests' / 'data' / 'ground_truth'

    gt_files = [
        gt_dir / 'gt_urban_long.json',
        gt_dir / 'gt_speaker_312.json',
    ]

    if '--grid' in sys.argv:
        # 网格搜索（用312条基准测试）
        run_grid_search(gt_dir / 'gt_speaker_312.json')
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
