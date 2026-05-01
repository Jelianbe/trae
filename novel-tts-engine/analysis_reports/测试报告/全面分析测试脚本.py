# -*- coding: utf-8 -*-
"""
全面分析测试脚本
用于对Novel-TTS-Engine的各个算法模块进行系统性评估
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ['DEBUG_NER'] = '0'

from pipeline.chapter_splitter import split_with_volumes
from pipeline.dialogue_classifier import DialogueClassifier
from pipeline.sfx_detector import SfxDetector
from pipeline.nlp_basics import get_nlp, get_persons, get_locations, get_organizations
from pipeline.character_manager import CharacterManager, get_character_manager
from pipeline.speaker_matcher import SpeakerMatcher


COMPREHENSIVE_TEST_TEXT = '''卷一 风起云涌

第一章 觉醒

林轩缓缓睁开双眼，映入眼帘的是陌生的床帐。

"少爷，您终于醒了！"小翠惊喜地喊道，眼眶中泛着泪光。

林轩挣扎着坐起身，只觉得浑身酸痛。他环顾四周，这是一间古色古香的房间，窗外阳光明媚。

"小翠，我睡了多久？"林轩问道。

"少爷，您昏迷了整整三天！"小翠说道，"老爷和夫人都担心坏了！"

就在这时，门外传来急促的脚步声。

"轩儿！你终于醒了！"林天豪大步走进房间，脸上满是欣慰。

"父亲。"林轩恭敬地行礼。

林天豪摆摆手，说道："轩儿，你感觉如何？有没有哪里不舒服？"

"父亲放心，孩儿已经无碍。"林轩回答道。

"那就好，那就好。"林天豪点点头，"你好好休息，有什么需要尽管吩咐下人。"

"是，父亲。"

待林天豪离开后，林轩独自坐在窗前，心中思绪万千。

"既来之，则安之。"他喃喃自语，"这一世，我定要活出精彩！"

咚咚咚！

敲门声响起。

"少爷，老奴是王管家。"门外传来苍老的声音。

"进来吧。"

王管家推门而入，手中捧着一摞书籍。

"少爷，这是您要的书籍。"王管家恭敬地说道。

"辛苦王叔了。"林轩接过书籍。

"少爷客气了，老奴告退。"

第二章 修炼

清晨，林轩来到后院的练武场。

呼！呼！

他挥舞着拳头，汗水顺着脸颊滑落。

"看来，我需要尽快提升实力。"林轩暗自思忖。

哗啦！

一本古籍从怀中滑落，林轩弯腰拾起，只见封面上写着《天元诀》三个大字。

"少爷，您休息一下吧。"小翠端着茶水走来，"这是夫人特意为您熬的。"

"好。"林轩接过茶杯，一饮而尽。

"少爷，您真厉害！"小翠拍手道，"才几天时间，您的拳法就进步了这么多！"

"还差得远呢。"林轩摇摇头，"我听说城里有武馆，打算去报名。"

"少爷要去武馆？"小翠惊讶道，"老爷不是说要请武师来府里教您吗？"

"府里太安逸了，我需要更大的压力。"林轩说道，"而且，我也想见识一下外面的世界。"

第三章 冲突

天元城，繁华热闹。

林轩带着小翠穿行在街道上，两旁店铺林立，叫卖声此起彼伏。

"少爷，我们快回去吧！"小翠紧紧跟在林轩身后，有些紧张。

就在这时，前方传来一阵喧哗。

"让开！让开！"

一群人簇拥着一个锦衣少年走来，那少年面带傲色，目中无人。

"哟，这不是林家的废物少爷吗？"锦衣少年看到林轩，嘴角勾起一抹嘲讽，"听说你昏迷了好几天，怎么，现在又活蹦乱跳了？"

林轩认出此人正是赵家的少爷赵虎，素来与林家不和。

"赵少爷说笑了。"林轩淡淡道，"让路。"

赵虎脸色一沉，喝道："怎么？不敢说话？也是，你们林家现在就是一群丧家之犬，哪敢得罪我们赵家！"

林轩眼中闪过一丝寒芒，但没有发作。

"少爷，我们走吧。"小翠拉了拉林轩的衣袖。

卷二 崭露头角

第四章 武馆

天元武馆，门庭若市。

"请出示身份证明。"守门弟子说道。

林轩递上林家的令牌，守门弟子验明后，恭敬地让开道路。

"下一个，林轩！"

考场上，一位中年考官正襟危坐。

"请出拳。"

林轩深吸一口气，猛然挥出一拳，击打在面前的测力石上。

砰！

测力石剧烈震动，上面的指针飞速旋转。

"三百斤！"考官惊呼，"恭喜你，林轩，你被录取了！这是你的学员令牌，明天开始正式上课。"

"多谢考官。"林轩接过令牌，心中暗喜。

第五章 授课

清晨，武馆演武场。

"林轩，你来得真早！"一个魁梧的身影走来，正是林轩在测试时结识的李铁。

"李铁。"林轩拱手行礼。

"哈哈，我这不是怕落后嘛！"李铁爽朗地笑道，"听说赵虎那家伙也在这个武馆，我可不想被他比下去！"

"对了，听说今天有大师兄的授课！"李铁兴奋道，"大师兄可是淬体境九重的高手，整个武馆年轻一辈的第一人！"

"淬体境九重？"林轩眼中闪过一丝向往，"那确实值得期待。"

不久后，一位白衣青年走上高台，正是大师兄陈风。

"今天，我要讲的是武道的根基——淬体！"陈风的声音洪亮，传遍整个演武场，"淬体，就是淬炼身体，让身体变得更加强大。只有根基扎实，才能走得更远！"

"武道一途，没有捷径可走，唯有勤修苦练！"陈风环顾众人，"希望各位都能在武道上有所成就！"

"多谢大师兄指点！"林轩高声应道。

陈风看了林轩一眼，微微点头，说道："你很不错，好好努力，将来必成大器！"

第六章 进步

一个月后。

"林轩！该吃饭了！"李铁的声音从门外传来。

"来了！"林轩放下手中的书籍，走出房间。

饭桌上，李铁一边大口扒饭，一边说道："林轩，你的进步真快！才一个月，你就已经追上我了！"

"是你让着我。"林轩笑道。

"再来！"李铁举起拳头，与林轩碰了碰。

夜深人静，林轩独自站在窗前，望着满天星辰。

"明天，又是新的一天！"他轻声说道，眼中满是坚定。
'''


GROUND_TRUTH_ANNOTATION = {
    "章节划分": {
        "卷数": 2,
        "章节数": 6,
        "卷标题": ["卷一 风起云涌", "卷二 崭露头角"],
        "章节标题": [
            "第一章 觉醒", "第二章 修炼", "第三章 冲突",
            "第四章 武馆", "第五章 授课", "第六章 进步"
        ]
    },
    "对话分类": {
        "总对话数": 42,
        "明确说话人": 35,
        "隐含说话人": 7
    },
    "拟声词": {
        "总数": 8,
        "列表": ["咚咚咚", "呼", "呼", "哗啦", "砰"]
    },
    "命名实体": {
        "人物": ["林轩", "小翠", "林天豪", "王管家", "赵虎", "李铁", "陈风"],
        "地点": ["天元城", "天元武馆"],
        "组织": ["林家", "赵家"]
    },
    "说话人匹配": {
        "明确匹配": [
            # 第一章 觉醒
            ('"少爷，您终于醒了！"小翠惊喜地喊道', "小翠"),
            ('"小翠，我睡了多久？"林轩问道', "林轩"),
            ('"少爷，您昏迷了整整三天！"小翠说道', "小翠"),
            ('"轩儿！你终于醒了！"林天豪大步走进房间', "林天豪"),
            ('"父亲。"林轩恭敬地行礼', "林轩"),
            ('"轩儿，你感觉如何？有没有哪里不舒服？"林天豪说道', "林天豪"),
            ('"父亲放心，孩儿已经无碍。"林轩回答道', "林轩"),
            ('"那就好，那就好。"林天豪点点头', "林天豪"),
            ('"你好好休息，有什么需要尽管吩咐下人。"林天豪说道', "林天豪"),
            ('"是，父亲。"', "林轩"),
            ('"既来之，则安之。"他喃喃自语', "林轩"),
            ('"这一世，我定要活出精彩！"', "林轩"),
            ('"少爷，老奴是王管家。"门外传来苍老的声音', "王管家"),
            ('"进来吧。"', "林轩"),
            ('"少爷，这是您要的书籍。"王管家恭敬地说道', "王管家"),
            ('"辛苦王叔了。"', "林轩"),
            ('"少爷客气了，老奴告退。"', "王管家"),
            # 第二章 修炼
            ('"看来，我需要尽快提升实力。"林轩暗自思忖', "林轩"),
            ('"少爷，您休息一下吧。"小翠端着茶水走来', "小翠"),
            ('"这是夫人特意为您熬的。"小翠说道', "小翠"),
            ('"好。"林轩接过茶杯', "林轩"),
            ('"少爷，您真厉害！"小翠拍手道', "小翠"),
            ('"才几天时间，您的拳法就进步了这么多！"小翠说道', "小翠"),
            ('"还差得远呢。"林轩摇摇头', "林轩"),
            ('"我听说城里有武馆，打算去报名。"林轩说道', "林轩"),
            ('"少爷要去武馆？"小翠惊讶道', "小翠"),
            ('"老爷不是说要请武师来府里教您吗？"小翠问道', "小翠"),
            ('"府里太安逸了，我需要更大的压力。"林轩说道', "林轩"),
            ('"而且，我也想见识一下外面的世界。"林轩说道', "林轩"),
            # 第三章 冲突
            ('"少爷，我们快回去吧！"小翠紧紧跟在林轩身后', "小翠"),
            ('"赵少爷说笑了。"林轩淡淡道', "林轩"),
            ('"让路。"林轩淡淡道', "林轩"),
            # 第四章 武馆
            ('"多谢考官。"林轩接过令牌', "林轩"),
            # 第五章 授课
            ('"林轩，你来得真早！"一个魁梧的身影走来，正是李铁', "李铁"),
            ('"李铁。"林轩拱手行礼', "林轩"),
            ('"哈哈，我这不是怕落后嘛！"李铁爽朗地笑道', "李铁"),
            ('"听说赵虎那家伙也在这个武馆，我可不想被他比下去！"李铁说道', "李铁"),
            ('"对了，听说今天有大师兄的授课！"李铁兴奋道', "李铁"),
            ('"大师兄可是淬体境九重的高手，整个武馆年轻一辈的第一人！"李铁说道', "李铁"),
            ('"淬体境九重？"林轩眼中闪过一丝向往', "林轩"),
            ('"那确实值得期待。"林轩说道', "林轩"),
            ('"今天，我要讲的是武道的根基——淬体！"陈风的声音洪亮', "陈风"),
            ('"淬体，就是淬炼身体，让身体变得更加强大。只有根基扎实，才能走得更远！"陈风说道', "陈风"),
            ('"武道一途，没有捷径可走，唯有勤修苦练！"陈风环顾众人', "陈风"),
            ('"希望各位都能在武道上有所成就！"陈风说道', "陈风"),
            ('"多谢大师兄指点！"林轩高声应道', "林轩"),
            ('"你很不错，好好努力，将来必成大器！"陈风看了林轩一眼', "陈风"),
            # 第六章 进步
            ('"林轩！该吃饭了！"李铁的声音从门外传来', "李铁"),
            ('"来了！"林轩放下手中的书籍', "林轩"),
            ('"林轩，你的进步真快！"李铁一边大口扒饭', "李铁"),
            ('"才一个月，你就已经追上我了！"李铁说道', "李铁"),
            ('"是你让着我。"林轩笑道', "林轩"),
            ('"再来！"李铁举起拳头', "林轩"),
            ('"明天，又是新的一天！"他轻声说道', "林轩"),
        ]
    }
}


def evaluate_chapter_splitter(text: str, ground_truth: dict) -> dict:
    """评估章节划分算法"""
    structure = split_with_volumes(text)
    
    expected_volumes = ground_truth["卷数"]
    expected_chapters = ground_truth["章节数"]
    expected_vol_titles = ground_truth["卷标题"]
    expected_ch_titles = ground_truth["章节标题"]
    
    actual_volumes = structure.total_volumes
    actual_chapters = structure.total_chapters
    actual_vol_titles = [v.title for v in structure.volumes]
    actual_ch_titles = [ch.title for v in structure.volumes for ch in v.chapters]
    
    vol_match = actual_vol_titles == expected_vol_titles
    ch_match = actual_ch_titles == expected_ch_titles
    
    total_content_len = sum(len(ch.content) for vol in structure.volumes for ch in vol.chapters)
    volume_title_len = sum(len(vol.title) + 2 for vol in structure.volumes)
    chapter_title_len = sum(len(ch.title) + 2 for vol in structure.volumes for ch in vol.chapters)
    effective_text_len = len(text) - volume_title_len - chapter_title_len
    coverage = total_content_len / effective_text_len if effective_text_len > 0 else 1.0
    
    score = 0
    if actual_volumes == expected_volumes:
        score += 25
    if actual_chapters == expected_chapters:
        score += 25
    if vol_match:
        score += 25
    if ch_match:
        score += 15
    score += min(coverage * 10, 10)
    
    return {
        "卷数正确": actual_volumes == expected_volumes,
        "章节数正确": actual_chapters == expected_chapters,
        "卷标题匹配": vol_match,
        "章节标题匹配": ch_match,
        "内容覆盖率": f"{coverage*100:.2f}%",
        "得分": score,
        "详情": {
            "期望卷数": expected_volumes,
            "实际卷数": actual_volumes,
            "期望章节数": expected_chapters,
            "实际章节数": actual_chapters,
            "期望卷标题": expected_vol_titles,
            "实际卷标题": actual_vol_titles,
            "期望章节标题": expected_ch_titles,
            "实际章节标题": actual_ch_titles
        }
    }


def evaluate_dialogue_classifier(text: str, ground_truth: dict) -> dict:
    """评估对话/旁白分类算法"""
    classifier = DialogueClassifier()
    
    sentences = text.split('\n')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    results = classifier.classify_batch(sentences)
    
    dialogues = [r for r in results if r.is_dialogue]
    narrations = [r for r in results if not r.is_dialogue]
    
    expected_dialogues = ground_truth["总对话数"]
    actual_dialogues = len(dialogues)
    
    accuracy = min(actual_dialogues / expected_dialogues, 1.0) if expected_dialogues > 0 else 1.0
    
    score = int(accuracy * 100)
    
    return {
        "对话识别数": actual_dialogues,
        "期望对话数": expected_dialogues,
        "识别准确率": f"{accuracy*100:.2f}%",
        "旁白段落数": len(narrations),
        "得分": score,
        "示例对话": [d.text[:50] + "..." for d in dialogues[:5]]
    }


def evaluate_sfx_detector(text: str, ground_truth: dict) -> dict:
    """评估拟声词检测算法"""
    detector = SfxDetector()
    result = detector.detect(text)
    
    expected_sfx = set(ground_truth["列表"])
    actual_sfx = set([r.text for r in result])
    
    correct = expected_sfx & actual_sfx
    missed = expected_sfx - actual_sfx
    extra = actual_sfx - expected_sfx
    
    recall = len(correct) / len(expected_sfx) if expected_sfx else 1.0
    precision = len(correct) / len(actual_sfx) if actual_sfx else 1.0
    
    score = int((recall + precision) / 2 * 100)
    
    return {
        "正确识别": list(correct),
        "漏识别": list(missed),
        "误识别": list(extra),
        "召回率": f"{recall*100:.2f}%",
        "精确率": f"{precision*100:.2f}%",
        "得分": score
    }


def evaluate_ner(text: str, ground_truth: dict) -> dict:
    """评估命名实体识别算法"""
    nlp = get_nlp()
    result = nlp.analyze(text)
    
    expected_persons = set(ground_truth["人物"])
    expected_locations = set(ground_truth["地点"])
    expected_orgs = set(ground_truth["组织"])
    
    actual_persons = set([e.text for e in result.entities if e.type == 'PER'])
    actual_locations = set([e.text for e in result.entities if e.type == 'LOC'])
    actual_orgs = set([e.text for e in result.entities if e.type == 'ORG'])
    
    person_correct = expected_persons & actual_persons
    loc_correct = expected_locations & actual_locations
    org_correct = expected_orgs & actual_orgs
    
    person_recall = len(person_correct) / len(expected_persons) if expected_persons else 1.0
    loc_recall = len(loc_correct) / len(expected_locations) if expected_locations else 1.0
    org_recall = len(org_correct) / len(expected_orgs) if expected_orgs else 1.0
    
    person_precision = len(person_correct) / len(actual_persons) if actual_persons else 1.0
    loc_precision = len(loc_correct) / len(actual_locations) if actual_locations else 1.0
    org_precision = len(org_correct) / len(actual_orgs) if actual_orgs else 1.0
    
    person_f1 = 2 * person_recall * person_precision / (person_recall + person_precision) if (person_recall + person_precision) > 0 else 0
    loc_f1 = 2 * loc_recall * loc_precision / (loc_recall + loc_precision) if (loc_recall + loc_precision) > 0 else 0
    org_f1 = 2 * org_recall * org_precision / (org_recall + org_precision) if (org_recall + org_precision) > 0 else 0
    
    avg_f1 = (person_f1 + loc_f1 + org_f1) / 3
    
    score = int(avg_f1 * 100)
    
    return {
        "人物识别": {
            "期望": list(expected_persons),
            "实际": list(actual_persons),
            "正确": list(person_correct),
            "漏识别": list(expected_persons - actual_persons),
            "误识别": list(actual_persons - expected_persons),
            "召回率": f"{person_recall*100:.2f}%",
            "精确率": f"{person_precision*100:.2f}%",
            "F1分数": f"{person_f1*100:.2f}%"
        },
        "地点识别": {
            "期望": list(expected_locations),
            "实际": list(actual_locations),
            "正确": list(loc_correct),
            "召回率": f"{loc_recall*100:.2f}%",
            "精确率": f"{loc_precision*100:.2f}%",
            "F1分数": f"{loc_f1*100:.2f}%"
        },
        "组织识别": {
            "期望": list(expected_orgs),
            "实际": list(actual_orgs),
            "正确": list(org_correct),
            "召回率": f"{org_recall*100:.2f}%",
            "精确率": f"{org_precision*100:.2f}%",
            "F1分数": f"{org_f1*100:.2f}%"
        },
        "平均F1分数": f"{avg_f1*100:.2f}%",
        "得分": score
    }


def evaluate_speaker_matcher(ground_truth: dict) -> dict:
    """评估说话人匹配算法"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        char_manager = CharacterManager(db_path)
        
        characters = [
            ("林轩", "male", {"轩儿", "林少爷", "少爷"}),
            ("小翠", "female", {"翠儿"}),
            ("林天豪", "male", {"老爷", "父亲"}),
            ("王管家", "male", {"王叔"}),
            ("赵虎", "male", {"赵少爷"}),
            ("李铁", "male", set()),
            ("陈风", "male", {"大师兄"}),
        ]
        
        for name, gender, aliases in characters:
            char_manager.add_character(name, gender=gender, aliases=aliases)
        
        matcher = SpeakerMatcher(char_manager)
        
        expected_matches = ground_truth["明确匹配"]
        
        correct = 0
        total = len(expected_matches)
        errors = []
        
        prev_speaker = None
        
        for dialogue, expected_speaker in expected_matches:
            char, matched_name = matcher.get_speaker_for_sentence(
                dialogue, 
                prev_speaker=prev_speaker
            )
            
            if matched_name == expected_speaker:
                correct += 1
                prev_speaker = matched_name
            else:
                errors.append({
                    "对话": dialogue[:30] + "...",
                    "期望": expected_speaker,
                    "实际": matched_name
                })
                if expected_speaker:
                    prev_speaker = expected_speaker
        
        accuracy = correct / total if total > 0 else 0
        score = int(accuracy * 100)
        
        return {
            "总对话数": total,
            "正确匹配": correct,
            "准确率": f"{accuracy*100:.2f}%",
            "得分": score,
            "错误详情": errors[:10]
        }
    
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except:
                pass


