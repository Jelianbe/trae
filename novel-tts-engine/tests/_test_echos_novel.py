# -*- coding: utf-8 -*-
"""跑《回声》测试 HybridSpeakerMatcher — 追踪 LLM 触发情况"""

import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DEBUG_NER'] = '0'

from pipeline.character_manager import CharacterManager
from pipeline.hybrid_speaker_matcher import HybridSpeakerMatcher

NOVEL_TEXT = """周五傍晚六点四十分，天已经黑透了。

苏晚站在公寓楼下，缩了缩脖子。十一月的风裹着细碎的雨丝，钻进她的衣领，冷得她打了个哆嗦。手机屏幕亮了一下，是快递员的号码。

"喂？您好，我就在楼下，您到了吗？"她努力让自己的声音听起来不那么急躁。

电话那头传来一阵刺耳的刹车声，然后是一个气喘吁吁的男声："到了到了！不好意思啊，刚才路上堵了半小时。您稍等，我马上上来。"

苏晚叹了口气，把手机塞回口袋。她已经等了二十分钟，脚趾在靴子里冻得发麻。旁边的路灯把她的影子拉得很长，像一根孤零零的电线杆。

电梯门打开的时候，一个穿着蓝色工装的小伙子冲了出来，怀里抱着一个纸箱。他的脸被风吹得发红，额头上却挂着汗珠。

"苏女士？您的快递。"他把箱子递过来，喘着粗气，"实在抱歉，今天单子太多……"

"没事。"苏晚接过箱子，低头看了眼寄件人——是妈妈寄来的。她心里突然一暖，语气也软了下来，"辛苦了，这么晚还在送。"

快递员咧嘴笑了笑："干我们这行的，哪有什么早晚。您慢用，我先走了！"说完转身就跑，电梯门在他身后缓缓合拢。

苏晚抱着箱子回到七楼的出租屋，把钥匙扔在玄关的鞋柜上，发出一声清脆的"啪嗒"。她用小刀划开胶带，打开纸箱，里面塞满了东西——自家灌的香肠、两罐辣椒酱、一件叠得整整齐齐的灰色毛衣，还有一张纸条。

纸条上是妈妈的笔迹，歪歪扭扭的："晚晚，天冷了，多穿点。别老吃外卖，对胃不好。妈想你。"

她的眼眶忽然有点发酸。

"哟，阿姨又寄好吃的了？"

声音从身后传来。苏晚转过头，看到林洋倚在厨房门口，手里端着一杯冒着热气的咖啡。他是她的合租室友，在一家互联网公司做产品经理，常年穿一件深蓝色的卫衣，头发乱糟糟的，像个没睡醒的大学生。

"你怎么跟鬼似的，一点声音都没有。"苏晚擦了擦眼睛，没好气地说。

林洋耸耸肩："是你太投入了。对了，晚上吃什么？我点了两份酸菜鱼，一会儿送到。"

"又点外卖？"苏晚皱眉，"上周你不是说要减肥吗？"

"那是上周的我，这周的我决定活出真我。"林洋一本正经地说，然后走进客厅，一屁股坐在沙发上，打开了电视。

电视里正在播一档财经访谈节目，主持人用标准的播音腔问道："林总，您认为未来五年房地产行业的发展趋势会如何？"画面切到一个西装革履的中年男人，他清了清嗓子，开始滔滔不绝地讲什么"存量博弈"、"城市分化"。

苏晚把毛衣拿出来在身上比了比，大小刚好。她把东西收拾好，走进客厅，在林洋旁边坐下。

"能不能换个台？"她问。

"遥控器在你那边。"林洋指了指茶几。

苏晚拿起遥控器，按了几下，屏幕跳到一个地方台，正在放一个调解节目。一个大妈哭天抹泪地说："我养了你二十年啊，你就这么对我？"

"还是财经吧。"苏晚果断换回去。

林洋笑了："你这品味，真是一言难尽。"

"你品味好？上周末你放的什么《乡村爱情》第十一部，我都替你丢人。"

"那是经典！你不懂。"

两人正拌着嘴，门铃响了。林洋跳起来去开门，拎回来两个塑料袋，酸菜鱼的香味一下子弥漫了整个屋子。他们坐在餐桌前，一人捧着一碗米饭，开始吃起来。

"说真的，"林洋夹了一块鱼片，含混不清地说，"你这周面试怎么样？上次你不是说有个公司让你去二面吗？"

苏晚的动作顿了一下。

"没成。"她低声说，"人家要五年经验，我才三年。"

林洋放下筷子，认真地看着她："那你打算怎么办？接着找？"

"不然呢？"苏晚苦笑，"总不能啃老吧。我妈还指着我寄钱回去呢。"

客厅里安静了几秒。电视里的财经专家还在分析什么"结构性机会"，声音听起来遥远而空洞。

"其实，"林洋犹豫了一下，"我们公司最近在招运营，你要不要试试？我可以内推。"

苏晚抬起头，眼睛里闪过一丝惊讶："你们公司？那个……什么科技？"

"云创科技。做企业服务的，虽然不大，但氛围还行。"林洋擦了擦嘴，"薪资可能比你之前低一点，但稳定。你先别急着拒绝，考虑考虑。"

苏晚没有说话。她低头看着碗里的米饭，心里乱糟糟的。来这座城市三年了，换了三份工作，每一次都像是从一个坑跳进另一个坑。她有时候怀疑自己是不是选错了路——如果当初听妈妈的话，留在老家考个公务员，是不是现在已经过上安稳的日子了？

可是她不甘心。

"好，我考虑一下。"她最终说。

林洋点点头，没有再说什么，低头继续吃鱼。

吃完饭，苏晚洗了碗，回到自己的房间。窗外雨下得更大了，啪啪地打在玻璃上，像有人在外面敲鼓。她打开台灯，拿出笔记本，准备改一改简历。

手机突然震动了。

是一个陌生号码，本地座机。她犹豫了一下，还是接了。

"喂，您好，请问是苏晚女士吗？"一个礼貌的女声。

"是我，您哪位？"

"您好，我是鼎盛集团人力资源部的。我们在招聘平台上看到您的简历，想邀请您来面试，岗位是市场策划。您明天上午方便吗？"

苏晚的心猛地跳了一下。

鼎盛集团？那可是这座城市排名前十的大公司。她之前投过简历，但石沉大海，没想到现在突然来了电话。

"方……方便的。"她努力让自己的声音平稳，"明天几点？"

"上午十点，您看可以吗？地址我稍后发到您手机上。"

"可以可以，谢谢您！"

挂了电话，苏晚愣了几秒，然后猛地从椅子上跳起来，冲到客厅。

林洋正窝在沙发上看手机，被她吓了一跳："干嘛？着火啦？"

"鼎盛！鼎盛让我去面试！"苏晚几乎是在喊。

"真的假的？"林洋也坐直了身子，"那可是大厂啊，你投了多久了？"

"快一个月了，我都以为没戏了！"苏晚激动得在客厅里来回走，"不行，我得准备一下，明天穿什么？简历要重新打印吗？他们会不会问很刁钻的问题？"

林洋看着她像无头苍蝇一样转来转去，忍不住笑了："你先冷静，深呼吸。面试就面试，你又不是没面过。来，坐下，我帮你模拟一下。"

苏晚深吸一口气，坐到他对面。

林洋清了清嗓子，板起脸，装出一副面试官的严肃表情："苏女士，请自我介绍一下。"

"噗——"苏晚没忍住笑了出来，"你这也太假了吧？"

"笑什么笑，正经的！"林洋敲了敲茶几，"重新来。"

苏晚抿住嘴，挺直腰背，用尽量沉稳的声音说："各位面试官好，我叫苏晚，毕业于……"

窗外的雨声渐渐小了。客厅的灯光暖黄，照在两个年轻人的脸上。这一刻，所有的焦虑、迷茫、不安，似乎都被暂时遗忘，只剩下一种单纯的期待。

明天，也许会是新的一天。"""


