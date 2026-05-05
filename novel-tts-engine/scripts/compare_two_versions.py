# -*- coding: utf-8 -*-
"""双版本对比评估脚本

对比主项目（pipeline/）和 v2 版本（说说看法/）的分析模块表现。

评估目标：
1. 角色识别准确率对比
2. 情绪标注准确率对比（L1/L2）
3. 综合准确率对比
4. 错误案例分析
5. 按文体/难度/挑战类型细分对比

版本定义：
- v1 (主项目): D:\trae\novel-tts-engine\pipeline\
- v2 (说说看法): D:\trae\说说看法\pipeline\

运行方式：
    python scripts/compare_two_versions.py
"""

import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
GT_PATH = PROJECT_ROOT / 'tests' / 'role_emotion_gt_100.json'

# 两个版本的 pipeline 路径
V1_PIPELINE = PROJECT_ROOT / 'pipeline'
V2_PIPELINE = Path(r'D:\trae\说说看法\pipeline')


def load_gt(gt_path: str) -> list:
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_speaker(speaker: str) -> str:
    """标准化角色名，便于比较"""
    if not speaker:
        return ""
    if speaker.startswith("未知"):
        return "未知"
    speaker = speaker.replace("未知", "").strip()
    if speaker.endswith("角色"):
        speaker = speaker[:-2]
    speaker = re.sub(r'^[那这一][个些只]?', '', speaker)
    speaker = speaker.replace("_", "")
    return speaker