def generate_report(results: dict, output_path: str):
    """生成分析报告"""
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("Novel-TTS-Engine 算法评估分析报告")
    report_lines.append("=" * 70)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    total_score = 0
    module_count = 0
    
    for module_name, result in results.items():
        report_lines.append("-" * 70)
        report_lines.append(f"【{module_name}】")
        report_lines.append("-" * 70)
        
        score = result.get("得分", 0)
        total_score += score
        module_count += 1
        
        if score >= 90:
            grade = "A+ 优秀"
        elif score >= 80:
            grade = "A 良好"
        elif score >= 70:
            grade = "B 合格"
        else:
            grade = "C 待改进"
        
        report_lines.append(f"得分: {score}/100")
        report_lines.append(f"等级: {grade}")
        report_lines.append("")
        
        for key, value in result.items():
            if key == "得分":
                continue
            if key == "详情" or key == "错误详情":
                report_lines.append(f"  {key}:")
                if isinstance(value, list):
                    for item in value[:5]:
                        report_lines.append(f"    - {item}")
                    if len(value) > 5:
                        report_lines.append(f"    ... 共 {len(value)} 项")
                else:
                    for k, v in value.items():
                        report_lines.append(f"    {k}: {v}")
            elif isinstance(value, list):
                report_lines.append(f"{key}: {value[:5]}{'...' if len(value) > 5 else ''}")
            else:
                report_lines.append(f"{key}: {value}")
        report_lines.append("")
    
    avg_score = total_score / module_count if module_count > 0 else 0
    
    report_lines.append("=" * 70)
    report_lines.append("【综合评估】")
    report_lines.append("=" * 70)
    report_lines.append(f"平均得分: {avg_score:.1f}/100")
    
    if avg_score >= 90:
        overall_grade = "A+ 优秀"
    elif avg_score >= 80:
        overall_grade = "A 良好"
    elif avg_score >= 70:
        overall_grade = "B 合格"
    else:
        overall_grade = "C 待改进"
    
    report_lines.append(f"综合等级: {overall_grade}")
    report_lines.append("")
    report_lines.append("【改进建议】")
    report_lines.append("")
    
    for module_name, result in results.items():
        score = result.get("得分", 0)
        if score < 80:
            report_lines.append(f"- {module_name}: 得分{score}分，需要优化")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("报告结束")
    report_lines.append("=" * 70)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    return avg_score, overall_grade


