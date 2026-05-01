import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
import os
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher

GROUND_TRUTH = [
    ("少爷，您终于醒了！", "小翠"),
    ("小翠，我睡了多久？", "林轩"),
    ("少爷，您昏迷了整整三天！", "小翠"),
    ("老爷和夫人都担心坏了！", "小翠"),
    ("轩儿！你终于醒了！", "林天豪"),
    ("父亲。", "林轩"),
    ("轩儿，你感觉如何？有没有哪里不舒服？", "林天豪"),
    ("父亲放心，孩儿已经无碍。", "林轩"),
    ("那就好，那就好。", "林天豪"),
    ("你好好休息，有什么需要尽管吩咐下人。", "林天豪"),
    ("是，父亲。", "林轩"),
    ("既来之，则安之。", "林轩"),
    ("这一世，我定要活出精彩！", "林轩"),
    ("少爷，老奴是王管家。", "王管家"),
    ("进来吧。", "林轩"),
    ("少爷，这是您要的书籍。", "王管家"),
    ("辛苦王叔了。", "林轩"),
    ("少爷客气了，老奴告退。", "王管家"),
    ("看来，我需要尽快提升实力。", "林轩"),
    ("少爷，您休息一下吧。", "小翠"),
    ("这是夫人特意为您熬的。", "小翠"),
    ("好。", "林轩"),
    ("少爷，您真厉害！", "小翠"),
    ("才几天时间，您的拳法就进步了这么多！", "小翠"),
    ("还差得远呢。", "林轩"),
    ("我听说城里有武馆，打算去报名。", "林轩"),
    ("少爷要去武馆？", "小翠"),
    ("老爷不是说要请武师来府里教您吗？", "小翠"),
    ("府里太安逸了，我需要更大的压力。", "林轩"),
    ("而且，我也想见识一下外面的世界。", "林轩"),
    ("少爷，我们快回去吧！", "小翠"),
    ("这一世，我一定要站在这个世界的巅峰！", "林轩"),
    ("让开！让开！", None),
    ("哟，这不是林家的废物少爷吗？", "赵虎"),
    ("听说你昏迷了好几天，怎么，现在又活蹦乱跳了？", "赵虎"),
    ("怎么？不敢说话？", "赵虎"),
    ("也是，你们林家现在就是一群丧家之犬，哪敢得罪我们赵家！", "赵虎"),
    ("赵少爷说笑了。", "林轩"),
    ("让路。", "林轩"),
    ("请出示身份证明。", None),
    ("下一个，林轩！", None),
    ("请出拳。", None),
    ("三百斤！", None),
    ("恭喜你，林轩，你被录取了！", None),
    ("这是你的学员令牌，明天开始正式上课。", None),
    ("多谢考官。", "林轩"),
    ("林轩，你来得真早！", "李铁"),
    ("李铁。", "林轩"),
    ("你怎么也这么早？", "林轩"),
    ("哈哈，我这不是怕落后嘛！", "李铁"),
    ("听说赵虎那家伙也在这个武馆，我可不想被他比下去！", "李铁"),
    ("对了，听说今天有大师兄的授课！", "李铁"),
    ("大师兄可是淬体境九重的高手，整个武馆年轻一辈的第一人！", "李铁"),
    ("淬体境九重？", "林轩"),
    ("那确实值得期待。", "林轩"),
    ("今天，我要讲的是武道的根基——淬体！", "陈风"),
    ("淬体，就是淬炼身体，让身体变得更加强大。只有根基扎实，才能走得更远！", "陈风"),
    ("武道一途，没有捷径可走，唯有勤修苦练！", "陈风"),
    ("希望各位都能在武道上有所成就！", "陈风"),
    ("多谢大师兄指点！", "林轩"),
    ("你很不错，好好努力，将来必成大器！", "陈风"),
    ("林轩！该吃饭了！", "李铁"),
    ("来了！", "林轩"),
    ("林轩，你的进步真快！", "李铁"),
    ("才一个月，你就已经追上我了！", "李铁"),
    ("是你让着我。", "林轩"),
    ("再来！", "林轩"),
    ("明天，又是新的一天！", "林轩"),
]

CHARACTER_INFO = [
    ("林轩", "male", {"轩儿", "林少爷", "少爷"}),
    ("小翠", "female", {"翠儿"}),
    ("林天豪", "male", {"老爷", "父亲"}),
    ("王管家", "male", {"王叔"}),
    ("赵虎", "male", {"赵少爷"}),
    ("李铁", "male", set()),
    ("陈风", "male", {"大师兄"}),
]


def test_speaker_matching():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        char_manager = CharacterManager(db_path)
        
        for name, gender, aliases in CHARACTER_INFO:
            char_manager.add_character(name, gender=gender, aliases=aliases)
        
        matcher = SpeakerMatcher(char_manager)
        
        correct = 0
        total = 0
        results = []
        
        prev_speaker = None
        
        for dialogue, expected_speaker in GROUND_TRUTH:
            total += 1
            
            if expected_speaker is None:
                correct += 1
                results.append(("SKIP", dialogue[:20], expected_speaker, None))
                continue
            
            char, matched_name = matcher.get_speaker_for_sentence(
                dialogue, 
                prev_speaker=prev_speaker
            )
            
            if matched_name == expected_speaker:
                correct += 1
                results.append(("OK", dialogue[:20], expected_speaker, matched_name))
                prev_speaker = matched_name
            else:
                results.append(("FAIL", dialogue[:20], expected_speaker, matched_name))
                if matched_name:
                    prev_speaker = matched_name
        
        accuracy = correct / total * 100
        
        print("=" * 70)
        print("说话人匹配准确率测试报告")
        print("=" * 70)
        print()
        print(f"总对话数: {total}")
        print(f"正确匹配: {correct}")
        print(f"准确率: {accuracy:.1f}%")
        print()
        
        print("=" * 70)
        print("匹配详情")
        print("=" * 70)
        print()
        
        print("【正确匹配】")
        for status, dialogue, expected, matched in results:
            if status == "OK" and expected is not None:
                print(f"  {status} '{dialogue}...' -> {matched}")
        print()
        
        print("【错误匹配】")
        errors = [r for r in results if r[0] == "FAIL"]
        if errors:
            for status, dialogue, expected, matched in errors:
                print(f"  {status} '{dialogue}...' expected: {expected}, got: {matched}")
        else:
            print("  No errors")
        print()
        
        print("【跳过（无说话人）】")
        skipped = [r for r in results if r[2] is None]
        for status, dialogue, expected, matched in skipped:
            print(f"  {status} '{dialogue}...'")
        print()
        
        print("=" * 70)
        print("评分结果")
        print("=" * 70)
        
        if accuracy >= 95:
            grade = "A+ Excellent"
            status = "PASS"
        elif accuracy >= 85:
            grade = "A Good"
            status = "PASS"
        elif accuracy >= 70:
            grade = "B Acceptable"
            status = "PASS"
        else:
            grade = "C Needs Improvement"
            status = "FAIL"
        
        print(f"准确率: {accuracy:.1f}%")
        print(f"等级: {grade}")
        print(f"状态: {status}")
        print()
        
        return accuracy
        
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except:
                pass


if __name__ == "__main__":
    test_speaker_matching()