def evaluate_version(version_name: str, pipeline_dir: Path):
    """评估指定版本的 pipeline"""
    print(f"\n{'='*80}")
    print(f"评估版本: {version_name}")
    print(f"模块路径: {pipeline_dir}")
    print(f"{'='*80}")
    
    # 保存原始 sys.path 和 sys.modules
    original_path = sys.path.copy()
    original_modules = {k: v for k, v in sys.modules.items() if k.startswith('pipeline')}
    
    # 清除 pipeline 模块缓存
    pipeline_modules = [k for k in sys.modules.keys() if k.startswith('pipeline')]
    for mod in pipeline_modules:
        del sys.modules[mod]
    
    # 插入目标版本的父目录
    pipeline_parent = str(pipeline_dir.parent)
    sys.path.insert(0, pipeline_parent)
    
    try:
        # 动态导入
        from pipeline.pipeline_runner import PipelineRunner
        from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext, get_speaker_matcher
        from pipeline.character_manager import get_character_manager
        
        gt_data = load_gt(GT_PATH)
        
        # L1 映射
        L2_TO_L1 = {
            'joy': 'excited', 'anger': 'excited', 'surprise': 'excited',
            'sadness': 'subdued', 'fear': 'subdued', 'neutral': 'neutral',
        }
        
        results = {
            'total': len(gt_data),
            'speaker_correct': 0,
            'emotion_l1_correct': 0,
            'emotion_l2_correct': 0,
            'both_correct': 0,
            'errors': [],
            'by_style': defaultdict(lambda: {'total': 0, 'speaker': 0, 'emotion_l1': 0, 'emotion_l2': 0}),
            'by_role_challenge': defaultdict(lambda: {'total': 0, 'speaker': 0}),
            'by_emotion_challenge': defaultdict(lambda: {'total': 0, 'emotion_l1': 0}),
            'speaker_confusion': defaultdict(lambda: defaultdict(int)),
            'emotion_confusion': defaultdict(lambda: defaultdict(int)),
        }
        
        start_time = time.time()
        
        for i, item in enumerate(gt_data):
            if i % 20 == 0:
                print(f"  进度: {i}/{len(gt_data)}")
            
            item_id = item['id']
            text = item['text']
            context_before = item.get('context_before', '')
            context_after = item.get('context_after', '')
            style = item.get('style', 'unknown')
            gt_speaker = item['speaker']
            gt_emotion = item['emotion_label']
            role_challenge = item.get('role_challenge', 'unknown')
            emotion_challenge = item.get('emotion_challenge', 'unknown')
            
            full_text = f"{context_before}\n{text}\n{context_after}"
            
            pred_speaker = ""
            pred_emotion = "neutral"
            
            try:
                runner = PipelineRunner()
                speaker_matcher = get_speaker_matcher()
                
                chapter_results = runner.analyze_chapters(full_text, force=True)
                
                all_sentences = []
                for cr in chapter_results:
                    all_sentences.extend(cr.sentences)
                
                target_sentence = None
                target_text = text.strip()
                for s in all_sentences:
                    if s.text.strip() == target_text:
                        target_sentence = s
                        break
                    if target_text in s.text:
                        target_sentence = s
                        break
                
                if target_sentence:
                    pred_speaker = target_sentence.speaker
                    pred_emotion = target_sentence.emotion
                    
                    # 尝试上下文推理覆盖
                    if context_before or context_after:
                        context_obj = DialogueContext(
                            text=text,
                            context_before=context_before,
                            context_after=context_after,
                            mentioned_characters=[]
                        )
                        match_result = speaker_matcher.match_speaker(context_obj)
                        if match_result:
                            pred_speaker = match_result.character.name
            except Exception as e:
                pass
            
            # 标准化和判断
            gt_speaker_norm = normalize_speaker(gt_speaker)
            pred_speaker_norm = normalize_speaker(pred_speaker)
            
            speaker_ok = (gt_speaker_norm == pred_speaker_norm) or (not gt_speaker_norm and not pred_speaker_norm)
            
            gt_emotion_l1 = L2_TO_L1.get(gt_emotion, gt_emotion)
            pred_emotion_l1 = L2_TO_L1.get(pred_emotion, pred_emotion)
            
            emotion_l2_ok = (gt_emotion == pred_emotion)
            emotion_l1_ok = (gt_emotion_l1 == pred_emotion_l1)
            
            # 更新统计
            results['by_style'][style]['total'] += 1
            results['by_role_challenge'][role_challenge]['total'] += 1
            results['by_emotion_challenge'][emotion_challenge]['total'] += 1
            
            if speaker_ok:
                results['speaker_correct'] += 1
                results['by_style'][style]['speaker'] += 1
                results['by_role_challenge'][role_challenge]['speaker'] += 1
            
            if emotion_l1_ok:
                results['emotion_l1_correct'] += 1
                results['by_style'][style]['emotion_l1'] += 1
                results['by_emotion_challenge'][emotion_challenge]['emotion_l1'] += 1
            
            if emotion_l2_ok:
                results['emotion_l2_correct'] += 1
                results['by_style'][style]['emotion_l2'] += 1
            
            if speaker_ok and emotion_l1_ok:
                results['both_correct'] += 1
            
            if not speaker_ok or not emotion_l1_ok:
                results['errors'].append({
                    'id': item_id,
                    'text': text[:50],
                    'gt_speaker': gt_speaker,
                    'pred_speaker': pred_speaker,
                    'gt_emotion': gt_emotion,
                    'pred_emotion': pred_emotion,
                    'gt_emotion_l1': gt_emotion_l1,
                    'pred_emotion_l1': pred_emotion_l1,
                    'speaker_ok': speaker_ok,
                    'emotion_l1_ok': emotion_l1_ok,
                    'emotion_l2_ok': emotion_l2_ok,
                    'style': style,
                    'role_challenge': role_challenge,
                    'emotion_challenge': emotion_challenge,
                })
            
            results['speaker_confusion'][gt_speaker][pred_speaker] += 1
            results['emotion_confusion'][gt_emotion][pred_emotion] += 1
        
        elapsed = time.time() - start_time
        results['elapsed'] = elapsed
        results['speaker_accuracy'] = results['speaker_correct'] / results['total']
        results['emotion_l1_accuracy'] = results['emotion_l1_correct'] / results['total']
        results['emotion_l2_accuracy'] = results['emotion_l2_correct'] / results['total']
        results['both_accuracy'] = results['both_correct'] / results['total']
        
        # 转换为普通 dict
        results['by_style'] = dict(results['by_style'])
        results['by_role_challenge'] = dict(results['by_role_challenge'])
        results['by_emotion_challenge'] = dict(results['by_emotion_challenge'])
        results['speaker_confusion'] = {k: dict(v) for k, v in results['speaker_confusion'].items()}
        results['emotion_confusion'] = {k: dict(v) for k, v in results['emotion_confusion'].items()}
        
        return results
        
    finally:
        # 恢复
        sys.path = original_path
        pipeline_modules = [k for k in sys.modules.keys() if k.startswith('pipeline')]
        for mod in pipeline_modules:
            del sys.modules[mod]
        for mod, val in original_modules.items():
            sys.modules[mod] = val