def main():
    print("=" * 70)
    print("Novel-TTS-Engine 全面分析测试")
    print("=" * 70)
    print()
    
    base_report_dir = Path(__file__).parent.parent / "analysis_reports"
    base_report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_type = "全面分析测试"
    
    report_subdir = base_report_dir / f"{report_type}_{timestamp}"
    report_subdir.mkdir(exist_ok=True)
    
    print("1. 评估章节划分算法...")
    chapter_result = evaluate_chapter_splitter(COMPREHENSIVE_TEST_TEXT, GROUND_TRUTH_ANNOTATION["章节划分"])
    print(f"   得分: {chapter_result['得分']}/100")
    
    print("2. 评估对话/旁白分类算法...")
    dialogue_result = evaluate_dialogue_classifier(COMPREHENSIVE_TEST_TEXT, GROUND_TRUTH_ANNOTATION["对话分类"])
    print(f"   得分: {dialogue_result['得分']}/100")
    
    print("3. 评估拟声词检测算法...")
    sfx_result = evaluate_sfx_detector(COMPREHENSIVE_TEST_TEXT, GROUND_TRUTH_ANNOTATION["拟声词"])
    print(f"   得分: {sfx_result['得分']}/100")
    
    print("4. 评估命名实体识别算法...")
    ner_result = evaluate_ner(COMPREHENSIVE_TEST_TEXT, GROUND_TRUTH_ANNOTATION["命名实体"])
    print(f"   得分: {ner_result['得分']}/100")
    
    print("5. 评估说话人匹配算法...")
    speaker_result = evaluate_speaker_matcher(GROUND_TRUTH_ANNOTATION["说话人匹配"])
    print(f"   得分: {speaker_result['得分']}/100")
    
    results = {
        "章节划分": chapter_result,
        "对话/旁白分类": dialogue_result,
        "拟声词检测": sfx_result,
        "命名实体识别": ner_result,
        "说话人匹配": speaker_result
    }
    
    report_path = report_subdir / f"算法评估分析报告_{timestamp}.txt"
    avg_score, overall_grade = generate_report(results, str(report_path))
    
    print()
    print("=" * 70)
    print("评估完成")
    print("=" * 70)
    print(f"平均得分: {avg_score:.1f}/100")
    print(f"综合等级: {overall_grade}")
    print(f"报告已保存至: {report_path}")
    
    json_path = report_subdir / f"详细数据_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"详细数据已保存至: {json_path}")
    
    return results


if __name__ == "__main__":
    main()
