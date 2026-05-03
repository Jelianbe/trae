#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能基准测试：测量管道处理速度

用途：
1. 建立当前版本的性能基线
2. 验证优化后的性能提升
3. 检测性能回归

使用方法：
    python scripts/benchmark_pipeline.py --chapters 10
    python scripts/benchmark_pipeline.py --chapters 50 --profile
"""

import sys
import time
import cProfile
import pstats
import io
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_runner import PipelineRunner, get_pipeline_runner, reset_pipeline_runner
from pipeline.character_manager import get_character_manager, reset_character_manager


def generate_test_text(num_chapters: int = 10) -> str:
    """
    生成测试用小说文本
    
    Args:
        num_chapters: 章节数量
    
    Returns:
        测试文本
    """
    chapters = []
    for i in range(1, num_chapters + 1):
        chapter = f"""
第{i}章 测试章节

萧炎缓缓睁开眼睛，目光扫过四周。
"这是哪里？"他心中暗想。

药老的声音在脑海中响起："你终于醒了。"

"药老，我昏迷了多久？"萧炎问道。

"差不多三天了。"药老回答道，"你之前的修炼太过急躁，差点走火入魔。"

萧炎苦笑着摇了摇头："我知道了，以后会注意的。"

此时，远处传来一阵脚步声。一个身着青衫的青年快步走来。
"萧炎，你没事吧？"青年关切地问道。

"林轩，我没事。"萧炎站起身来，"多谢关心。"

两人相视一笑，并肩向山下走去。

石碑上刻着几个大字："斗之力，三段。"

萧炎心中暗忖："这就是我的起点吗？"
"""
        chapters.append(chapter)
    
    return "\n".join(chapters)


def benchmark_pipeline(num_chapters: int = 10, use_profile: bool = False) -> dict:
    """
    运行基准测试
    
    Args:
        num_chapters: 测试章节数
        use_profile: 是否启用性能分析
    
    Returns:
        测试结果字典
    """
    # 重置全局实例（确保干净的测试环境）
    reset_pipeline_runner()
    reset_character_manager()
    
    # 生成测试文本
    print(f"生成 {num_chapters} 章测试文本...")
    test_text = generate_test_text(num_chapters)
    print(f"文本长度：{len(test_text)} 字符")
    print()
    
    # 获取管道实例
    runner = get_pipeline_runner()
    
    # 运行测试
    print("开始处理...")
    start_time = time.perf_counter()
    
    if use_profile:
        # 启用性能分析
        pr = cProfile.Profile()
        pr.enable()
        results = runner.analyze_chapters(test_text, force=True, cache_key="benchmark")
        pr.disable()
        
        # 输出性能分析报告
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(30)  # 前 30 个最耗时的函数
        print("\n=== 性能分析报告（Top 30 耗时函数）===")
        print(s.getvalue())
    else:
        results = runner.analyze_chapters(test_text, force=True, cache_key="benchmark")
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    # 统计结果
    total_sentences = sum(len(r.sentences) for r in results)
    total_dialogues = sum(r.statistics.get('dialogue_count', 0) for r in results)
    total_entities = sum(r.statistics.get('entity_count', 0) for r in results)
    
    print("\n=== 基准测试结果 ===")
    print(f"处理章节数：{len(results)}")
    print(f"总句子数：{total_sentences}")
    print(f"总对话数：{total_dialogues}")
    print(f"总实体数：{total_entities}")
    print(f"处理时间：{elapsed:.3f} 秒")
    print(f"每章平均时间：{elapsed/len(results):.3f} 秒")
    print(f"每秒处理章节：{len(results)/elapsed:.2f} 章/秒")
    print()
    
    return {
        'num_chapters': len(results),
        'total_sentences': total_sentences,
        'total_dialogues': total_dialogues,
        'total_entities': total_entities,
        'elapsed_seconds': elapsed,
        'seconds_per_chapter': elapsed / len(results) if results else 0,
        'chapters_per_second': len(results) / elapsed if elapsed > 0 else 0,
    }


def compare_baselines(before: dict, after: dict):
    """
    对比优化前后的性能
    
    Args:
        before: 优化前的测试结果
        after: 优化后的测试结果
    """
    print("\n=== 性能对比 ===")
    print(f"{'指标':<20} {'优化前':<15} {'优化后':<15} {'提升':<10}")
    print("-" * 60)
    
    elapsed_before = before['elapsed_seconds']
    elapsed_after = after['elapsed_seconds']
    improvement = ((elapsed_before - elapsed_after) / elapsed_before) * 100
    
    print(f"{'处理时间（秒）':<20} {elapsed_before:<15.3f} {elapsed_after:<15.3f} {improvement:+.1f}%")
    
    spc_before = before['seconds_per_chapter']
    spc_after = after['seconds_per_chapter']
    improvement_spc = ((spc_before - spc_after) / spc_before) * 100
    print(f"{'每章时间（秒）':<20} {spc_before:<15.3f} {spc_after:<15.3f} {improvement_spc:+.1f}%")
    
    cps_before = before['chapters_per_second']
    cps_after = after['chapters_per_second']
    improvement_cps = ((cps_after - cps_before) / cps_before) * 100
    print(f"{'每秒章节数':<20} {cps_before:<15.2f} {cps_after:<15.2f} {improvement_cps:+.1f}%")
    print()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='管道性能基准测试')
    parser.add_argument('--chapters', type=int, default=10, help='测试章节数（默认 10）')
    parser.add_argument('--profile', action='store_true', help='启用性能分析')
    parser.add_argument('--compare', action='store_true', help='对比模式（运行两次）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("novel-tts-engine 管道性能基准测试")
    print("=" * 60)
    print()
    
    if args.compare:
        # 对比模式：运行两次
        print(">>> 第一次运行（优化前）")
        before_result = benchmark_pipeline(args.chapters, args.profile)
        
        print("\n" + "=" * 60)
        print(">>> 第二次运行（优化后）")
        after_result = benchmark_pipeline(args.chapters, args.profile)
        
        compare_baselines(before_result, after_result)
    else:
        benchmark_pipeline(args.chapters, args.profile)
