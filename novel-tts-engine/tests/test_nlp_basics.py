import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.nlp_basics import (
    NLPBasics, NLPResult, Token, Entity,
    analyze, tokenize, pos_tag, get_entities, get_persons,
    is_chapter_title_pattern, filter_chapter_title_entities
)


class TestNLPBasics:
    @pytest.fixture
    def nlp(self):
        return NLPBasics()

    def test_analyze_empty_text(self, nlp):
        result = nlp.analyze("")
        assert result.tokens == []
        assert result.entities == []
        assert result.sentences == []

    def test_analyze_whitespace(self, nlp):
        result = nlp.analyze("   ")
        assert result.tokens == []
        assert result.entities == []

    def test_analyze_simple_text(self, nlp):
        text = "这是一个测试句子。"
        result = nlp.analyze(text)
        
        assert isinstance(result, NLPResult)
        assert result.raw_text == text
        assert len(result.sentences) >= 1
        assert len(result.tokens) > 0

    def test_tokenize(self, nlp):
        text = "我爱自然语言处理"
        tokens = nlp.tokenize(text)
        
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)

    def test_pos_tag(self, nlp):
        text = "我爱自然语言处理"
        pos_tags = nlp.pos_tag(text)
        
        assert isinstance(pos_tags, list)
        assert len(pos_tags) > 0
        assert all(isinstance(t, tuple) and len(t) == 2 for t in pos_tags)

    def test_split_sentences(self, nlp):
        text = "这是第一句。这是第二句！这是第三句？"
        sentences = nlp._split_sentences(text)
        
        assert len(sentences) >= 2

    def test_split_sentences_with_newline(self, nlp):
        text = "第一行\n第二行\n第三行"
        sentences = nlp._split_sentences(text)
        
        assert len(sentences) >= 2

    def test_get_entities(self, nlp):
        text = "张三在北京工作"
        entities = nlp.get_entities(text)
        
        assert isinstance(entities, list)

    def test_get_persons(self, nlp):
        text = "张三和李四一起去了上海"
        persons = nlp.get_persons(text)
        
        assert isinstance(persons, list)

    def test_get_locations(self, nlp):
        text = "他去了北京和上海"
        locations = nlp.get_locations(text)
        
        assert isinstance(locations, list)


class TestTokenDataclass:
    def test_token_creation(self):
        token = Token(text="测试", pos="NN", ner="O")
        assert token.text == "测试"
        assert token.pos == "NN"
        assert token.ner == "O"

    def test_token_default_values(self):
        token = Token(text="测试", pos="NN")
        assert token.lemma == ""
        assert token.ner == "O"


class TestEntityDataclass:
    def test_entity_creation(self):
        entity = Entity(text="张三", type="PER", start=0, end=2)
        assert entity.text == "张三"
        assert entity.type == "PER"
        assert entity.start == 0
        assert entity.end == 2


class TestNLPResultDataclass:
    def test_nlp_result_creation(self):
        result = NLPResult(
            tokens=[Token(text="测试", pos="NN")],
            entities=[Entity(text="张三", type="PER", start=0, end=2)],
            sentences=["测试句子"],
            pos_tags=[("测试", "NN")],
            raw_text="测试句子"
        )
        assert len(result.tokens) == 1
        assert len(result.entities) == 1
        assert len(result.sentences) == 1


class TestConvenienceFunctions:
    def test_analyze_function(self):
        text = "这是一个测试。"
        result = analyze(text)
        assert isinstance(result, NLPResult)

    def test_tokenize_function(self):
        text = "测试文本"
        tokens = tokenize(text)
        assert isinstance(tokens, list)

    def test_pos_tag_function(self):
        text = "测试文本"
        tags = pos_tag(text)
        assert isinstance(tags, list)

    def test_get_entities_function(self):
        text = "测试文本"
        entities = get_entities(text)
        assert isinstance(entities, list)

    def test_get_persons_function(self):
        text = "测试文本"
        persons = get_persons(text)
        assert isinstance(persons, list)


