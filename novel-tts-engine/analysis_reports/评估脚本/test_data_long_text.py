"""长文本测试集 (全文 Ground Truth)

用途: 完整小说级别的端到端测试
注意: 运行耗时较长，建议单独执行

字段说明:
  id: 测试集标识
  style: 文体风格
  novel_name: 小说文件名
  has_gt: 是否有对话级GT标注
  ground_truth: 完整 GT JSON 内容（如有）
  annotation_content: 人工标注文档内容（如有）
"""

LONG_TEXT_TEST_SETS = [
  {
    "id": "LONG-novel_xiuxian",
    "style": "修仙",
    "novel_name": "test_novel.txt",
    "has_gt": True,
    "dialogue_count": 55,
    "total_sentences": 117,
    "ground_truth": {
      "novel": "test_novel",
      "style": "修仙",
      "dialogue_speakers": [{"text": "“少爷，您终于醒了！”", "speaker": "小翠"}, {"text": "“小翠，我睡了多久？”", "speaker": "林轩"}, {"text": "“少爷，您昏迷了整整三天！”", "speaker": "小翠"}, {"text": "“轩儿！你终于醒了！”", "speaker": "林天豪"}, {"text": "“父亲。”", "speaker": "林轩"}, {"text": "“轩儿，你感觉如何？”", "speaker": "林天豪"}, {"text": "“父亲放心，孩儿已经无碍。”", "speaker": "林轩"}, {"text": "“那就好，那就好。”", "speaker": "林天豪"}, {"text": "“是，父亲。”", "speaker": "林轩"}, {"text": "“既来之，则安之。”", "speaker": "林轩"}, {"text": "“少爷，老奴是王管家。”", "speaker": "王管家"}, {"text": "“进来吧。”", "speaker": "林轩"}, {"text": "“少爷，这是您要的书籍。”", "speaker": "王管家"}, {"text": "“辛苦王叔了。”", "speaker": "林轩"}, {"text": "“少爷客气了，老奴告退。”", "speaker": "王管家"}, {"text": "“看来，我需要尽快提升实力。”", "speaker": "林轩"}, {"text": "“少爷，您休息一下吧。”", "speaker": "小翠"}, {"text": "“好。”", "speaker": "林轩"}, {"text": "“少爷，您真厉害！”", "speaker": "小翠"}, {"text": "“还差得远呢。”", "speaker": "林轩"}, {"text": "“少爷要去武馆？”", "speaker": "小翠"}, {"text": "“府里太安逸了，我需要更大的压力。”", "speaker": "林轩"}, {"text": "“要下雨了。”", "speaker": "林轩"}, {"text": "“少爷，我们快回去吧！”", "speaker": "小翠"}, {"text": "“这一世，我一定要站在这个世界的巅峰！”", "speaker": "林轩"}, {"text": "“让开！让开！”", "speaker": "赵虎"}, {"text": "“那是赵家的少爷赵虎。”", "speaker": "路人"}, {"text": "“淬体境三重？这么厉害！”", "speaker": "路人"}, {"text": "“可不是嘛，赵家可是我们天元城的三大家族之一！”", "speaker": "路人"}, {"text": "“哟，这不是林家的废物少爷吗？”", "speaker": "赵虎"}, {"text": "“赵少爷说笑了。让路。”", "speaker": "林轩"}, {"text": "“怎么？不敢说话？”", "speaker": "赵虎"}, {"text": "“这林家少爷，胆子不小啊！”", "speaker": "路人"}, {"text": "“是啊，敢这么跟赵虎说话！”", "speaker": "路人"}, {"text": "“请出示身份证明。”", "speaker": "考官"}, {"text": "“听说这次考核很严格，要通过三关才能成为正式学员！”", "speaker": "路人"}, {"text": "“下一个，林轩！”", "speaker": "考官"}, {"text": "“请出拳。”", "speaker": "考官"}, {"text": "“三百斤！”", "speaker": "考官"}, {"text": "“恭喜你，林轩，你被录取了！”", "speaker": "考官"}, {"text": "“多谢考官。”", "speaker": "林轩"}, {"text": "“林轩，你来得真早！”", "speaker": "李铁"}, {"text": "“李铁。你怎么也这么早？”", "speaker": "林轩"}, {"text": "“哈哈，我这不是怕落后嘛！”", "speaker": "李铁"}, {"text": "“对了，听说今天有大师兄的授课！”", "speaker": "李铁"}, {"text": "“淬体境九重？”", "speaker": "林轩"}, {"text": "“今天，我要讲的是武道的根基——淬体！”", "speaker": "陈风"}, {"text": "“武道一途，没有捷径可走，唯有勤修苦练！”", "speaker": "陈风"}, {"text": "“你很不错，好好努力，将来必成大器！”", "speaker": "陈风"}, {"text": "“多谢大师兄指点！”", "speaker": "林轩"}, {"text": "“林轩！该吃饭了！”", "speaker": "李铁"}, {"text": "“来了！”", "speaker": "林轩"}, {"text": "“林轩，你的进步真快！”", "speaker": "李铁"}, {"text": "“是你让着我。再来！”", "speaker": "林轩"}, {"text": "“明天，又是新的一天！”", "speaker": "林轩"}],
      "entities": {"persons": ["林轩", "小翠", "林天豪", "王管家", "赵虎", "李铁", "陈风"], "speaking_persons": ["林轩", "小翠", "林天豪", "王管家", "赵虎", "李铁", "陈风"], "organizations": [], "locations": ["天元城", "林府", "天元武馆"], "aliases": {"林轩": ["轩儿", "少爷", "林家少爷"], "林天豪": ["老爷", "父亲"], "王管家": ["王叔", "老奴"], "陈风": ["大师兄"]}},
      "dialogue_sentences_sample": [{'text': '卷一 风起云涌', 'is_dialogue': False, 'speaker': None}, {'text': '第一章 少年初醒', 'is_dialogue': False, 'speaker': None}, {'text': '清晨的阳光透过破旧的窗棂洒落进来，照在少年的脸上。', 'is_dialogue': False, 'speaker': None}, {'text': '林轩缓缓睁开双眼，眼中闪过一丝迷茫。他心想，这里是什么地方？记忆如潮水般涌来，原主的记忆逐渐与他的意识融合。', 'is_dialogue': False, 'speaker': None}, {'text': '"少爷，您终于醒了！"一个清脆的声音传来。', 'is_dialogue': True, 'speaker': '小翠'}, {'text': '林轩转头看去，只见一个十四五岁的小丫鬟正站在床边，眼中满是欣喜。她叫小翠，是林府的贴身丫鬟。', 'is_dialogue': False, 'speaker': None}, {'text': '"小翠，我睡了多久？"林轩轻声问道。', 'is_dialogue': True, 'speaker': '林轩'}, {'text': '"少爷，您昏迷了整整三天！"小翠激动地说道，"老爷和夫人都担心坏了！"', 'is_dialogue': True, 'speaker': '小翠'}, {'text': '林轩缓缓坐起身，感觉浑身酸痛。他暗道，这具身体太弱了，需要好好调养。', 'is_dialogue': False, 'speaker': None}, {'text': '这时，门外传来一阵急促的脚步声。', 'is_dialogue': False, 'speaker': None}],
      "dialogue_sentences_count": 117,
    },
    "annotation_content": None,
  },
  {
    "id": "LONG-novel_urban",
    "style": "都市异能",
    "novel_name": "test_novel_urban.txt",
    "has_gt": True,
    "dialogue_count": 23,
    "total_sentences": 144,
    "ground_truth": {
      "novel": "test_novel_urban",
      "style": "都市异能",
      "dialogue_speakers": [{"text": "“苏夜，你在这里！”", "speaker": "林雪"}, {"text": "“林雪，你怎么上来了？”", "speaker": "苏夜"}, {"text": "“公司出事了。”", "speaker": "林雪"}, {"text": "“今天有个神秘组织来公司搜查”", "speaker": "林雪"}, {"text": "“他们怎么知道这里有异能者？”", "speaker": "苏夜"}, {"text": "“苏夜，来会议室一趟。”", "speaker": "老陈"}, {"text": "“苏先生，我们是暗影会的调查员。”", "speaker": "黑衣人"}, {"text": "“我不知道你们在说什么。”", "speaker": "苏夜"}, {"text": "“苏夜，快来老地方！”", "speaker": "林雪"}, {"text": "“这是赵天行赵大哥。”", "speaker": "林雪"}, {"text": "“我是华夏异能者联盟的负责人。”", "speaker": "赵天行"}, {"text": "“明天开始，你来联盟总部报道。”", "speaker": "赵天行"}, {"text": "“暗影会的人来了！”", "speaker": "联盟成员"}, {"text": "“苏夜，你跟我去前线！”", "speaker": "赵天行"}, {"text": "“干得好，苏夜！”", "speaker": "赵天行"}, {"text": "“我建议潜入基地。”", "speaker": "苏夜"}, {"text": "“太危险了。”", "speaker": "林雪"}, {"text": "“样本准备好了吗？”", "speaker": "博士"}, {"text": "“这不是科学，这是犯罪！”", "speaker": "苏夜"}, {"text": "“苏夜，你这次立了大功。”", "speaker": "赵天行"}, {"text": "“这是大家共同努力的结果。”", "speaker": "苏夜"}, {"text": "“苏夜，你太棒了！”", "speaker": "林雪"}, {"text": "“为了守护这个世界！”", "speaker": "三人"}],
      "entities": {"persons": ["苏夜", "林雪", "赵天行", "老陈", "张总", "博士"], "speaking_persons": ["苏夜", "林雪", "赵天行", "老陈", "博士"], "organizations": ["暗影会", "华夏异能者联盟"], "locations": [], "aliases": {"苏夜": ["苏先生"], "赵天行": ["赵大哥"]}},
      "dialogue_sentences_sample": [{'text': '卷一 暗流涌动', 'is_dialogue': False, 'speaker': None}, {'text': '第一章 异能觉醒', 'is_dialogue': False, 'speaker': None}, {'text': '夜幕降临，霓虹灯照亮了这座不眠的城市。', 'is_dialogue': False, 'speaker': None}, {'text': '苏夜独自坐在天台上，俯瞰着脚下的车水马龙。三个月前，他还只是一名普通的程序员，直到那场意外改变了一切。', 'is_dialogue': False, 'speaker': None}, {'text': '"轰隆！"远处的雷声滚滚而来，暴雨即将来临。', 'is_dialogue': False, 'speaker': None}, {'text': '苏夜伸出手，指尖隐约闪烁着微弱的蓝色光芒。那是他觉醒的异能——操控电流。', 'is_dialogue': False, 'speaker': None}, {'text': '"苏夜，你在这里！"一个清脆的女声从楼梯口传来。', 'is_dialogue': True, 'speaker': '林雪'}, {'text': '苏夜转头看去，只见林雪快步走来。她是苏夜的同事，也是唯一知道他秘密的人。', 'is_dialogue': False, 'speaker': None}, {'text': '"林雪，你怎么上来了？"苏夜收起手中的电光，轻声问道。', 'is_dialogue': True, 'speaker': '苏夜'}, {'text': '"公司出事了。"林雪脸色凝重，"今天有个神秘组织来公司搜查，说是要找什么异能者。"', 'is_dialogue': True, 'speaker': '林雪'}],
      "dialogue_sentences_count": 144,
    },
    "annotation_content": "# 都市异能测试小说 - 标准标注文件\n# 格式: 章节标注 + 对话标注 + 实体标注 + 说话人标注\n\n## 基本信息\n- 文件名: test_novel_urban.txt\n- 风格: 都市异能\n- 总字符数: 约8000\n- 总行数: 约250\n\n## 章节标注\n卷一: 暗流涌动\n  - 第一章: 异能觉醒\n  - 第二章: 暗影初现\n  - 第三章: 异能者联盟\n  - 第四章: 初次交锋\n卷二: 破晓之光\n  - 第五章: 深入虎穴\n  - 第六章: 联盟反击\n  - 第七章: 新的曙光\n\n## 人物实体标注\n- 苏夜: PER (主角，异能者，操控电流)\n- 林雪: PER (女主角，苏夜同事，后加入联盟)\n- 赵天行: PER (华夏异能者联盟负责人，火焰异能)\n- 老陈: PER (部门经理)\n- 张总: PER (公司总经理)\n- 暗影会: ORG (反派组织)\n- 华夏异能者联盟: ORG (主角方组织)\n\n## 地点实体标注\n- 天台: LOC\n- 公司: LOC\n- 会议室: LOC\n- 咖啡馆: LOC\n- 联盟总部: LOC\n- 训练室: LOC\n- 城郊基地: LOC\n- 实验室: LOC\n\n## 对话标注样本\n- \"苏夜，你在这里！\" → 说话人: 林雪\n- \"林雪，你怎么上来了？\" → 说话人: 苏夜\n- \"公司出事了。\" → 说话人: 林雪\n- \"苏夜，来会议室一趟。\" → 说话人: 老陈\n- \"苏先生，我们是暗影会的调查员。\" → 说话人: 黑衣人\n- \"我不知道你们在说什么。\" → 说话人: 苏夜\n- \"苏夜，快来老地方！有重要的事情！\" → 说话人: 林雪\n- \"苏夜，这是赵天行赵大哥。\" → 说话人: 林雪\n- \"苏夜，你好。我是华夏异能者联盟的负责人。\" → 说话人: 赵天行\n- \"我愿意。\" → 说话人: 苏夜\n- \"苏夜，我也加入了联盟。以后我们一起战斗！\" → 说话人: 林雪\n- \"很好！\" → 说话人: 赵天行\n- \"暗影会的人来了！\" → 说话人: 联盟成员\n- \"全体戒备！苏夜，你跟我去前线！\" → 说话人: 赵天行\n- \"是！\" → 说话人: 苏夜\n- \"哼，赵天行，你的火焰还是这么嚣张！\" → 说话人: 黑衣人\n- \"暗影鼠辈，也敢在我的地盘撒野！\" → 说话人: 赵天行\n- \"没想到这里还有别的异能者！\" → 说话人: 黑衣人\n- \"撤退！\" → 说话人: 黑衣人首领\n- \"干得好，苏夜！你的电流攻击非常精准！\" → 说话人: 赵天行\n- \"根据线报，暗影会在城郊有一个秘密基地。\" → 说话人: 赵天行\n- \"我建议潜入基地，获取他们的情报。\" → 说话人: 苏夜\n- \"太危险了。\" → 说话人: 林雪\n- \"明白！\" → 说话人: 林雪\n- \"样本准备好了吗？\" → 说话人: 博士\n- \"准备好了，博士。\" → 说话人: 对讲机回应\n- \"很好。明天开始抽取程序。\" → 说话人: 博士\n- \"他们居然在研究能力抽取！\" → 说话人: 赵天行\n- \"我们必须阻止他们！\" → 说话人: 林雪\n- \"是的。\" → 说话人: 苏夜\n- \"苏夜，干得好！\" → 说话人: 赵天行\n- \"收到！我正在前往实验室，摧毁他们的研究设备！\" → 说话人: 苏夜\n- \"站住！\" → 说话人: 博士\n- \"这不是科学，这是犯罪！\" → 说话人: 苏夜\n- \"快走！\" → 说话人: 苏夜\n- \"苏夜，你这次立了大功。\" → 说话人: 赵天行\n- \"这是大家共同努力的结果。\" → 说话人: 苏夜\n- \"苏夜，你太棒了！\" → 说话人: 林雪\n- \"这都是因为有你和赵大哥的支持。\" → 说话人: 苏夜\n- \"虽然暗影会已经被击败，但我们知道，世界上还有很多未知的挑战等待着我们。\" → 说话人: 赵天行\n- \"我们准备好了。\" → 说话人: 苏夜\n- \"无论前方有什么困难，我们都会一起面对！\" → 说话人: 林雪\n- \"为了守护这个世界！\" → 说话人: 三人齐声\n\n## 拟声词标注\n- 轰隆: 雷声\n- 劈啪: 电光声\n- 叮铃铃: 电话声\n- 呜: 警报声\n- 呼: 训练声\n- 轰: 爆炸声/火焰声\n- 轰隆: 爆炸声\n- 咔嚓: 开门声\n\n## 标注规则说明\n1. 人物实体标注包含姓名和类型（PER/ORG/LOC）\n2. 对话标注包含对话内容和对应说话人\n3. 说话人标注以对话前的叙述性提示为准（如\"林雪说道\"）\n4. 拟声词标注包含词汇和对应的声音类型\n",
  },
  {
    "id": "LONG-novel_western",
    "style": "西幻",
    "novel_name": "test_novel_western.txt",
    "has_gt": True,
    "dialogue_count": 90,
    "total_sentences": 308,
    "ground_truth": {
      "novel": "test_novel_western",
      "style": "西幻",
      "dialogue_speakers": [{"text": "“北方有异动。”", "speaker": "艾德温"}, {"text": "“我能感觉到魔力的波动。”", "speaker": "伊莉雅"}, {"text": "“那不是雷声。”", "speaker": "艾德温"}, {"text": "“是炎魔，至少有三只。”", "speaker": "伊莉雅"}, {"text": "“情况如何？”", "speaker": "加尔文"}, {"text": "“炎魔入侵，立即组织防御。”", "speaker": "艾德温"}, {"text": "“是！”", "speaker": "加尔文"}, {"text": "“射击！”", "speaker": "加尔文"}, {"text": "“弓箭无效！”", "speaker": "骑士"}, {"text": "“换银箭！”", "speaker": "艾德温"}, {"text": "“它们在试探我们的实力。”", "speaker": "伊莉雅"}, {"text": "“根据古籍记载，炎魔不会无缘无故出现。”", "speaker": "伊莉雅"}, {"text": "“一定是有人召唤了它们。”", "speaker": "艾德温"}, {"text": "“巡逻队在北边发现了痕迹。”", "speaker": "加尔文"}, {"text": "“有人类与炎魔勾结？”", "speaker": "伊莉雅"}, {"text": "“很有可能。”", "speaker": "加尔文"}, {"text": "“明天一早，我带人去北方调查。”", "speaker": "艾德温"}, {"text": "“我和你一起去。”", "speaker": "伊莉雅"}, {"text": "“我留守哨站，组织防御。”", "speaker": "加尔文"}, {"text": "“魔力波动越来越强了。”", "speaker": "伊莉雅"}, {"text": "“防御！”", "speaker": "艾德温"}, {"text": "“它变强了。”", "speaker": "伊莉雅"}, {"text": "“就是现在！”", "speaker": "艾德温"}, {"text": "“没事吧？”", "speaker": "伊莉雅"}, {"text": "“没事，继续前进。”", "speaker": "艾德温"}, {"text": "“他在召唤更多的炎魔。”", "speaker": "伊莉雅"}, {"text": "“分三组，同时攻击。伊莉雅，你负责打断仪式。”", "speaker": "艾德温"}, {"text": "“明白。”", "speaker": "伊莉雅"}, {"text": "“莫洛克？”", "speaker": "艾德温"}, {"text": "“没想到你会记得我。”", "speaker": "莫洛克"}, {"text": "“你为什么要召唤炎魔？”", "speaker": "艾德温"}, {"text": "“为了力量！”", "speaker": "莫洛克"}, {"text": "“你疯了！炎魔只会毁灭一切！”", "speaker": "伊莉雅"}, {"text": "“撤退！”", "speaker": "艾德温"}, {"text": "“情况比我们想象的严重。”", "speaker": "艾德温"}, {"text": "“足以摧毁整个哨站。”", "speaker": "伊莉雅"}, {"text": "“我们必须请求支援。”", "speaker": "艾德温"}, {"text": "“在支援到达之前，我们必须加强防御。”", "speaker": "加尔文"}, {"text": "“把所有魔法师都调来。”", "speaker": "艾德温"}, {"text": "“我有个主意。”", "speaker": "伊莉雅"}, {"text": "“古籍中提到过，炎魔害怕圣水和银的组合物。”", "speaker": "伊莉雅"}, {"text": "“你能制作吗？”", "speaker": "艾德温"}, {"text": "“可以，但需要时间。”", "speaker": "伊莉雅"}, {"text": "“我们没有两天时间。”", "speaker": "加尔文"}, {"text": "“它来了。”", "speaker": "艾德温"}, {"text": "“全体准备战斗！”", "speaker": "艾德温"}, {"text": "“它还有两个小时就会到达。”", "speaker": "加尔文"}, {"text": "“我们能赢吗？”", "speaker": "年轻骑士"}, {"text": "“我们必须赢。”", "speaker": "艾德温"}, {"text": "“这是圣光药剂，能暂时增强你的力量。”", "speaker": "伊莉雅"}, {"text": "“谢谢你，伊莉雅。”", "speaker": "艾德温"}, {"text": "“不会失败的。”", "speaker": "艾德温"}, {"text": "“防线已经布置完毕。”", "speaker": "加尔文"}, {"text": "“攻击！”", "speaker": "艾德温"}, {"text": "“退守内墙！”", "speaker": "加尔文"}, {"text": "“它的力量太强了。”", "speaker": "伊莉雅"}, {"text": "“艾德温！”", "speaker": "伊莉雅"}, {"text": "“赢了吗？”", "speaker": "艾德温"}, {"text": "“赢了。”", "speaker": "伊莉雅"}, {"text": "“城墙需要完全重建。”", "speaker": "加尔文"}, {"text": "“王都的支援什么时候到？”", "speaker": "艾德温"}, {"text": "“预计明天。”", "speaker": "伊莉雅"}, {"text": "“他趁乱逃走了。”", "speaker": "加尔文"}, {"text": "“黑暗势力正在集结，目标是王都。”", "speaker": "伊莉雅"}, {"text": "“我们必须提前警告国王。”", "speaker": "艾德温"}, {"text": "“这场战争才刚刚开始。”", "speaker": "艾德温"}, {"text": "“艾德温骑士，你的英勇事迹已经传遍王都。”", "speaker": "雷纳德"}, {"text": "“我只是做了该做的事。”", "speaker": "艾德温"}, {"text": "“城墙需要重建，但人员伤亡不大。”", "speaker": "加尔文"}, {"text": "“这是证据。”", "speaker": "伊莉雅"}, {"text": "“必须立即报告国王。”", "speaker": "雷纳德"}, {"text": "“我们和你一起回去。”", "speaker": "艾德温"}, {"text": "“莫洛克的同党。”", "speaker": "雷纳德"}, {"text": "“我们必须尽快查出来。”", "speaker": "伊莉雅"}, {"text": "“为什么？”", "speaker": "艾德温"}, {"text": "“莫洛克承诺给我力量……”", "speaker": "托马斯"}, {"text": "“你背叛了圣光。”", "speaker": "艾德温"}, {"text": "“按军法处置。”", "speaker": "加尔文"}, {"text": "“等等。”", "speaker": "伊莉雅"}, {"text": "“他可能有更多的情报。”", "speaker": "伊莉雅"}, {"text": "“放过我的家人，他们什么都不知道。”", "speaker": "托马斯"}, {"text": "“我答应你。”", "speaker": "艾德温"}, {"text": "“我们必须立刻赶回王都。”", "speaker": "艾德温"}, {"text": "“勇敢的骑士们，感谢你们的到来。”", "speaker": "国王"}, {"text": "“陛下，黑暗势力正在集结。”", "speaker": "艾德温"}, {"text": "“我们将组建一支新的联军，对抗黑暗。”", "speaker": "国王"}, {"text": "“艾德温，你愿意担任先锋吗？”", "speaker": "国王"}, {"text": "“这是我的荣幸，陛下。”", "speaker": "艾德温"}, {"text": "“让我们为了光明，为了正义，为了这个世界！”", "speaker": "国王"}, {"text": "“为了光明！”", "speaker": "众人"}],
      "entities": {"persons": ["艾德温", "伊莉雅", "加尔文", "莫洛克", "雷纳德", "托马斯"], "speaking_persons": ["艾德温", "伊莉雅", "加尔文", "莫洛克", "雷纳德", "托马斯"], "organizations": ["圣骑士团", "北方魔法学院"], "locations": ["灰石哨站", "王都"], "aliases": {}},
      "dialogue_sentences_sample": [{'text': '# 西方奇幻测试小说 - 艾德温与炎魔的传说', 'is_dialogue': False, 'speaker': None}, {'text': '# 风格：翻译体西幻，魔法与骑士的世界', 'is_dialogue': False, 'speaker': None}, {'text': '# 字数：约8000字，8章，2卷', 'is_dialogue': False, 'speaker': None}, {'text': '## 第一卷：黑暗降临', 'is_dialogue': False, 'speaker': None}, {'text': '### 第一章：边境哨站', 'is_dialogue': False, 'speaker': None}, {'text': '寒风呼啸着穿过灰石哨站的城墙。', 'is_dialogue': False, 'speaker': None}, {'text': '年轻的骑士艾德温站在塔楼上，凝视着远方被白雪覆盖的荒原。', 'is_dialogue': False, 'speaker': None}, {'text': '他的披风在风中猎猎作响。', 'is_dialogue': False, 'speaker': None}, {'text': '"你在这里站了整整一夜。"', 'is_dialogue': False, 'speaker': None}, {'text': '一个温柔的声音从身后传来。', 'is_dialogue': False, 'speaker': None}],
      "dialogue_sentences_count": 308,
    },
    "annotation_content": None,
  },
  {
    "id": "LONG-novel_doupo",
    "style": "玄幻(斗破)",
    "novel_name": "test_novel_doupo_ch1-10.txt",
    "has_gt": True,
    "dialogue_count": 10,
    "total_sentences": 0,
    "ground_truth": {
      "novel": "斗破苍穹_前10章",
      "style": "玄幻",
      "dialogue_speakers": [{"text": "“斗之力，三段！”", "speaker": "测验魔石碑"}, {"text": "“萧炎，斗之力，三段！级别：低级！”", "speaker": "中年男子"}, {"text": "“下一个，萧媚！”", "speaker": "测验人"}, {"text": "“下一个，萧薰儿！”", "speaker": "测试员"}, {"text": "“萧炎哥哥。”", "speaker": "萧薰儿"}, {"text": "“我现在还有资格让你怎么叫么？”", "speaker": "萧炎"}, {"text": "“萧炎哥哥，以前你曾经与薰儿说过，要能放下，才能拿起，提放自如，是自在人！”", "speaker": "萧薰儿"}, {"text": "“呵呵，自在人？我也只会说而已，你看我现在的模样，象自在人吗？而且……这世界，本来就不属于我。”", "speaker": "萧炎"}, {"text": "“萧炎哥哥，虽然并不知道你究竟是怎么回事，不过，薰儿相信，你会重新站起来，取回属于你的荣耀与尊严……”", "speaker": "萧薰儿"}, {"text": "“当年的萧炎哥哥，的确很吸引人……”", "speaker": "萧薰儿"}],
      "entities": {"persons": ["萧炎", "萧媚", "萧薰儿", "萧战", "药老", "药尘", "纳兰嫣然", "葛叶", "云山", "云韵"], "speaking_persons": ["萧炎", "萧薰儿", "萧战", "药老", "纳兰嫣然", "葛叶"], "organizations": ["萧家", "加列家族", "云岚宗", "炼药师公会"], "locations": ["乌坦城", "斗气大陆", "后山", "测验魔石碑", "广场", "萧家", "加列家族"], "aliases": {"萧炎": ["炎儿"], "药老": ["药尘", "老者"], "萧战": ["族长", "父亲"], "萧薰儿": ["薰儿", "熏儿"], "纳兰嫣然": ["嫣然"]}},
    },
    "annotation_content": None,
  },
  {
    "id": "LONG-novel_guimi",
    "style": "诡秘(闺秘)",
    "novel_name": "test_novel_guimi_ch1-10.txt",
    "has_gt": False,
    "dialogue_count": 0,
    "total_sentences": 0,
    "ground_truth": None,
    "annotation_content": None,
  },
]
