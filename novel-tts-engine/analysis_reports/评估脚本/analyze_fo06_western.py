# -*- coding: utf-8 -*-
"""
FO-06 对西幻文本说话人匹配的影响分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.nlp_basics import get_nlp
from pipeline.entity_linker import get_entity_linker, reset_entity_linker
from pipeline.speaker_matcher import SpeakerMatcher, MatchResult
from pipeline.context_diversity_validator import get_context_validator, reset_context_validator

text_file = Path(__file__).parent.parent.parent / 'tests' / 'test_novel_western.txt'
text = text_file.read_text(encoding='utf-8')

gt_persons = {'艾德温', '伊莉雅', '加尔文', '莫洛克', '雷纳德', '托马斯'}
gt_dialogues = [
    {"line": "你终于来了。", "speaker": "伊莉雅"},
    {"line": "路上遇到些麻烦。", "speaker": "艾德温"},
    {"line": "北方魔法学院的援军已经在路上了，", "speaker": "艾德温"},
    {"line": "圣骑士团的伤亡如何？", "speaker": "伊莉雅"},
    {"line": "轻伤三人，", "speaker": "托马斯"},
    {"line": "雷纳德团长安排得很好，", "speaker": "托马斯"},
    {"line": "加尔文副官正在组织防御。", "speaker": "托马斯"},
    {"line": "很好，", "speaker": "伊莉雅"},
    {"line": "先安置伤员，", "speaker": "伊莉雅"},
    {"line": "魔法结界还能维持多久？", "speaker": "伊莉雅"},
    {"line": "最多两个小时。", "speaker": "艾德温"},
    {"line": "莫洛克教授已经在准备反制咒语了，", "speaker": "艾德温"},
    {"line": "他需要更多时间。", "speaker": "艾德温"},
    {"line": "两个小时足够了。", "speaker": "伊莉雅"},
    {"line": "加尔文刚才传来消息，", "speaker": "伊莉雅"},
    {"line": "北城墙已经修复。", "speaker": "伊莉雅"},
    {"line": "雷纳德说他的骑兵随时可以出击。", "speaker": "伊莉雅"},
    {"line": "让莫洛克先完成咒语，", "speaker": "艾德温"},
    {"line": "雷纳德的骑兵作为后备力量。", "speaker": "艾德温"},
    {"line": "灰石哨站的情况怎么样？", "speaker": "伊莉雅"},
    {"line": "我已经派人去查看了，", "speaker": "艾德温"},
    {"line": "托马斯会带回最新消息。", "speaker": "艾德温"},
]

nlp = get_nlp()
result = nlp.analyze(text)

# 创建两个SpeakerMatcher：一个没有FO-06，一个有FO-06
class NoFO06Matcher(SpeakerMatcher):
    """禁用了FO-06的匹配器"""
    def match_speaker(self, context):
        # 跳过match_by_trigger_words调用
        return super().match_speaker.__wrapped__(self, context) if hasattr(super().match_speaker, '__wrapped__') else None

from pipeline.speaker_matcher import MatchResult, DialogueContext

def test_matching(with_fo06=True):
    reset_context_validator()
    reset_entity_linker()
    
    matcher = SpeakerMatcher()
    matcher.char_manager.set_ground_truth(persons=list(gt_persons))
    
    # 加载语义模型
    from pipeline.semantic_ranker import get_semantic_ranker
    sr = get_semantic_ranker()
    sr.load_model()
    matcher.semantic_ranker = sr
    
    correct = 0
    total = len(gt_dialogues)
    
    for i, dl in enumerate(gt_dialogues):
        ctx = DialogueContext(
            text=dl['line'],
            chapter_id=0,
            prev_speaker=None,
        )
        result = matcher.match_speaker(ctx)
        if result and result.character.name == dl['speaker']:
            correct += 1
    
    return correct, total, correct / total * 100

print("西幻文本对话-角色匹配测试")
print("=" * 60)

# 由于FO-06的触发词是写在match_speaker内部的，直接测试
# 先临时禁用FO-06
import pipeline.speaker_matcher as sm

# 保存原始方法
original_match_by_trigger_words = sm.SpeakerMatcher.match_by_trigger_words

# 场景A: 禁用FO-06
def no_trigger_words(self, text, context):
    return None
sm.SpeakerMatcher.match_by_trigger_words = no_trigger_words

result_a = test_matching(with_fo06=False)
print(f"无FO-06: {result_a[0]}/{result_a[1]} = {result_a[2]:.1f}%")

# 场景B: 启用FO-06
sm.SpeakerMatcher.match_by_trigger_words = original_match_by_trigger_words
result_b = test_matching(with_fo06=True)
print(f"有FO-06: {result_b[0]}/{result_b[1]} = {result_b[2]:.1f}%")

print(f"\n差异: {result_b[2] - result_a[2]:+.1f}")

# 详细分析每句话的匹配情况
print("\n" + "=" * 60)
print("逐句分析")
print("=" * 60)

for with_fo06 in [False, True]:
    if with_fo06:
        sm.SpeakerMatcher.match_by_trigger_words = original_match_by_trigger_words
    else:
        sm.SpeakerMatcher.match_by_trigger_words = no_trigger_words
    
    reset_context_validator()
    reset_entity_linker()
    matcher = SpeakerMatcher()
    matcher.char_manager.set_ground_truth(persons=list(gt_persons))
    sr = get_semantic_ranker()
    sr.load_model()
    matcher.semantic_ranker = sr
    
    label = "无FO-06" if not with_fo06 else "有FO-06"
    print(f"\n{label}:")
    for i, dl in enumerate(gt_dialogues):
        ctx = DialogueContext(text=dl['line'], chapter_id=0, prev_speaker=None)
        result = matcher.match_speaker(ctx)
        matched_name = result.character.name if result else "无匹配"
        ok = "✅" if matched_name == dl['speaker'] else "❌"
        if result:
            print(f"  {ok} '{dl['line'][:20]}...' -> {matched_name} (置信度={result.confidence:.2f}, 类型={result.match_type})")
        else:
            print(f"  {ok} '{dl['line'][:20]}...' -> 无匹配")