def print_comparison_report(v1: dict, v2: dict):
    """打印对比报告"""
    print("\n" + "=" * 80)
    print("双版本对比评估报告")
    print("=" * 80)
    
    print(f"\n{'指标':<28} {'v1 (主项目)':<18} {'v2 (说说看法)':<18} {'变化':<10}")
    print("-" * 80)
    
    metrics = [
        ('测试样本数', v1['total'], v2['total'], False),
        ('角色识别准确率', f"{v1['speaker_accuracy']:.1%}", f"{v2['speaker_accuracy']:.1%}", True),
        ('情绪标注准确率 L1(3类)', f"{v1['emotion_l1_accuracy']:.1%}", f"{v2['emotion_l1_accuracy']:.1%}", True),
        ('情绪标注准确率 L2(6类)', f"{v1['emotion_l2_accuracy']:.1%}", f"{v2['emotion_l2_accuracy']:.1%}", True),
        ('综合准确率（两者都对）', f"{v1['both_accuracy']:.1%}", f"{v2['both_accuracy']:.1%}", True),
        ('耗时', f"{v1['elapsed']:.1f}s", f"{v2['elapsed']:.1f}s", False),
    ]
    
    for name, v1_val, v2_val, is_pct in metrics:
        if is_pct:
            v1_num = float(v1_val.rstrip('%')) / 100
            v2_num = float(v2_val.rstrip('%')) / 100
            diff = v2_num - v1_num
            diff_str = f"+{diff:.1%}" if diff >= 0 else f"{diff:.1%}"
        else:
            diff_str = ""
        print(f"{name:<28} {str(v1_val):<18} {str(v2_val):<18} {diff_str:<10}")
    
    # 按文体对比
    print(f"\n{'按文体统计':<20}")
    print("-" * 80)
    
    all_styles = sorted(set(list(v1['by_style'].keys()) + list(v2['by_style'].keys())))
    
    print(f"{'文体':<8} {'v1角色':<10} {'v2角色':<10} {'角色差异':<10} {'v1情绪L1':<10} {'v2情绪L1':<10} {'情绪差异':<10}")
    print("-" * 80)
    
    for style in all_styles:
        v1_s = v1['by_style'].get(style, {})
        v2_s = v2['by_style'].get(style, {})
        v1_t = v1_s.get('total', 0)
        v2_t = v2_s.get('total', 0)
        
        v1_s_acc = v1_s.get('speaker', 0) / v1_t if v1_t > 0 else 0
        v2_s_acc = v2_s.get('speaker', 0) / v2_t if v2_t > 0 else 0
        v1_e_acc = v1_s.get('emotion_l1', 0) / v1_t if v1_t > 0 else 0
        v2_e_acc = v2_s.get('emotion_l1', 0) / v2_t if v2_t > 0 else 0
        
        s_diff = v2_s_acc - v1_s_acc
        e_diff = v2_e_acc - v1_e_acc
        
        print(f"{style:<8} {v1_s_acc:.1%}       {v2_s_acc:.1%}       {'+' if s_diff>0 else ''}{s_diff:+.1%}     {v1_e_acc:.1%}       {v2_e_acc:.1%}       {'+' if e_diff>0 else ''}{e_diff:+.1%}")
    
    # 角色识别挑战类型对比
    print(f"\n{'按角色挑战类型统计':<20}")
    print("-" * 80)
    
    all_rc = sorted(set(list(v1['by_role_challenge'].keys()) + list(v2['by_role_challenge'].keys())))[:10]
    
    print(f"{'挑战类型':<40} {'v1准确率':<12} {'v2准确率':<12} {'差异':<10}")
    print("-" * 80)
    
    for rc in all_rc:
        v1_rc = v1['by_role_challenge'].get(rc, {})
        v2_rc = v2['by_role_challenge'].get(rc, {})
        v1_t = v1_rc.get('total', 0)
        v2_t = v2_rc.get('total', 0)
        
        v1_acc = v1_rc.get('speaker', 0) / v1_t if v1_t > 0 else 0
        v2_acc = v2_rc.get('speaker', 0) / v2_t if v2_t > 0 else 0
        diff = v2_acc - v1_acc
        
        rc_short = rc[:38] + '..' if len(rc) > 40 else rc
        print(f"{rc_short:<40} {v1_acc:.1%}        {v2_acc:.1%}        {'+' if diff>0 else ''}{diff:+.1%}")
    
    # 情绪标注挑战类型对比
    print(f"\n{'按情绪挑战类型统计':<20}")
    print("-" * 80)
    
    all_ec = sorted(set(list(v1['by_emotion_challenge'].keys()) + list(v2['by_emotion_challenge'].keys())))[:10]
    
    print(f"{'挑战类型':<40} {'v1准确率':<12} {'v2准确率':<12} {'差异':<10}")
    print("-" * 80)
    
    for ec in all_ec:
        v1_ec = v1['by_emotion_challenge'].get(ec, {})
        v2_ec = v2['by_emotion_challenge'].get(ec, {})
        v1_t = v1_ec.get('total', 0)
        v2_t = v2_ec.get('total', 0)
        
        v1_acc = v1_ec.get('emotion_l1', 0) / v1_t if v1_t > 0 else 0
        v2_acc = v2_ec.get('emotion_l1', 0) / v2_t if v2_t > 0 else 0
        diff = v2_acc - v1_acc
        
        ec_short = ec[:38] + '..' if len(ec) > 40 else ec
        print(f"{ec_short:<40} {v1_acc:.1%}        {v2_acc:.1%}        {'+' if diff>0 else ''}{diff:+.1%}")
    
    # 情绪混淆矩阵对比
    print(f"\n{'情绪混淆矩阵 (v1)':<30}")
    print("-" * 50)
    _print_confusion_matrix(v1['emotion_confusion'])
    
    print(f"\n{'情绪混淆矩阵 (v2)':<30}")
    print("-" * 50)
    _print_confusion_matrix(v2['emotion_confusion'])
    
    # 错误对比分析
    v1_error_ids = {e['id'] for e in v1['errors']}
    v2_error_ids = {e['id'] for e in v2['errors']}
    common_errors = v1_error_ids & v2_error_ids
    v1_only = v1_error_ids - v2_error_ids
    v2_only = v2_error_ids - v1_error_ids
    
    print(f"\n{'错误对比分析':<20}")
    print("-" * 80)
    print(f"v1 错误数: {len(v1['errors'])}")
    print(f"v2 错误数: {len(v2['errors'])}")
    print(f"共同错误: {len(common_errors)}")
    print(f"v1 独有错误（v2 修好了）: {len(v1_only)}")
    print(f"v2 独有错误（v2 新引入）: {len(v2_only)}")
    
    if v1_only:
        print(f"\nv2 修好的案例（前5条）:")
        for e in v1['errors']:
            if e['id'] in v1_only:
                print(f"  {e['id']}: {e['text'][:40]}")
                if not e['speaker_ok']:
                    print(f"    角色: GT={e['gt_speaker']} v1={e['pred_speaker']} -> v2=正确")
                if not e['emotion_l1_ok']:
                    print(f"    情绪: GT={e['gt_emotion']}({e['gt_emotion_l1']}) v1={e['pred_emotion']}({e['pred_emotion_l1']}) -> v2=正确")
                if len([x for x in v1['errors'] if x['id'] in v1_only]) <= 5:
                    pass
    
    if v2_only:
        print(f"\nv2 新引入的错误（前5条）:")
        for e in v2['errors']:
            if e['id'] in v2_only:
                print(f"  {e['id']}: {e['text'][:40]}")
                if not e['speaker_ok']:
                    print(f"    角色: GT={e['gt_speaker']} v1=正确 -> v2={e['pred_speaker']}")
                if not e['emotion_l1_ok']:
                    print(f"    情绪: GT={e['gt_emotion']}({e['gt_emotion_l1']}) v1=正确 -> v2={e['pred_emotion']}({e['pred_emotion_l1']})")


