# -*- coding: utf-8 -*-
"""
排查萧媚漏报：逐段检查萧媚在对话中的出现情况

目标：
1. 确认萧媚是否在对话场景中出现
2. 检查SpeakerRoleFilter为什么没有捕获她
3. 如果应该被捕获，找出管道中的问题
"""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.context_diversity_validator import get_context_validator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.semantic_ranker import get_semantic_ranker

# 读取测试文本
text_file = Path(__file__).parent.parent / 'tests' / 'test_novel_doupo_ch1-10.txt'
text = text_file.read_text(encoding='utf-8')

print("=" * 80)
print("排查萧媚漏报：逐段检查")
print("=" * 80)

# Step 1: 找到所有"萧媚"出现的位置
xiaomei_pattern = re.compile('萧媚')
matches = list(xiaomei_pattern.finditer(text))

print(f"\n【萧媚在文本中的出现位置】：共{len(matches)}次")
for i, m in enumerate(matches):
    # 提取上下文（前后100字符）
    start = max(0, m.start() - 50)
    end = min(len(text), m.end() + 100)
    context = text[start:end].replace('\n', ' ')
    
    # 检查是否有对话标记
    has_dialogue_marker = any(keyword in context for keyword in ['道', '说', '问', '喊', '笑', '答', '应'])
    has_quote = any(c in context for c in ['"', '"', ''', ''', '「', '」'])
    
    print(f"\n[{i+1}] 位置 {m.start()}")
    print(f"    上下文: ...{context}...")
    print(f"    有对话标记: {'是' if has_dialogue_marker else '否'}")
    print(f"    有引号: {'是' if has_quote else '否'}")

# Step 2: 检查SpeakerRoleFilter的内部逻辑
print(f"\n\n{'=' * 80}")
print("【SpeakerRoleFilter内部检查】")
print("=" * 80)

nlp = get_nlp()
result = nlp.analyze(text)
per_entities = [e for e in result.entities if e.type == 'PER']

# 统计验证
validator = get_context_validator(mode='speaker_role', whitelist=set())
validated = validator.validate(per_entities, text)

# 找到萧媚实体
xiaomei_entities = [e for e in validated if e.text == '萧媚']
print(f"\n萧媚实体数: {len(xiaomei_entities)}")
if xiaomei_entities:
    e = xiaomei_entities[0]
    print(f"  confidence: {e.confidence:.2f}")
    print(f"  start: {e.start}, end: {e.end}")
    
    # 检查萧媚的上下文
    context_start = max(0, e.start - 50)
    context_end = min(len(text), e.end + 50)
    context = text[context_start:context_end]
    print(f"  上下文: ...{context}...")

# Step 3: 检查SpeakerRoleFilter的场景计数
print(f"\n\n{'=' * 80}")
print("【SpeakerRoleFilter场景计数检查】")
print("=" * 80)

semantic_ranker = get_semantic_ranker()
semantic_ranker.load_model()

speaker_filter = SpeakerRoleFilter(semantic_ranker=semantic_ranker)

# 运行filter来填充内部计数
_ = speaker_filter.filter(validated, text, nlp)

# 检查萧媚的场景计数
xiaomei_scene_count = speaker_filter._entity_scene_count.get('萧媚', 0)
print(f"\n萧媚的场景计数: {xiaomei_scene_count}")

# 检查SpeakerRoleFilter的对话分割
if hasattr(speaker_filter, '_dialogue_spans'):
    print(f"对话片段数: {len(speaker_filter._dialogue_spans)}")
    
    # 检查萧媚是否在任何对话片段中
    xiaomei_in_dialogue = False
    for span in speaker_filter._dialogue_spans:
        if hasattr(span, 'start') and hasattr(span, 'end'):
            if any(e.start >= span.start and e.end <= span.end for e in xiaomei_entities):
                xiaomei_in_dialogue = True
                break
    
    print(f"萧媚在对话片段中: {'是' if xiaomei_in_dialogue else '否'}")

# Step 4: 分析萧媚的对话上下文
print(f"\n\n{'=' * 80}")
print("【萧媚的对话上下文分析】")
print("=" * 80)

# 找到所有包含"萧媚"的句子
sentences = text.replace('\n', ' ').replace('。', '。\n').replace('！', '！\n').replace('？', '？\n').split('\n')
xiaomei_sentences = [s for s in sentences if '萧媚' in s]

print(f"\n包含'萧媚'的句子数: {len(xiaomei_sentences)}")
for i, s in enumerate(xiaomei_sentences):
    print(f"\n[{i+1}] {s.strip()}")
    
    # 检查是否有说话人标识
    if any(keyword in s for keyword in ['萧媚道', '萧媚说', '萧媚问', '萧媚笑']):
        print("    → 有明确的说话人标识")
    else:
        print("    → 无明确说话人标识")

print("\n" + "=" * 80)
print("分析结论：")
print("=" * 80)
print("1. 如果萧媚有明确的'萧媚道'类标识，SpeakerRoleFilter应该能捕获")
print("2. 如果没有明确标识，但她在对话上下文中，可能需要改进对话检测逻辑")
print("3. 如果她确实不在对话场景中，那么漏报是合理的（GT标注可能有误）")
