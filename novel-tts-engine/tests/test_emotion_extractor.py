# -*- coding: utf-8 -*-
"""EmotionExtractor 单元测试（方案B：双管道情绪提取，三层标注体系）"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.emotion_extractor import EmotionExtractor, EmotionResult


class TestEmotionExtractor:
    @pytest.fixture
    def extractor(self):
        return EmotionExtractor()

    def test_anger_dirty_words(self, extractor):
        """愤怒：脏话/粗口"""
        result = extractor.classify("你给我滚出去！混蛋！")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'anger', f"期望 anger，得到 {result.emotion_label}"
        assert result.confidence >= 0.5

    def test_anger_imperative_exclamation(self, extractor):
        """愤怒：祈使句 + 高感叹号密度"""
        result = extractor.classify("全体集合！准备战斗！马上！")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'anger', f"期望 anger，得到 {result.emotion_label}"
        assert result.confidence >= 0.4

    def test_anger_emotion_verb(self, extractor):
        """愤怒：情绪动词"""
        result = extractor.classify("他怒吼道：你太放肆了！")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'anger', f"期望 anger，得到 {result.emotion_label}"

    def test_fear_trembling(self, extractor):
        """恐惧：颤抖动词"""
        result = extractor.classify("她颤抖着说：别过来……我害怕……")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'fear', f"期望 fear，得到 {result.emotion_label}"
        assert result.confidence >= 0.4

    def test_fear_short_questions(self, extractor):
        """恐惧：短句 + 问号"""
        result = extractor.classify("是谁？在哪？别吓我……")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label in ('fear', 'surprise'), f"得到 {result.emotion_label}"

    def test_sadness_sigh(self, extractor):
        """悲伤：叹词开头"""
        result = extractor.classify("唉，这一切都结束了……")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'sadness', f"期望 sadness，得到 {result.emotion_label}"
        assert result.confidence >= 0.4

    def test_sadness_emotion_adverb(self, extractor):
        """悲伤：情绪副词"""
        result = extractor.classify("他不禁流下了眼泪……")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'sadness', f"期望 sadness，得到 {result.emotion_label}"

    def test_surprise_rhetorical(self, extractor):
        """惊讶：反问句"""
        result = extractor.classify("难道这不是你做的吗？怎么可能！")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'surprise', f"期望 surprise，得到 {result.emotion_label}"
        assert result.confidence >= 0.4

    def test_surprise_how_unexpected(self, extractor):
        """惊讶：怎么/居然/竟然"""
        result = extractor.classify("他居然来了？怎么会有这种事？")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'surprise', f"期望 surprise，得到 {result.emotion_label}"

    def test_joy_laughter(self, extractor):
        """喜悦：笑声"""
        result = extractor.classify("哈哈哈！太好了！太棒了！")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'joy', f"期望 joy，得到 {result.emotion_label}"
        assert result.confidence >= 0.5

    def test_joy_exclamatory(self, extractor):
        """喜悦：感叹句模式"""
        result = extractor.classify("太好了！这简直是完美！")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'joy', f"期望 joy，得到 {result.emotion_label}"

    def test_neutral_plain_statement(self, extractor):
        """中性：平淡叙述"""
        result = extractor.classify("他走进了房间，看了看四周。")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'neutral', f"期望 neutral，得到 {result.emotion_label}"

    def test_neutral_question(self, extractor):
        """中性：普通询问"""
        result = extractor.classify("你知道这件事吗？")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label in ('neutral', 'surprise'), f"得到 {result.emotion_label}"

    def test_empty_text(self, extractor):
        """空文本"""
        result = extractor.classify("")
        assert isinstance(result, EmotionResult)
        assert result.emotion_label == 'neutral'

    def test_batch_classify(self, extractor):
        """批量分类"""
        texts = [
            "你给我滚出去！",
            "哈哈哈！太好了！",
            "唉，一切都结束了……",
            "他走进了房间。",
        ]
        results = extractor.batch_classify(texts)
        assert len(results) == 4
        assert all(isinstance(r, EmotionResult) for r in results)
        assert results[0].emotion_label == 'anger'
        assert results[1].emotion_label == 'joy'
        assert results[2].emotion_label == 'sadness'

    def test_classify_simple_compat(self, extractor):
        """简化接口兼容性测试"""
        emotion, conf = extractor.classify_simple("你给我滚出去！")
        assert emotion == 'anger'
        assert conf >= 0.5

    def test_emotion_result_fields(self, extractor):
        """EmotionResult 三层标注字段测试"""
        result = extractor.classify("你给我滚出去！混蛋！")
        # L1 粗分类
        assert result.emotion_class in ('neutral', 'excited', 'subdued')
        # L2 细分类
        assert result.emotion_label in ('joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral')
        # L3 8维向量
        assert len(result.emotion_vector) == 8
        assert all(0.0 <= v <= 1.0 for v in result.emotion_vector)
        # 情感描述
        assert isinstance(result.emotion_text, str)
        assert len(result.emotion_text) > 0
        # 强度
        assert 0.0 <= result.intensity <= 1.0

    def test_l2_to_l1_mapping_anger_high_intensity(self, extractor):
        """L2 → L1 映射：高强度愤怒 → excited"""
        result = extractor.classify("滚！滚出去！混蛋！")
        assert result.emotion_label == 'anger'
        # 高强度愤怒应该是 excited
        if result.intensity >= 0.6:
            assert result.emotion_class == 'excited'

    def test_l2_to_l1_mapping_sadness(self, extractor):
        """L2 → L1 映射：悲伤 → subdued"""
        result = extractor.classify("唉，这一切都结束了……我好难过")
        assert result.emotion_label == 'sadness'
        assert result.emotion_class == 'subdued'

    def test_l2_to_l1_mapping_neutral(self, extractor):
        """L2 → L1 映射：中性 → neutral"""
        result = extractor.classify("他走进了房间。")
        assert result.emotion_label == 'neutral'
        assert result.emotion_class == 'neutral'

    def test_emotion_vector_anger(self, extractor):
        """L3 向量：愤怒维度"""
        result = extractor.classify("滚！混蛋！")
        assert result.emotion_label == 'anger'
        # anger 是第 2 维（索引 1）
        assert result.emotion_vector[1] > 0  # anger 维度应该有值

    def test_emotion_vector_neutral(self, extractor):
        """L3 向量：平静维度"""
        result = extractor.classify("他走进了房间。")
        assert result.emotion_label == 'neutral'
        # calm 是第 8 维（索引 7）
        assert result.emotion_vector[7] == 1.0  # neutral 时 calm 应该是 1.0

    def test_exclamation_density(self, extractor):
        """感叹号密度检测"""
        features = extractor.extract_features("天哪！！！这太疯狂了！！！")
        assert features.exclamation_density > 0.3
        assert features.exclamation_count >= 6

    def test_dirty_word_detection(self, extractor):
        """脏话检测"""
        features = extractor.extract_features("你这个混蛋！滚开！")
        assert features.has_dirty_words is True

    def test_repetition_detection(self, extractor):
        """重复模式检测"""
        features = extractor.extract_features("哈哈哈，真的真的太好了！")
        assert features.has_repetition is True

    def test_imperative_detection(self, extractor):
        """祈使句检测"""
        features = extractor.extract_features("马上准备战斗！立刻集合！")
        assert features.is_imperative is True

    def test_rhetorical_detection(self, extractor):
        """反问句检测"""
        features = extractor.extract_features("难道这不是你的错吗？")
        assert features.is_rhetorical is True

    def test_short_sentences_detection(self, extractor):
        """短句连续检测"""
        features = extractor.extract_features("是谁？在哪？快说！")
        assert features.has_short_sentences is True