class TestEntityExtraction:
    def test_extract_entities_bio_format(self):
        nlp = NLPBasics()
        
        tokens = [
            Token(text="张", pos="NR"),
            Token(text="三", pos="NR"),
            Token(text="在", pos="P"),
            Token(text="北", pos="NS"),
            Token(text="京", pos="NS"),
        ]
        
        entities = nlp._extract_entities_from_pos(tokens)
        
        assert len(entities) == 2
        assert entities[0].text == "张三"
        assert entities[0].type == "PER"
        assert entities[1].text == "北京"
        assert entities[1].type == "LOC"

    def test_extract_entities_single_token(self):
        nlp = NLPBasics()
        
        tokens = [
            Token(text="张三", pos="NR"),
            Token(text="在", pos="P"),
            Token(text="北京", pos="NS"),
        ]
        
        entities = nlp._extract_entities_from_pos(tokens)
        
        assert len(entities) == 2
        assert entities[0].text == "张三"
        assert entities[1].text == "北京"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestChapterTitlePattern:
    """Tests for is_chapter_title_pattern function."""

    def test_chapter_number_chinese(self):
        """Test '第一章' is detected as chapter title."""
        assert is_chapter_title_pattern("第一章") is True

    def test_chapter_number_arabic(self):
        """Test '第1章' is detected as chapter title."""
        assert is_chapter_title_pattern("第1章") is True

    def test_volume_chinese(self):
        """Test '卷一' is detected as chapter title."""
        assert is_chapter_title_pattern("卷一") is True

    def test_volume_arabic(self):
        """Test '卷1' is detected as chapter title."""
        assert is_chapter_title_pattern("卷1") is True

    def test_chapter_with_hui(self):
        """Test '第一百回' is detected as chapter title."""
        assert is_chapter_title_pattern("第一百回") is True

    def test_chapter_with_jie(self):
        """Test '第2节' is detected as chapter title."""
        assert is_chapter_title_pattern("第2节") is True

    def test_normal_name_not_matched(self):
        """Test '林轩' is not detected as chapter title."""
        assert is_chapter_title_pattern("林轩") is False

    def test_number_in_body_not_matched(self):
        """Test '三天' (number in body text) is not detected as chapter title."""
        assert is_chapter_title_pattern("三天") is False

    def test_complex_chapter_title(self):
        """Test '第一章 觉醒' is detected as chapter title (prefix match)."""
        assert is_chapter_title_pattern("第一章 觉醒") is True

    def test_volume_with_title(self):
        """Test '卷一 风起云涌' is detected as chapter title."""
        assert is_chapter_title_pattern("卷一 风起云涌") is True

    def test_location_name_not_matched(self):
        """Test '北京' is not detected as chapter title."""
        assert is_chapter_title_pattern("北京") is False

    def test_organization_not_matched(self):
        """Test '天龙帮' is not detected as chapter title."""
        assert is_chapter_title_pattern("天龙帮") is False


class TestFilterChapterTitleEntities:
    """Tests for filter_chapter_title_entities function."""

    def test_filter_chapter_one(self):
        """Test '第一章' entity is filtered out."""
        entities = [
            Entity(text="第一章", type="LOC", start=0, end=3),
        ]
        filtered = filter_chapter_title_entities(entities)
        assert len(filtered) == 0

    def test_filter_volume_one(self):
        """Test '卷一' entity is filtered out."""
        entities = [
            Entity(text="卷一", type="LOC", start=0, end=2),
        ]
        filtered = filter_chapter_title_entities(entities)
        assert len(filtered) == 0

    def test_preserve_normal_name(self):
        """Test normal name like '林轩' is preserved."""
        entities = [
            Entity(text="林轩", type="PER", start=0, end=2),
        ]
        filtered = filter_chapter_title_entities(entities)
        assert len(filtered) == 1
        assert filtered[0].text == "林轩"

    def test_preserve_numbers_in_body(self):
        """Test numbers in body text like '三天' are preserved."""
        entities = [
            Entity(text="三天", type="NUM", start=0, end=2),
        ]
        filtered = filter_chapter_title_entities(entities)
        assert len(filtered) == 1
        assert filtered[0].text == "三天"

    def test_mixed_entities(self):
        """Test mixed entities are filtered correctly."""
        entities = [
            Entity(text="第一章", type="LOC", start=0, end=3),
            Entity(text="林轩", type="PER", start=10, end=12),
            Entity(text="卷二", type="LOC", start=20, end=22),
            Entity(text="北京", type="LOC", start=30, end=32),
        ]
        filtered = filter_chapter_title_entities(entities)
        
        assert len(filtered) == 2
        assert filtered[0].text == "林轩"
        assert filtered[1].text == "北京"

    def test_empty_entities(self):
        """Test empty entity list returns empty."""
        filtered = filter_chapter_title_entities([])
        assert filtered == []

    def test_all_chapter_titles_filtered(self):
        """Test all chapter title patterns are filtered."""
        entities = [
            Entity(text="第1章", type="LOC", start=0, end=4),
            Entity(text="第100回", type="LOC", start=10, end=16),
            Entity(text="第一百章", type="LOC", start=20, end=24),
            Entity(text="卷1", type="LOC", start=30, end=33),
        ]
        filtered = filter_chapter_title_entities(entities)
        assert len(filtered) == 0

    def test_with_chapter_objects(self):
        """Test filtering with Chapter objects for position-based filtering."""
        from pipeline.chapter_splitter import Chapter
        
        chapters = [
            Chapter(index=0, title="第一章 觉醒", content="content", start_pos=0, end_pos=100),
        ]
        
        entities = [
            Entity(text="第一章", type="LOC", start=0, end=3),
            Entity(text="觉醒", type="PER", start=4, end=6),  # In title range
            Entity(text="林轩", type="PER", start=10, end=12),  # In content
        ]
        filtered = filter_chapter_title_entities(entities, chapters=chapters)
        
        # Only 林轩 should remain (第一章 is pattern match, 觉醒 is in title range)
        assert len(filtered) == 1
        assert filtered[0].text == "林轩"

    def test_preserve_entity_with_similar_pattern(self):
        """Test entities that contain chapter-like text but are not chapter titles."""
        # This tests edge cases where chapter-like text appears in body
        entities = [
            Entity(text="三", type="NUM", start=0, end=1),
            Entity(text="一", type="NUM", start=2, end=3),
        ]
        filtered = filter_chapter_title_entities(entities)
        # Single characters should not match chapter patterns
        assert len(filtered) == 2
