#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修仙传全文测试脚本
- 读取 Desktop/修仙传(1).txt
- 提取对话（使用 DIALOGUE_PATTERNS）
- 调用 speaker_matcher 识别说话人
- 输出准确率统计和错误明细
"""

import sys, os, re, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS

# 修仙传路径
XIUXIAN_PATH = r"C:\Users\月笙如歌\Desktop\修仙传(1).txt"

def extract_dialogues(text):
    """提取所有对话及其上下文"""
    dialogues = []
    lines = text.split('\n')
    full_text = '\n'.join(lines)
    
    for pattern in DIALOGUE_PATTERNS:
        for match in pattern.finditer(full_text):
            start = max(0, match.start() - 200)
            end = min(len(full_text), match.end() + 200)
            context_before = full_text[start:match.start()]
            context_after = full_text[match.end():end]
            dialogues.append({
                'text': match.group(),
                'context_before': context_before,
                'context_after': context_after,
                'position': match.start()
            })
    
    dialogues.sort(key=lambda d: d['position'])
    return dialogues

def main():
    print("=" * 60)
    print(" 修仙传全文说话人识别测试")
    print("=" * 60)
    
    # 读取修仙传
    if not os.path.exists(XIUXIAN_PATH):
        print(f"错误: 文件不存在 {XIUXIAN_PATH}")
        return
    
    with open(XIUXIAN_PATH, 'r', encoding='utf-8') as f:
        xiuxian_text = f.read()
    
    print(f"\n修仙传文件大小: {len(xiuxian_text):,} 字符")
    print(f"修仙传总行数: {xiuxian_text.count(chr(10)):,} 行")
    
    # 提取对话
    dialogues = extract_dialogues(xiuxian_text)
    print(f"\n提取到 {len(dialogues)} 个对话")
    
    # 初始化角色管理器
    import tempfile
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    
    project_id = "xiuxian_full_test"
    
    # 创建修仙传角色（从修仙传诊断报告中提取的角色）
    characters = [
        ('孙项明', 'male'),
        ('郭垣', 'male'),
        ('郭垣正', 'male'),  # 可能是别名
        ('林家管事', 'male'),
        ('管事', 'male'),
        ('中年修士', 'male'),
    ]
    
    for name, gender in characters:
        try:
            cm.add_character(name=name, project_id=project_id, gender=gender)
        except Exception:
            pass
    
    # 初始化说话人匹配器
    from pipeline.semantic_ranker import get_semantic_ranker
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    # 运行测试
    print(f"\n开始测试 {len(dialogues)} 个对话...")
    start_time = time.time()
    
    results = []
    correct = 0
    unknown = 0
    wrong = 0
    
    for i, dlg in enumerate(dialogues):
        # 获取上下文
        ctx_before = dlg['context_before'][-300:]  # 取最后300字符
        ctx_after = dlg['context_after'][:300]  # 取前300字符
        
        # 调用说话人匹配器
        candidates = sm._extract_context_speakers(
            text=dlg['text'],
            context_before=ctx_before,
            context_after=ctx_after
        )
        
        # 获取最佳候选
        if candidates:
            best = candidates[0]  # (name, reason, confidence)
            speaker_name = best[0]
            reason = best[1]
            confidence = best[2]
        else:
            speaker_name = "未知"
            reason = "无候选"
            confidence = 0.0
        
        results.append({
            'index': i + 1,
            'text': dlg['text'][:50],
            'speaker': speaker_name,
            'reason': reason,
            'confidence': confidence,
        })
        
        if speaker_name.startswith('未知'):
            unknown += 1
        else:
            correct += 1  # 暂时算正确，因为修仙传没有标准答案
    
    elapsed = time.time() - start_time
    
    print(f"\n测试完成! 耗时: {elapsed:.2f}秒")
    print(f"\n{'='*60}")
    print(f" 统计结果")
    print(f"{'='*60}")
    print(f" 总对话数: {len(dialogues)}")
    print(f" 识别出说话人: {correct} ({correct/len(dialogues):.1%})")
    print(f" 未知: {unknown} ({unknown/len(dialogues):.1%})")
    print(f" 平均耗时/对话: {elapsed/len(dialogues)*1000:.0f}ms")
    
    # 输出前20个结果
    print(f"\n{'='*60}")
    print(f" 前20个对话识别结果")
    print(f"{'='*60}")
    for r in results[:20]:
        print(f"  {r['index']:3d}. [{r['speaker']:<8s}] (置信度={r['confidence']:.2f}, {r['reason']})")
        print(f"       {r['text']}")
    
    # 输出未知结果
    unknown_results = [r for r in results if r['speaker'].startswith('未知')]
    if unknown_results:
        print(f"\n{'='*60}")
        print(f" 未知说话人 ({len(unknown_results)}个)")
        print(f"{'='*60}")
        for r in unknown_results[:20]:
            print(f"  {r['index']:3d}. [{r['speaker']}] ({r['reason']})")
            print(f"       {r['text']}")
    
    # 输出说话人分布
    speaker_counts = {}
    for r in results:
        speaker = r['speaker']
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    print(f"\n{'='*60}")
    print(f" 说话人分布")
    print(f"{'='*60}")
    sorted_speakers = sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True)
    for speaker, count in sorted_speakers:
        bar = '█' * (count // 2)
        print(f"  {speaker:<12s} {count:3d} {bar}")
    
    # 清理
    try:
        os.unlink(db_path)
    except:
        pass

if __name__ == '__main__':
    main()