def main():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        cm = CharacterManager(db_path)
        for name, gender, aliases in [
            ("苏晚", "female", {"晚晚"}),
            ("林洋", "male", set()),
            ("快递员", "male", {"小伙子"}),
            ("妈妈", "female", set()),
        ]:
            cm.add_character(name, gender=gender, aliases=aliases)
        suwan = cm.get_character_by_name("苏晚")
        linyang = cm.get_character_by_name("林洋")
        if suwan:
            cm.lock_character(suwan.id)

        sm = HybridSpeakerMatcher(cm)

        # Patch _llm_fallback 加日志
        orig_llm = sm._llm_fallback
        llm_triggered = []  # (dialogue, reason, rule_result)

        def logged_llm(context):
            llm_triggered.append({
                'dialogue': getattr(context, 'dialogue', None) or context.text,
                'context_before': (context.context_before or '')[:50],
                'context_after': (context.context_after or '')[:50],
            })
            return orig_llm(context)

        sm._llm_fallback = logged_llm

        # Patch match_speaker 记录规则结果
        orig_match = sm.match_speaker
        rule_results = []

        def logged_match(context):
            orig = getattr(sm, '_rule_matcher_orig', None)
            if orig:
                rule_result = orig(context)
            else:
                rule_result = sm.rule_matcher.match_speaker(context)
            rule_results.append({
                'character': rule_result.character.name if rule_result else None,
                'confidence': rule_result.confidence if rule_result else None,
                'match_type': rule_result.match_type if rule_result else None,
            })
            return orig_match(context)

        sm.match_speaker = logged_match

        print("=" * 85)
        print("  《回声》—— HybridSpeakerMatcher 详细报告")
        print("=" * 85)

        results = sm.analyze_dialogue(NOVEL_TEXT, chapter_id=1)

        print(f"\n共识别 {len(results)} 段对话\n")
        print("-" * 85)

        for i, (dia, speaker) in enumerate(results):
            rr = rule_results[i] if i < len(rule_results) else {}
            triggered = next(
                (t for t in llm_triggered
                 if (t['dialogue'][:40] in (dia or '') or (dia or '')[:40] in t['dialogue'])),
                None
            )

            speaker_name = speaker.name if speaker else "???"
            conf = rr.get('confidence', '?')
            mtype = rr.get('match_type', '?')
            rn = rr.get('character', '-')

            trigger_tag = " 🤖LLM!" if triggered else ""
            diag = ("规则→" + str(rn)[:8] +
                    f"(c={conf})"
                    + f" [{mtype[:16]}]") if rn else "None→LLM"

            dia_short = dia[:40] + "..." if len(dia) > 40 else dia
            print(f"  [{i+1:2d}] {trigger_tag}  «{dia_short}»")
            print(f"        → {speaker_name}  [{diag}]")

            if triggered:
                print(f"        LLM 输入: 前={triggered['context_before']} | 后={triggered['context_after']}")
            print()

        print("-" * 85)
        print(f"  LLM 实际调用次数: {sm._llm_call_count}")
        print(f"  LLM 被触发段数 : {len(llm_triggered)}")
        print(f"  LLM 触发明细:")
        for i, t in enumerate(llm_triggered):
            d = t['dialogue'][:35]
            print(f"    [{i+1}] «{d}...»")
        print("=" * 85)

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except:
                pass


if __name__ == "__main__":
    main()
