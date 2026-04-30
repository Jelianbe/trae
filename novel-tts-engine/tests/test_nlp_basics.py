import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.nlp_basics import (
    NLPBasics, NLPResult, Token, Entity,
    analyze, tokenize, pos_tag, get_entities, get_persons
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
