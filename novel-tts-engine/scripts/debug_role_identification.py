# -*- coding: utf-8 -*-
"""角色识别故障诊断脚本

按顺序排查五个环节：
1. 对话分类是否识别了对话？
2. SpeakerRoleFilter 是否从上下文中提取到候选实体？
3. CharacterManager 是否已注册角色？
4. SpeakerMatcher 执行了吗？
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pipeline_runner import PipelineRunner


def debug_single_sample(context_before, text, context_after):
    """单样本全链路调试"""
    full_text = f"{context_before}\n{text}\n{context_after}"
    
    print("=" * 80)
    print("角色识别故障诊断")
    print("=" * 80)
    print(f"\n输入文本:")
    print(f"  context_before: {context_before}")
    print(f"  text: {text}")
    print(f"  context_after: {context_after}")
    
    # 1. 运行完整 pipeline
    print("\n" + "=" * 80)
    print("环节1: 运行完整 Pipeline")
    print("=" * 80)
    
    runner = PipelineRunner()
    results = runner.analyze_chapters(full_text, force=True)
    
    # 找到所有句子和目标句子
    all_sentences = []
    for cr in results:
        all_sentences.extend(cr.sentences)
    
    print(f"\n提取的句子总数: {len(all_sentences)}")
    for i, s in enumerate(all_sentences):
        print(f"  [{i}] type={s.type:<10} speaker='{s.speaker}' text={s.text[:40]}")
    
    target = None
    for s in all_sentences:
        if text in s.text:
            target = s
            break
    
    if not target:
        print("\n❌ 未找到目标句子")
        return
    
    print(f"\n目标句子:")
    print(f"  文本: {target.text}")
    print(f"  类型: {target.type}")
    print(f"  speaker: '{target.speaker}'")
    print(f"  emotion: '{target.emotion}'")
    
    # 检查环节1结果
    if target.type == 'narration':
        print("\n❌ 问题: 句子类型是 narration 而不是 dialogue")
        print("   原因: dialogue_classifier 没识别出引号或对话")
        return
    else:
        print("\n✅ 环节1通过: 句子类型正确识别为 dialogue")
    
    # 2. 检查NER提取
    print("\n" + "=" * 80)
    print("环节2: NER 提取")
    print("=" * 80)
    
    try:
        from pipeline.nlp_basics import get_nlp
        nlp = get_nlp()
        entities = nlp.analyze(full_text)
        per_entities = [e for e in entities if e.type == 'PER']
        print(f"\n提取的 PER 实体: {[(e.text, e.confidence) for e in per_entities]}")
        
        if not per_entities:
            print("❌ 问题: 没有提取到任何 PER 实体")
            return
        else:
            print(f"✅ 环节2通过: 提取到 {len(per_entities)} 个 PER 实体")
    except Exception as e:
        print(f"❌ NLP 模块错误: {e}")
        return
    
    # 3. 检查 SpeakerRoleFilter
    print("\n" + "=" * 80)
    print("环节3: SpeakerRoleFilter 过滤")
    print("=" * 80)
    
    try:
        from pipeline.speaker_role_filter import get_speaker_role_filter
        role_filter = get_speaker_role_filter()
        filtered = role_filter.filter(per_entities, full_text)
        print(f"\n过滤后的说话角色: {[(e.text, e.confidence) for e in filtered]}")
        
        if not filtered:
            print("❌ 问题: SpeakerRoleFilter 过滤掉了所有实体")
            return
        else:
            print(f"✅ 环节3通过: 过滤后剩余 {len(filtered)} 个候选")
    except Exception as e:
        print(f"❌ SpeakerRoleFilter 错误: {e}")
        return
    
    # 4. 检查 CharacterManager
    print("\n" + "=" * 80)
    print("环节4: CharacterManager 角色注册")
    print("=" * 80)
    
    try:
        from pipeline.character_manager import get_character_manager
        char_mgr = get_character_manager()
        all_chars = char_mgr.get_all_characters()
        print(f"\n已注册角色数: {len(all_chars)}")
        if all_chars:
            print(f"已注册角色: {[c.name for c in all_chars[:10]]}")
        else:
            print("已注册角色: (无)")
        
        # 检查特定角色是否注册
        for pe in per_entities:
            char = char_mgr.get_by_name(pe.text)
            if char:
                print(f"  角色 '{pe.text}': 已注册 (id={char.id})")
            else:
                print(f"  角色 '{pe.text}': 未注册")
        
        if not all_chars:
            print("\n❌ 问题: CharacterManager 中没有任何角色")
            print("   原因: 冷启动阈值没触发，或角色未从测试 GT 注册")
            return
        else:
            print(f"\n✅ 环节4通过: 已注册 {len(all_chars)} 个角色")
    except Exception as e:
        print(f"❌ CharacterManager 错误: {e}")
        return
    
    # 5. 检查 SpeakerMatcher
    print("\n" + "=" * 80)
    print("环节5: SpeakerMatcher 匹配")
    print("=" * 80)
    
    try:
        from pipeline.speaker_matcher import get_speaker_matcher
        matcher = get_speaker_matcher()
        print(f"\nSpeakerMatcher 已加载")
        
        # 检查匹配逻辑是否执行
        if target.speaker:
            print(f"✅ 环节5通过: speaker 已匹配为 '{target.speaker}'")
        else:
            print(f"❌ 问题: SpeakerMatcher 执行后 speaker 仍为空")
            print("   需要进一步检查匹配日志")
    except Exception as e:
        print(f"❌ SpeakerMatcher 错误: {e}")
        return
    
    # 总结
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)
    print(f"句子类型: {target.type}")
    print(f"PER 实体: {len(per_entities)} 个")
    print(f"过滤后候选: {len(filtered)} 个")
    print(f"已注册角色: {len(all_chars)} 个")
    print(f"最终 speaker: '{target.speaker}'")


def main():
    # 使用 re_001 作为测试样本
    context_before = "苏夜站在门口，脸色铁青。"
    text = "你给我滚出去！"
    context_after = "林雪愣住了，她从没见过苏夜这样。"
    
    debug_single_sample(context_before, text, context_after)


if __name__ == '__main__':
    main()
