"""Rewrite test_data_v6.py with ASCII double quotes"""
import sys
sys.path.insert(0, 'D:/trae/novel-tts-engine')

# Generate the test data file with ASCII quotes by using json module
data = [
  {"id": 1, "paragraph": '林轩推开客栈的门，对着掌柜说道："来一间上房。"掌柜抬头看了看他，笑道："客官来得巧，正好还剩一间。"', "dialogues": [{"text": "来一间上房。", "speaker": "林轩"}, {"text": "客官来得巧，正好还剩一间。", "speaker": "掌柜"}]},
  {"id": 2, "paragraph": '小翠端着茶走进书房，轻声道："小姐，该用茶了。"纳兰嫣然放下书卷，头也不抬地问："放到桌上吧，老爷回来了吗？"', "dialogues": [{"text": "小姐，该用茶了。", "speaker": "小翠"}, {"text": "放到桌上吧，老爷回来了吗？", "speaker": "纳兰嫣然"}]},
  {"id": 3, "paragraph": '苏夜站在山崖边，望着远处的云海说道："十年了，我终于回来了。"身后传来脚步声，一个熟悉的声音响起："师弟，别来无恙。"', "dialogues": [{"text": "十年了，我终于回来了。", "speaker": "苏夜"}, {"text": "师弟，别来无恙。", "speaker": "林雪"}]},
  {"id": 4, "paragraph": '黑衣人抽出长剑。"把东西交出来。"月光照亮了剑刃。苏夜冷笑一声："做梦。"', "dialogues": [{"text": "把东西交出来。", "speaker": "黑衣人"}, {"text": "做梦。", "speaker": "苏夜"}]},
  {"id": 5, "paragraph": '林雪推门而入。"林轩，你又在偷懒！"她叉着腰怒视着躺在床上的少年。林轩懒洋洋地翻了个身："姐，让我再睡会儿。"', "dialogues": [{"text": "林轩，你又在偷懒！", "speaker": "林雪"}, {"text": "姐，让我再睡会儿。", "speaker": "林轩"}]},
  {"id": 6, "paragraph": '赵天行走进训练场。他沉声说道："今天开始，由我负责你们的考核。"众学员立刻安静下来。', "dialogues": [{"text": "今天开始，由我负责你们的考核。", "speaker": "赵天行"}]},
  {"id": 7, "paragraph": '药老从戒指中飘出。他看了一眼萧炎，缓缓道："这枚丹药，你先服下。"萧炎接过来，毫不犹豫地吞了下去。', "dialogues": [{"text": "这枚丹药，你先服下。", "speaker": "药老"}]},
  {"id": 8, "paragraph": '小翠笑了笑。她轻声说："知道了，小姐。"然后转身离开房间。纳兰嫣然望着她的背影，叹了口气。', "dialogues": [{"text": "知道了，小姐。", "speaker": "小翠"}]},
  {"id": 9, "paragraph": '林轩问道："你去参加拍卖会吗？"小翠摇头："不去，我还要准备晚宴。"他又劝道："机会难得，一起去吧。"', "dialogues": [{"text": "你去参加拍卖会吗？", "speaker": "林轩"}, {"text": "不去，我还要准备晚宴。", "speaker": "小翠"}, {"text": "机会难得，一起去吧。", "speaker": "林轩"}]},
  {"id": 10, "paragraph": '萧炎看向药老："这枚丹药值多少？"药老捋了捋胡须："至少三万金币。"萧炎皱眉："太贵了。"', "dialogues": [{"text": "这枚丹药值多少？", "speaker": "萧炎"}, {"text": "至少三万金币。", "speaker": "药老"}, {"text": "太贵了。", "speaker": "萧炎"}]},
  {"id": 11, "paragraph": '苏夜举起酒杯："敬我们的友谊。"林雪碰了碰杯："敬未来。"赵天行一饮而尽："好酒！"', "dialogues": [{"text": "敬我们的友谊。", "speaker": "苏夜"}, {"text": "敬未来。", "speaker": "林雪"}, {"text": "好酒！", "speaker": "赵天行"}]},
  {"id": 12, "paragraph": '一个白发老者缓缓走来。他捋了捋胡须说道："年轻人，你与我有缘。"苏夜愣住了。', "dialogues": [{"text": "年轻人，你与我有缘。", "speaker": "白发老者"}]},
  {"id": 13, "paragraph": '黑暗中，一个高大的身影浮现。他低沉地说道："交出那块玉石，饶你不死。"林轩握紧拳头："休想。"', "dialogues": [{"text": "交出那块玉石，饶你不死。", "speaker": "黑衣人"}, {"text": "休想。", "speaker": "林轩"}]},
  {"id": 14, "paragraph": '一位身穿黑袍的骑士走进殿堂。他单膝跪地："陛下，前线战报。"博士抬头："念。"', "dialogues": [{"text": "陛下，前线战报。", "speaker": "骑士"}, {"text": "念。", "speaker": "博士"}]},
  {"id": 15, "paragraph": '林雪拍了一下桌子。"这丹药如何？"药老看向萧炎。萧炎点头道："很好，我买了。"', "dialogues": [{"text": "这丹药如何？", "speaker": "林雪"}, {"text": "很好，我买了。", "speaker": "萧炎"}]},
  {"id": 16, "paragraph": '纳兰嫣然推门而入。她冷冷说道："你来了。"林轩站起身："嫣然姐，好久不见。"', "dialogues": [{"text": "你来了。", "speaker": "纳兰嫣然"}, {"text": "嫣然姐，好久不见。", "speaker": "林轩"}]},
  {"id": 17, "paragraph": '苏夜走到窗前。他望着夜色自言自语道："什么时候才能结束这一切？"身后传来轻柔的声音："很快了，相信我。"', "dialogues": [{"text": "什么时候才能结束这一切？", "speaker": "苏夜"}, {"text": "很快了，相信我。", "speaker": "伊莉雅"}]},
  {"id": 18, "paragraph": '"萧炎，你太弱了！"药老摇头道。萧炎低下头："师傅，我会努力的。"药老叹了口气。', "dialogues": [{"text": "萧炎，你太弱了！", "speaker": "药老"}, {"text": "师傅，我会努力的。", "speaker": "萧炎"}]},
  {"id": 19, "paragraph": '"纳兰嫣然，你变强了。"林轩认真地说。纳兰嫣然笑道："多谢夸奖，你也不差。"', "dialogues": [{"text": "纳兰嫣然，你变强了。", "speaker": "林轩"}, {"text": "多谢夸奖，你也不差。", "speaker": "纳兰嫣然"}]},
  {"id": 20, "paragraph": '"冲啊！"众人齐声喊道。他们如潮水般涌向城门。骑士们举起长矛，高呼："为了荣耀！"', "dialogues": [{"text": "冲啊！", "speaker": "GROUP:CROWD"}, {"text": "为了荣耀！", "speaker": "骑士们"}]},
  {"id": 21, "paragraph": '"杀了他们！"联盟成员怒吼着冲上前。博士冷笑："不自量力。"', "dialogues": [{"text": "杀了他们！", "speaker": "联盟成员"}, {"text": "不自量力。", "speaker": "博士"}]},
  {"id": 22, "paragraph": '"魔法准备好了。"艾德温举起法杖。伊莉雅点点头："开始吧，加尔文在等我们。"', "dialogues": [{"text": "魔法准备好了。", "speaker": "艾德温"}, {"text": "开始吧，加尔文在等我们。", "speaker": "伊莉雅"}]},
  {"id": 23, "paragraph": '"加尔文，你背叛了我们！"艾德温怒吼。加尔文平静地回答："不，我只是选择了正确的道路。"', "dialogues": [{"text": "加尔文，你背叛了我们！", "speaker": "艾德温"}, {"text": "不，我只是选择了正确的道路。", "speaker": "加尔文"}]},
  {"id": 24, "paragraph": '"伊莉雅，别冲动。"骑士拉住她的手。伊莉雅甩开他："我要亲手杀了他。"', "dialogues": [{"text": "伊莉雅，别冲动。", "speaker": "骑士"}, {"text": "我要亲手杀了他。", "speaker": "伊莉雅"}]},
  {"id": 25, "paragraph": '"博士，实验结果如何？"林轩急切地问道。博士推了推眼镜："成功了，这是样本。"他递出一个试管。', "dialogues": [{"text": "博士，实验结果如何？", "speaker": "林轩"}, {"text": "成功了，这是样本。", "speaker": "博士"}]},
  {"id": 26, "paragraph": '"林轩，你去哪？"小翠喊住他。林轩头也不回："找药老。"她急忙追上去："等等我！"', "dialogues": [{"text": "林轩，你去哪？", "speaker": "小翠"}, {"text": "找药老。", "speaker": "林轩"}, {"text": "等等我！", "speaker": "小翠"}]},
  {"id": 27, "paragraph": '"萧炎，别去送死！"药老抓住他的肩膀。萧炎挣脱开："我必须去。"他转身跳下悬崖。', "dialogues": [{"text": "萧炎，别去送死！", "speaker": "药老"}, {"text": "我必须去。", "speaker": "萧炎"}]},
  {"id": 28, "paragraph": '"你输了。"苏夜收起剑。黑衣人跪在地上："不可能……"苏夜冷冷地说："事实如此。"', "dialogues": [{"text": "你输了。", "speaker": "苏夜"}, {"text": "不可能……", "speaker": "黑衣人"}, {"text": "事实如此。", "speaker": "苏夜"}]},
  {"id": 29, "paragraph": '"林雪在吗？"赵天行敲了敲门。门开了，一个清脆的声音回答："她出去了，我是小翠。"', "dialogues": [{"text": "林雪在吗？", "speaker": "赵天行"}, {"text": "她出去了，我是小翠。", "speaker": "小翠"}]},
  {"id": 30, "paragraph": '"全体注意，向右转！"骑士队长高声下令。众人齐刷刷地转身。博士满意地点头："很好。"', "dialogues": [{"text": "全体注意，向右转！", "speaker": "骑士队长"}, {"text": "很好。", "speaker": "博士"}]},
  {"id": 31, "paragraph": '"救命！"一个女声尖叫。苏夜冲进小巷，看到黑衣人正持刀威胁。"放开她。"他冷声道。', "dialogues": [{"text": "救命！", "speaker": "伊莉雅"}, {"text": "放开她。", "speaker": "苏夜"}]},
  {"id": 32, "paragraph": '"艾德温，你太冲动了。"加尔文叹了口气。艾德温反驳道："冲动？他杀了我全家！"', "dialogues": [{"text": "艾德温，你太冲动了。", "speaker": "加尔文"}, {"text": "冲动？他杀了我全家！", "speaker": "艾德温"}]},
  {"id": 33, "paragraph": '"这瓶药水，喝了能解毒。"白发老者递过瓶子。林轩犹豫了一下："我凭什么相信你？"老者笑了笑："信不信由你。"', "dialogues": [{"text": "这瓶药水，喝了能解毒。", "speaker": "白发老者"}, {"text": "我凭什么相信你？", "speaker": "林轩"}, {"text": "信不信由你。", "speaker": "白发老者"}]},
  {"id": 34, "paragraph": '"骑士们，冲锋！"首领挥剑指向敌方。众人齐声呐喊："杀！"博士站在高处，冷冷地看着这一切。', "dialogues": [{"text": "骑士们，冲锋！", "speaker": "首领"}, {"text": "杀！", "speaker": "骑士们"}]},
  {"id": 35, "paragraph": '"赵天行，你居然作弊！"林雪愤怒地指着他。赵天行摊手："证据呢？"她咬牙道："我会找到的。"', "dialogues": [{"text": "赵天行，你居然作弊！", "speaker": "林雪"}, {"text": "证据呢？", "speaker": "赵天行"}, {"text": "我会找到的。", "speaker": "林雪"}]},
]

# Write Python file with ASCII quotes using single-quote delimited strings
import json
with open('analysis_reports/test_data_v6.py', 'w', encoding='utf-8') as f:
    f.write('"""Hardcoded test data"""\n')
    f.write('TEST_PARAGRAPHS = ')
    f.write(json.dumps(data, ensure_ascii=False, indent=2))
    f.write('\n')

# Verify
from pipeline.speaker_hint_matcher import DIALOGUE_PATTERNS as DP
total = 0
for item in data:
    total += sum(1 for pat in DP for _ in pat.finditer(item['paragraph']))
print(f"Verified: {total}/{sum(len(d['dialogues']) for d in data)} dialogues match")
