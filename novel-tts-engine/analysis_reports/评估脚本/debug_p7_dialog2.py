"""诊断P7对话2的context_before"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import tempfile, uuid
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS

P7 = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起："这枚丹药，你先服下。"萧炎点头照做。"感觉如何？"老者问道。'

def test():
    # 先看DIALOGUE_PATTERNS怎么分割对话
    for i, pattern in enumerate(DIALOGUE_PATTERNS):
        matches = list(pattern.finditer(P7))
        if matches:
            print(f'Pattern {i}: {pattern.pattern[:30]}... -> {len(matches)} matches')
            for m in matches:
                print(f'  match: [{m.group()}] at {m.start()}-{m.end()}')
    
    print()
    
    # 手工计算每段对话的context_before和context_after
    # 对话1: "这枚丹药，你先服下。"
    # 对话2: "感觉如何？"
    
    dialogue1 = '"这枚丹药，你先服下。"'
    dialogue2 = '"感觉如何？"'
    
    idx1 = P7.find(dialogue1)
    idx2 = P7.find(dialogue2)
    
    print(f'全文: {P7}')
    print(f'对话1位置: {idx1}')
    print(f'对话2位置: {idx2}')
    print()
    
    # 对话1的上下文
    ctx_before_1 = P7[:idx1].strip()
    ctx_after_1 = P7[idx1+len(dialogue1):].strip()
    print(f'对话1 context_before: "{ctx_before_1}"')
    print(f'对话1 context_after: "{ctx_after_1}"')
    print()
    
    # 对话2的上下文
    ctx_before_2 = P7[:idx2].strip()
    ctx_after_2 = P7[idx2+len(dialogue2):].strip()
    print(f'对话2 context_before: "{ctx_before_2}"')
    print(f'对话2 context_after: "{ctx_after_2}"')
    print()
    
    # 检查对话2的context_before中是否有药老
    if '药老' in ctx_before_2:
        print('对话2 context_before包含"药老"')
    else:
        print('对话2 context_before不包含"药老"')
    
    if '萧炎' in ctx_before_2:
        print('对话2 context_before包含"萧炎"')
    else:
        print('对话2 context_before不包含"萧炎"')

if __name__ == '__main__':
    test()
