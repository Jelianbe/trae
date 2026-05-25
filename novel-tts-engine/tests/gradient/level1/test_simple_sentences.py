# -*- coding: utf-8 -*-
"""
Level 1: 简单句匹配（单句，无上下文依赖）

目的：验证"X说"模式的基础匹配能力
测试数据：人工构造的简单句（无上下文依赖）
用例数：~35 条（合并外国名）
通过标准：≥ 95%
执行频率：每次代码改动后
执行时间：< 10 秒

v2.0 变更（2026-05-23）：
  - 合并 L2.5（外国名）所有用例
  - 扩充到 ~35 条覆盖所有单句场景
"""

import pytest
import tempfile
import os

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager


class TestSimpleSentenceMatching:
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass

    @pytest.fixture
    def char_manager(self, temp_db):
        return CharacterManager(temp_db)

    @pytest.fixture
    def matcher(self, char_manager):
        return SpeakerMatcher(char_manager)

    # ===== 基础中文名 =====
    @pytest.mark.parametrize("input_text,expected_speaker", [
        ('张三说："你好"', "张三"),
        ('李四道："再见"', "李四"),
        ('"你好"张三说。', "张三"),
        ('"再见"，李四笑着说。', "李四"),
        ('王五问道："你是谁？"', "王五"),
        ('赵六回答说："我是赵六"', "赵六"),
        ('掌柜说："客官来得巧"', "掌柜"),
        ('小翠轻声说："小姐..."', "小翠"),
        ('"把东西交出来。"黑衣人说。', "黑衣人"),
        ('张三对李四说："你去叫王五"', "张三"),
        ('李四回答道："好的"', "李四"),
        ('王五大声喊道："快跑！"', "王五"),
        ('赵六喃喃道："也许吧..."', "赵六"),
        ('"快走！"张三催促道。', "张三"),
        ('扎着马尾辫的女人："..."', "扎着马尾辫的女人"),
        # 新增
        ('冷锋道："跟我来"', "冷锋"),
        ('"小心！"阿飞喊道。', "阿飞"),
        ('林黛玉叹道："罢了"', "林黛玉"),
        ('老陈哼了一声道："你以为呢"', "老陈"),
        ('老李笑着说："那可未必"', "老李"),
    ])
    def test_simple_sentence_matching(self, input_text, expected_speaker, matcher):
        hint, hint_type = matcher.extract_speaker_hint(input_text)
        assert hint is not None, f"未能从 '{input_text}' 中提取到说话人提示"
        assert hint == expected_speaker, f"期望 '{expected_speaker}'，实际 '{hint}'"

    # ===== 外国名 =====
    @pytest.mark.parametrize("input_text,expected_speaker", [
        # 俄罗斯名字
        ('夫斯基说："今天天气不错"', "夫斯基"),
        ('伊万诺夫道："我们出发吧"', "伊万诺夫"),
        ('娜塔莎娃回答："好的"', "娜塔莎娃"),
        ('亚历山大·尼古拉耶维奇说："我明白了"', "亚历山大·尼古拉耶维奇"),
        ('米哈伊尔·谢尔盖耶维奇笑道："有趣"', "米哈伊尔·谢尔盖耶维奇"),
        # 西方名字
        ('亚瑟说："Excalibur！"', "亚瑟"),
        ('伊丽莎白·班内特回答："这是偏见"', "伊丽莎白·班内特"),
        ('哈利·波特说："除你武器！"', "哈利·波特"),
        ('克里斯托弗·哥伦布道："发现新大陆了"', "克里斯托弗·哥伦布"),
        ('汤姆说："是的，简"', "汤姆"),
        # 日本名字
        ('田中说："我回来了"', "田中"),
        ('佐藤樱井说："樱花开了"', "佐藤樱井"),
        ('宇智波鼬道："你还差得远呢"', "宇智波鼬"),
        ('小鸟游六花说："邪王真眼！"', "小鸟游六花"),
        # 音译名/混合
        ('阿卜杜拉·拉赫曼说："愿真主保佑"', "阿卜杜拉·拉赫曼"),
        # 单引号
        ("漂亮的女孩笑着说：'你好'", "漂亮的女孩"),
        ("疲惫不堪的猎人靠在树上，喃喃道：'终于...'", "疲惫不堪的猎人"),
        ("愤怒的掌柜拍着桌子吼道：'滚出去！'", "愤怒的掌柜"),
    ])
    def test_foreign_names_and_quotes(self, input_text, expected_speaker, matcher):
        hint, hint_type = matcher.extract_speaker_hint(input_text)
        assert hint is not None, f"未能从 '{input_text}' 中提取到说话人提示"
        assert hint == expected_speaker, f"期望 '{expected_speaker}'，实际 '{hint}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
