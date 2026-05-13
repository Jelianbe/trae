"""诊断P1/P3/P9/P12等失败案例"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker
import tempfile, uuid

# P1: 掌柜
P1 = "林轩推开客栈的门，对着掌柜说道：\"来一间上房。\"掌柜抬头看了看他，笑道：\"客官来得巧，正好还剩一间。\""

# P12: 白发老者
P12 = "一个白发老者缓缓走来。他捋了捋胡须说道：\"年轻人，你与我有缘。\"苏夜愣住了。"

# P4: 黑衣人
P4 = "黑衣人抽出长剑。\"把东西交出来。\"月光照亮了剑刃。苏夜冷笑一声：\"做梦。\""

# P9: 林轩
P9 = "林轩问道：\"你去参加拍卖会吗？\"小翠摇头：\"不去，我还要准备晚宴。\"他又劝道：\"机会难得，一起去吧。\""

def diagnose(paragraph_text, precreate_chars=None):
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    cm = CharacterManager(db_path=db_path)
    project_id = f'test_{uuid.uuid4().hex[:8]}'
    
    if precreate_chars:
        for name, gender in precreate_chars:
            cm.add_character(name=name, project_id=project_id, aliases=set(), gender=gender)
    
    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id
    
    print(f"\n{'='*60}")
    print(f"段落: {paragraph_text[:80]}...")
    print(f"{'='*60}")
    
    results = sm.analyze_dialogue(paragraph_text, chapter_id=1)
    
    for i, (dialogue_text, speaker_char) in enumerate(results):
        actual = speaker_char.name if speaker_char else '未知'
        print(f"  对话{i+1}: [{dialogue_text}] -> {actual}")
        
        # 打印匹配过程
        prefix_start = 0 if i == 0 else results[i-1][1]
        prefix = paragraph_text[prefix_start:paragraph_text.find(dialogue_text)].strip()
        suffix = paragraph_text[paragraph_text.find(dialogue_text)+len(dialogue_text):].strip()
        
        print(f"    prefix: {prefix[:50]}")
        print(f"    suffix: {suffix[:50]}")
        
        # 尝试匹配上下文
        context_before = prefix
        context_after = suffix
        
        # 提取身份词
        identity_words = sm._extract_identity_words(context_before)
        if identity_words:
            print(f"    身份词(前): {identity_words}")
        identity_words = sm._extract_identity_words(context_after)
        if identity_words:
            print(f"    身份词(后): {identity_words}")
        
        # 角色库匹配
        narration = sm._extract_narration(context_before + " " + context_after)
        char_match = sm._match_from_character_library(narration)
        if char_match:
            print(f"    角色库匹配: {char_match.name}")
        
        # NER
        ner_results = sm._extract_from_ner(narration)
        if ner_results:
            print(f"    NER: {ner_results}")

def main():
    print("=== 模式A: 无预创建角色 ===")
    for p_name, p_text in [("P1", P1), ("P12", P12), ("P4", P4), ("P9", P9)]:
        diagnose(p_text)
    
    print("\n\n=== 模式B: 预创建18角色 ===")
    precreate_chars = [
        ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
        ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
        ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
        ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
        ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
        ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
    ]
    for p_name, p_text in [("P1", P1), ("P12", P12), ("P4", P4), ("P9", P9)]:
        diagnose(p_text, precreate_chars)

if __name__ == '__main__':
    main()
