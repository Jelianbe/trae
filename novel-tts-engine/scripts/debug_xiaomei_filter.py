# -*- coding: utf-8 -*-
"""
调试萧媚在SpeakerRoleFilter阶段为什么被过滤
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import get_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

# GT
gt_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ground_truth.json'
ground_truth = json.loads(gt_file.read_text(encoding='utf-8'))
gt_speaking_persons = set(ground_truth['entities']['speaking_persons'])

nlp = get_nlp()
result = nlp.analyze(text)

# 统计验证
validator = get_context_validator(mode='speaker_role', whitelist=gt_speaking_persons)
validated = validator.validate(result.entities, text)

# 检查萧媚在validated中的状态
xiaomei_validated = [e for e in validated if e.text == '萧媚']
print("=" * 80)
print("调试萧媚在SpeakerRoleFilter前")
print("=" * 80)

print(f"\n【validated中'萧媚'实体数】: {len(xiaomei_validated)}")
if xiaomei_validated:
    e = xiaomei_validated[0]
    print(f"  text={e.text}, confidence={e.confidence:.2f}")

# SpeakerRoleFilter
semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()

speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)
print(f"\n【SpeakerRoleFilter配置】")
print(f"  semantic_ranker available: {speaker_filter.semantic_ranker.is_available()}")

# 查看萧媚的场景计数
# 先调用filter看看内部处理
role_entities = speaker_filter.filter(validated, text, nlp)

print(f"\n【SpeakerRoleFilter后】")
xiaomei_after = [e for e in role_entities if e.text == '萧媚']
print(f"  '萧媚'实体数: {len(xiaomei_after)}")
if xiaomei_after:
    e = xiaomei_after[0]
    print(f"  text={e.text}, confidence={e.confidence:.2f}")
else:
    print(f"  ❌ '萧媚'被过滤了")
    
    # 查看SpeakerRoleFilter的内部计数
    if hasattr(speaker_filter, '_entity_scene_count'):
        print(f"\n【SpeakerRoleFilter内部场景计数】")
        xiaomei_count = speaker_filter._entity_scene_count.get('萧媚', 0)
        print(f"  萧媚场景数: {xiaomei_count}")
    
    # 检查萧媚是否在_whitelist中
    if hasattr(speaker_filter, '_whitelist'):
        print(f"  whitelist: {speaker_filter._whitelist}")

print("\n" + "=" * 80)
