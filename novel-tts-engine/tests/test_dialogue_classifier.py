import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.dialogue_classifier import (
    DialogueClassifier, ClassifiedSentence,
    classify_sentence, classify_sentences, is_dialogue
)


class TestDialogueClassifier:
    @pytest.fixture
    def classifier(self):
        return DialogueClassifier()

    def test_classify_dialogue_with_quotes(self, classifier):
        text = '「你好，请问这里是哪里？」'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'dialogue'
        assert result.is_dialogue is True
        assert result.confidence >= 0.85

    def test_classify_dialogue_with_double_quotes(self, classifier):
        text = '"这是对话内容。"'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'dialogue'
        assert result.is_dialogue is True

    def test_classify_dialogue_with_curly_quotes(self, classifier):
        text = '"这是中文引号的对话。"'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'dialogue'
        assert result.is_dialogue is True

    def test_classify_dialogue_with_says(self, classifier):
        text = '他说道："今天天气真好。"'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'dialogue'
        assert result.is_dialogue is True

    def test_classify_narration_with_think(self, classifier):
        text = '他心想，这事情有些不对劲。'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'narration'
        assert result.is_dialogue is False

    def test_classify_narration_with_feel(self, classifier):
        text = '她觉得这件事情有些蹊跷。'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'narration'
        assert result.is_dialogue is False

    def test_classify_narration_plain(self, classifier):
        text = '太阳从东方升起，照亮了整个城市。'
        result = classifier.classify(text)
        
        assert result.sentence_type == 'narration'
        assert result.is_dialogue is False

    def test_classify_empty_text(self, classifier):
        result = classifier.classify("")
        
        assert result.sentence_type == 'narration'
        assert result.confidence == 0.5

    def test_classify_whitespace(self, classifier):
        result = classifier.classify("   ")
        
        assert result.sentence_type == 'narration'

    def test_extract_dialogue_content(self, classifier):
        text = '「这是对话内容」'
        content = classifier._extract_dialogue_content(text)
        
        assert content == '这是对话内容'

    def test_extract_dialogue_content_double_quotes(self, classifier):
        text = '"这是双引号对话"'
        content = classifier._extract_dialogue_content(text)
        
        assert content == '这是双引号对话'

    def test_classify_batch(self, classifier):
        texts = [
            '「对话一」',
            '这是旁白。',
            '"对话二"'
        ]
        results = classifier.classify_batch(texts)
        
        assert len(results) == 3
        assert results[0].is_dialogue is True
        assert results[1].is_dialogue is False
        assert results[2].is_dialogue is True


class TestClassifiedSentenceDataclass:
    def test_creation(self):
        sentence = ClassifiedSentence(
            text="测试文本",
            sentence_type="dialogue",
            confidence=0.95,
            is_dialogue=True
        )
        
        assert sentence.text == "测试文本"
        assert sentence.sentence_type == "dialogue"
        assert sentence.confidence == 0.95
        assert sentence.is_dialogue is True


class TestConvenienceFunctions:
    def test_classify_sentence_function(self):
        text = '「测试对话」'
        result = classify_sentence(text)
        
        assert isinstance(result, ClassifiedSentence)
        assert result.is_dialogue is True

    def test_classify_sentences_function(self):
        texts = ['「对话」', '旁白文本']
        results = classify_sentences(texts)
        
        assert len(results) == 2
        assert all(isinstance(r, ClassifiedSentence) for r in results)

    def test_is_dialogue_function(self):
        assert is_dialogue('「对话」') is True
        assert is_dialogue('这是旁白。') is False


class TestAccuracy:
    @pytest.fixture
    def classifier(self):
        return DialogueClassifier()

    def test_accuracy_dialogue(self, classifier):
        test_cases = [
            ('「你好」', 'dialogue'),
            ('"测试对话"', 'dialogue'),
            ('他说："走吧。"', 'dialogue'),
            ('「请问你是谁？」', 'dialogue'),
            ('『这是书名号对话』', 'dialogue'),
        ]
        
        correct = 0
        for text, expected in test_cases:
            result = classifier.classify(text)
            if result.sentence_type == expected:
                correct += 1
        
        accuracy = correct / len(test_cases) * 100
        assert accuracy >= 80

    def test_accuracy_narration(self, classifier):
        test_cases = [
            ('他心想这件事不对。', 'narration'),
            ('她觉得有些奇怪。', 'narration'),
            ('这时，门开了。', 'narration'),
            ('原来如此，他想。', 'narration'),
            ('太阳落山了。', 'narration'),
        ]
        
        correct = 0
        for text, expected in test_cases:
            result = classifier.classify(text)
            if result.sentence_type == expected:
                correct += 1
        
        accuracy = correct / len(test_cases) * 100
        assert accuracy >= 80


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
