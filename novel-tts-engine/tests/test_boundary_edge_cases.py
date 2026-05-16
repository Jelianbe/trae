"""
边界条件与异常场景综合测试
涵盖：极端输入、空数据、特殊字符、大数据量、错误数据
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pipeline.chapter_splitter import ChapterSplitter
from pipeline.emotion_extractor import EmotionExtractor
from pipeline.nlp_basics import NLPBasics
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.entity_linker import EntityLinker
from pipeline.context_diversity_validator import ContextDiversityValidator
from pipeline.speaker_role_filter import SpeakerRoleFilter
from pipeline.pronoun_resolver import PronounResolver
from pipeline.semantic_ranker import SemanticRanker
from pipeline.hybrid_speaker_matcher import HybridSpeakerMatcher
from pipeline.entity_cleaner import EntityCleaner


# ============================================================
# 第1组：空输入/极短输入测试
# ============================================================
class TestEmptyInput:
    def test_chapter_splitter_empty(self):
        s = ChapterSplitter()
        result = s.split("")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_chapter_splitter_whitespace(self):
        s = ChapterSplitter()
        result = s.split("   \n  \n  ")
        assert len(result) >= 1

    def test_emotion_extractor_empty(self):
        e = EmotionExtractor()
        r = e.classify("")
        assert r is not None

    def test_nlp_basics_empty(self):
        n = NLPBasics()
        r = n.analyze("")
        assert r is not None
        assert len(r.entities) == 0

    def test_entity_linker_empty_input(self):
        linker = EntityLinker(char_manager=CharacterManager())
        r = linker.link([], "")
        assert isinstance(r, list)
        assert len(r) == 0

    def test_entity_cleaner_empty_input(self):
        cleaner = EntityCleaner()
        r = cleaner.clean([], "")
        assert isinstance(r, list)


# ============================================================
# 第2组：极端字符测试
# ============================================================
class TestExtremeCharacters:
    def test_only_numbers(self):
        n = NLPBasics()
        r = n.analyze("1234567890")
        assert r is not None

    def test_very_long_single_word(self):
        """超长单个词汇（无空格、无标点）"""
        n = NLPBasics()
        r = n.analyze("的" * 10000)
        assert r is not None

    def test_mixed_scripts(self):
        """中日韩英混合"""
        n = NLPBasics()
        text = "Hello世界こんにちは안녕하세요" + "他说" + "a" * 100
        r = n.analyze(text)
        assert r is not None

    def test_unicode_control_chars(self):
        """Unicode控制字符"""
        n = NLPBasics()
        text = "\u0000\u0001\u0002\u0003" + "你好" + "\ufffe\uffff"
        r = n.analyze(text)
        assert r is not None

    def test_zero_width_chars(self):
        """零宽字符"""
        n = NLPBasics()
        text = "他\u200b说\u200c：\u200d\"你好\""
        r = n.analyze(text)
        assert r is not None


# ============================================================
# 第3组：边界数值测试
# ============================================================
class TestBoundaryValues:
    def test_exactly_5000_chars(self):
        """5000字精确边界（分章阈值）"""
        s = ChapterSplitter()
        text = "测试" * 2500
        result = s.split(text)
        assert len(result) >= 1

    def test_just_under_chapter_threshold(self):
        """略低于分章阈值"""
        s = ChapterSplitter()
        text = (("第1章 测试\n" + "内容" * 100 + "\n") +
                ("第2章 测试\n" + "内容" * 50))
        result = s.split(text)
        assert len(result) >= 2

    def test_overlapping_chapter_boundary(self):
        """重叠分章边界"""
        s = ChapterSplitter()
        text = ("内容" * 4000 + "第1章 标题" + "内容" * 4000)
        result = s.split(text)
        assert len(result) >= 2

    def test_single_character_dialogue(self):
        """单个字符的对话"""
        sm = SpeakerMatcher(char_manager=CharacterManager())
        r = sm.analyze_dialogue('他说"好"')
        assert len(r) >= 1


# ============================================================
# 第4组：异常数据注入测试
# ============================================================
class TestMalformedData:
    def test_malformed_chapter_title(self):
        """畸形的章节标题"""
        s = ChapterSplitter()
        text = "第零章 测试\n内容\n第壹章 测试\n内容"
        result = s.split(text)
        assert len(result) >= 1

    def test_repeated_same_speaker(self):
        """同一角色连续对话100次"""
        sm = SpeakerMatcher(char_manager=CharacterManager())
        text = "他说" + '"你好"' * 100
        r = sm.analyze_dialogue(text)
        assert len(r) >= 1

    def test_very_long_entity_name(self):
        """超长实体名"""
        n = NLPBasics()
        text = "尼古拉斯赵四罗伯特威廉姆斯说" + '"你好"'
        r = n.analyze(text)
        assert r is not None

    def test_repeated_speaker_no_context(self):
        """无上下文语境时说话人匹配不崩溃"""
        sm = SpeakerMatcher(char_manager=CharacterManager())
        text = '"你好"' * 100
        r = sm.analyze_dialogue(text)
        assert isinstance(r, list)


# ============================================================
# 第5组：重复操作一致性测试
# ============================================================
class TestRepeatedOperations:
    def test_repeated_analyze_same_text(self):
        """同一文本重复分析10次，结果应一致"""
        n = NLPBasics()
        text = "张三说\"你好\"李四说\"再见\""
        results = [n.analyze(text) for _ in range(10)]
        for i in range(1, len(results)):
            assert len(results[i].entities) == len(results[0].entities)
            assert len(results[i].sentences) == len(results[0].sentences)

    def test_repeated_create_same_character(self):
        """重复创建同一角色不应产生重复"""
        cm = CharacterManager()
        unique_id = f"test_repeat_{id(self)}"
        c1 = cm.find_or_create(unique_id, "test_project")
        c2 = cm.find_or_create(unique_id, "test_project")
        c3 = cm.find_or_create(unique_id, "test_project")
        chars = cm.get_all_characters("test_project")
        matching = [c for c in chars if c.name == unique_id]
        assert len(matching) == 1, f"重复创建产生了{len(matching)}个同名角色"

    def test_emotion_repeated_same_result(self):
        """情绪分类对相同输入应返回相同结果"""
        e = EmotionExtractor()
        text = "他冷笑道：\"你以为你跑得掉吗？\""
        labels = [e.classify(text).emotion_label for _ in range(5)]
        assert len(set(labels)) == 1, f"同一输入产生了不同情绪标签: {labels}"


# ============================================================
# 第6组：错误处理和异常安全测试
# ============================================================
class TestErrorHandling:
    def test_speaker_matcher_bad_project_id(self):
        """不存在的project_id"""
        sm = SpeakerMatcher(char_manager=CharacterManager())
        try:
            r = sm.analyze_dialogue('他说"你好"', chapter_id="nonexistent_999")
            assert isinstance(r, list)
        except Exception as e:
            pytest.fail(f"不存在的project_id导致崩溃: {e}")

    def test_pronoun_resolver_no_gender_info(self):
        """无性别信息的代词消解"""
        resolver = PronounResolver(char_manager=CharacterManager())
        try:
            r = resolver.resolve("他站起来说\"你好\"")
            assert isinstance(r, list)
        except Exception as e:
            pytest.fail(f"无性别信息导致崩溃: {e}")


# ============================================================
# 第7组：大数据量性能基线测试
# ============================================================
class TestLargeDataBaseline:
    def test_5000_char_nlp(self):
        """5000字文本NLP分析性能基线"""
        import time
        n = NLPBasics()
        text = "张三说\"你好啊\"李四回答\"我很好\"" * 500
        start = time.time()
        r = n.analyze(text)
        elapsed = time.time() - start
        print(f"\n[PERF] 5000字NLP分析: {elapsed:.3f}s, 实体数: {len(r.entities)}")

    def test_1000_dialogue_chunks(self):
        """1000个对话块的说话人匹配性能基线"""
        import time
        sm = SpeakerMatcher(char_manager=CharacterManager())
        text = "他说" + '"你好。"' * 500
        start = time.time()
        r = sm.analyze_dialogue(text)
        elapsed = time.time() - start
        print(f"\n[PERF] 说话人匹配(500块): {elapsed:.3f}s, 结果数: {len(r)}")


# ============================================================
# 第8组：集成验证 — 跨模块数据一致性
# ============================================================
class TestIntegrationConsistency:
    def test_entity_pipeline_end_to_end(self):
        """完整实体分析流水线：NLP → 多样性验证 → 角色过滤 → 实体链接"""
        text = "张三走进房间。李四抬头看了他一眼。张三说道\"你来了。\"李四回答\"嗯。\""
        nlp = NLPBasics()
        nlp_result = nlp.analyze(text)
        assert len(nlp_result.entities) > 0, "NER未提取到任何实体"

        validator = ContextDiversityValidator()
        validated = validator.validate(nlp_result.entities, text)
        assert len(validated) > 0, "多样性验证过滤了所有实体"

        filter_ = SpeakerRoleFilter()
        filtered = filter_.filter(validated, text, nlp)
        assert len(filtered) > 0, "角色过滤后实体为空"

        cm = CharacterManager()
        linker = EntityLinker(char_manager=cm)
        linked = linker.link(filtered, text)
        assert len(linked) > 0, "实体链接后结果为空"

    def test_speaker_and_emotion_consistency(self):
        """说话人匹配 → 情绪分类的数据一致性"""
        text = '张三冷笑道："你以为你跑得掉吗？"'
        sm = SpeakerMatcher(char_manager=CharacterManager())
        emotion = EmotionExtractor()
        dialogues = sm.analyze_dialogue(text)
        assert len(dialogues) > 0, "说话人匹配未返回结果"
        if len(dialogues) > 0:
            text_part = dialogues[0][0] if isinstance(dialogues[0], tuple) else dialogues[0]
            emotion_result = emotion.classify(str(text_part))
            assert emotion_result is not None

    def test_chapter_speaker_char_link(self):
        """章节 → 说话人 → 角色的完整链路"""
        text = "第1章 相遇\n张三说\"你好。\""
        cm = CharacterManager()
        sm = SpeakerMatcher(char_manager=cm)
        results = sm.analyze_dialogue(text)
        assert len(results) >= 1
        chars = cm.get_all_characters()
        assert len(chars) > 0, "说话人匹配未在角色管理器中注册角色"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