def _print_confusion_matrix(confusion: dict):
    """打印混淆矩阵"""
    emotions = sorted(set(list(confusion.keys()) + [p for preds in confusion.values() for p in preds.keys()]))
    
    # 表头
    header = "GT\\Pred  " + "  ".join(f"{e[:6]:<7}" for e in emotions[:6])
    print(header)
    print("-" * len(header))
    
    for gt in emotions[:6]:
        row = f"{gt:<8}"
        for pred in emotions[:6]:
            count = confusion.get(gt, {}).get(pred, 0)
            row += f"{count:<8}"
        print(row)


def main():
    print("双版本对比评估脚本")
    print("=" * 80)
    print(f"v1 (主项目): {V1_PIPELINE}")
    print(f"v2 (说说看法): {V2_PIPELINE}")
    print(f"测试集: {GT_PATH}")
    
    # 验证路径
    if not V1_PIPELINE.exists():
        print(f"错误: v1 pipeline 不存在 - {V1_PIPELINE}")
        return
    
    if not V2_PIPELINE.exists():
        print(f"错误: v2 pipeline 不存在 - {V2_PIPELINE}")
        return
    
    if not GT_PATH.exists():
        print(f"错误: 测试数据不存在 - {GT_PATH}")
        return
    
    # 评估 v1
    v1_result = evaluate_version("v1 (主项目)", V1_PIPELINE)
    
    # 评估 v2
    v2_result = evaluate_version("v2 (说说看法)", V2_PIPELINE)
    
    # 打印对比报告
    print_comparison_report(v1_result, v2_result)
    
    # 导出 JSON 报告
    output_dir = PROJECT_ROOT / 'analysis_reports' / '优化报告'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report = {
        'v1': v1_result,
        'v2': v2_result,
        'summary': {
            'v1_speaker': f"{v1_result['speaker_accuracy']:.1%}",
            'v2_speaker': f"{v2_result['speaker_accuracy']:.1%}",
            'speaker_diff': f"{v2_result['speaker_accuracy'] - v1_result['speaker_accuracy']:+.1%}",
            'v1_emotion_l1': f"{v1_result['emotion_l1_accuracy']:.1%}",
            'v2_emotion_l1': f"{v2_result['emotion_l1_accuracy']:.1%}",
            'emotion_l1_diff': f"{v2_result['emotion_l1_accuracy'] - v1_result['emotion_l1_accuracy']:+.1%}",
            'v1_both': f"{v1_result['both_accuracy']:.1%}",
            'v2_both': f"{v2_result['both_accuracy']:.1%}",
            'both_diff': f"{v2_result['both_accuracy'] - v1_result['both_accuracy']:+.1%}",
        }
    }
    
    output_path = output_dir / '双版本对比评估报告_20260505.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nJSON报告已导出: {output_path}")


if __name__ == '__main__':
    main()
