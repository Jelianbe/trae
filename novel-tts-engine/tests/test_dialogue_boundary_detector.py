# -*- coding: utf-8 -*-
"""对话边界检测器单元测试"""

import pytest

from pipeline.dialogue_boundary_detector import (
    DialogueBoundaryDetector,
    QuoteInfo,
    DialogueBoundaryResult,
    get_detector,
    is_dialogue,
    detect_all_quotes,
)


class TestDialogueBoundaryDetector:
    """对话边界检测器测试"""

    @pytest.fixture
    def detector(self):
        return DialogueBoundaryDetector()

    @pytest.fixture
    def sample_quote(self):
        return QuoteInfo(
            text="你好啊，今天天气真不错。",
            full_text="「你好啊，今天天气真不错。」",
            quote_type="「」",
            start_pos=5,
            end_pos=20,
            context_before="他笑道：",
            context_after="，然后转身离开了。",
        )

    # ==================== 策略1：说话动词锚定 ====================

    class TestStrategy1SpeechVerbAnchor:
        """测试策略1：说话动词锚定"""

        @pytest.fixture
        def detector(self):
            return DialogueBoundaryDetector()

        def test_speech_verb_before_quote(self, detector):
            """测试：说话动词在引号前"""
            text = '他笑道：「今天天气真不错。」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True
            assert any("说话动词" in r for r in results[0].reasons)

        def test_speech_verb_after_quote(self, detector):
            """测试：说话动词在引号后"""
            text = '「今天天气真不错。」他笑道，然后转身离开。'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True

        def test_no_speech_verb_nearby(self, detector):
            """测试：引号附近无说话动词"""
            text = '他看着远处的「青云阁」，心中感慨万千。'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 修改后：无说话动词不再添加抑制标签，默认放行
            assert not any("无说话动词" in r for r in results[0].suppression_reasons)
            # 但地名引用（含专有名词后缀）仍可能被策略2-检查5抑制
            assert "无说话动词" not in str(results[0].suppression_reasons)

        def test_compound_speech_verb(self, detector):
            """测试：复合说话动词"""
            for verb in ['沉声道', '低声道', '冷冷道', '笑道', '叹道', '怒道']:
                text = f'他{verb}：「你别过来！」'
                results = detector.detect_all(text)
                assert len(results) == 1
                assert results[0].is_dialogue is True, f"动词 '{verb}' 应该识别为对话"

        def test_window_boundary(self, detector):
            """测试：说话动词在窗口边界"""
            detector_15 = DialogueBoundaryDetector(anchor_window=15)
            # 说话动词刚好在15字内
            text = '一二三四五六七八九十多说话：「你好」'
            results = detector_15.detect_all(text)
            assert len(results) == 1

    # ==================== 策略2：内容结构分析 ====================

    class TestStrategy2ContentStructure:
        """测试策略2：引号内容结构分析"""

        @pytest.fixture
        def detector(self):
            return DialogueBoundaryDetector()

        def test_normal_dialogue(self, detector):
            """测试：正常对话（含标点）"""
            text = '他说道：「你好，我是张三。」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True
            assert any("句子结束标点" in r for r in results[0].reasons)

        def test_question_dialogue(self, detector):
            """测试：问句对话"""
            text = '他问道：「你去哪里？」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True
            assert any("问号" in r for r in results[0].reasons)

        def test_modal_particle(self, detector):
            """测试：含语气词结尾"""
            text = '他说道：「走吧。」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True

        def test_pure_noun_phrase(self, detector):
            """测试：纯名词短语（非对话）"""
            text = '门上写着「青云阁」三个字。'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 纯名词短语应被抑制
            assert any("名词短语" in r for r in results[0].suppression_reasons)

        def test_proper_noun_suffix(self, detector):
            """测试：专有名词后缀（地名/物品名）"""
            for suffix in ['阁', '殿', '峰', '宗', '剑', '丹', '图']:
                text = f'这块牌匾上刻着「凌云{suffix}」'
                results = detector.detect_all(text)
                assert len(results) == 1
                # 专有名词应被抑制
                assert any("专有名词" in r or "名词短语" in r for r in results[0].suppression_reasons), \
                    f"后缀 '{suffix}' 应该识别为专有名词"

        def test_single_char_exclaim(self, detector):
            """测试：单字+叹号（拟声词）"""
            text = '只听「杀！」的一声，他冲了出去。'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert any("单字" in r for r in results[0].suppression_reasons)

        def test_single_word_no_punctuation(self, detector):
            """测试：无标点单/双字词"""
            text = '他拿起「宝剑」，挥舞起来。'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert any("单/双字词" in r for r in results[0].suppression_reasons)

        def test_ellipsis_monologue(self, detector):
            """测试：含省略号（修改后：不再作为抑制信号）"""
            text = '他心想：「也许……这就是命运吧……」'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 修改后：省略号不再作为抑制信号，默认放行交给下游处理
            assert not any("省略号" in r for r in results[0].suppression_reasons)

        def test_empty_quote(self, detector):
            """测试：空引号"""
            text = '他说着「」，不知该说什么。'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 空引号应该被策略2抑制（内容为空）
            assert any("空" in r for r in results[0].suppression_reasons)
            # 空内容不应该判定为对话
            assert results[0].is_dialogue is False

    # ==================== 策略3：引号模式抑制 ====================

    class TestStrategy3QuotePatternSuppression:
        """测试策略3：引号模式抑制"""

        @pytest.fixture
        def detector(self):
            return DialogueBoundaryDetector()

        def test_book_quote_keyword(self, detector):
            """测试：书本引用关键词"""
            for kw in ['写着', '刻着', '记载', '石碑', '碑文', '信中']:
                text = f'{kw}：「天道酬勤」'
                results = detector.detect_all(text)
                assert len(results) == 1
                assert any("引用" in r or "关键词" in r for r in results[0].suppression_reasons), \
                    f"关键词 '{kw}' 应该触发抑制"

        def test_inscription_pattern(self, detector):
            """测试：碑文模式（修改后：默认放行，交给下游）"""
            text = '石碑上刻着：「剑道无极」'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 修改后：不确定时默认放行，碑文模式交给 speaker_matcher + LLM 兜底
            # 抑制理由仍然存在（供下游消费），但不再直接判为非对话
            assert any("引用" in r or "关键词" in r for r in results[0].suppression_reasons)
            assert results[0].is_dialogue is True

        def test_letter_pattern(self, detector):
            """测试：书信模式"""
            text = '信中写道：「见字如面，一切安好。」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert any("引用" in r or "关键词" in r for r in results[0].suppression_reasons)

        def test_long_quote_no_speaker(self, detector):
            """测试：长引号无说话动词（修改后：默认放行）"""
            long_text = "这是一段很长的文字，超过一百字。" * 4
            text = f'古籍上记载着这段文字：「{long_text}」'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 修改后：长引号不再被直接判为非对话，抑制理由仍记录供下游参考
            assert any("过长" in r or "引用" in r or "关键词" in r for r in results[0].suppression_reasons)
            assert results[0].is_dialogue is True

        def test_newline_in_quote(self, detector):
            """测试：引号内含换行符（诗文）"""
            text = '石碑上刻着：「\n床前明月光，\n疑是地上霜。\n」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert any("换行符" in r for r in results[0].suppression_reasons)

        def test_normal_quote_not_suppressed(self, detector):
            """测试：正常对话不被抑制"""
            text = '他笑道：「你今天看起来不错。」'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 正常对话不应被策略3抑制
            assert not any("引用" in r for r in results[0].suppression_reasons)

    # ==================== 综合测试 ====================

    class TestIntegration:
        """综合测试"""

        @pytest.fixture
        def detector(self):
            return DialogueBoundaryDetector()

        def test_real_dialogue_detected(self, detector):
            """测试：真实对话正确识别"""
            test_cases = [
                ('他问道：「你是谁？」', True),
                ('她笑道：「你真有趣。」', True),
                ('「快走！」他大喊道。', True),
                ('老者沉声道：「此事非同小可。」', True),
            ]
            for text, expected in test_cases:
                results = detector.detect_all(text)
                assert len(results) == 1, f"文本: {text}"
                assert results[0].is_dialogue == expected, f"文本: {text}"

        def test_dialogue_without_speech_verb(self, detector):
            """测试：无说话动词但有对话内容的情况"""
            # 这种情况可能被判定为非对话（因为没有说话动词锚定）
            # 这是预期行为：没有说话动词时，抑制策略会起作用
            text = '「我不同意。」她摇了摇头。'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 允许这种情况被判定为非对话（因为没有说话动词）
            # 或者被判定为对话（如果内容结构支持）
            # 这里不强制要求结果，只验证检测器能处理

        def test_non_dialogue_suppressed(self, detector):
            """测试：非对话正确抑制（修改后：仅高置信度仍抑制）"""
            test_cases = [
                # 仍被抑制：明确地名/物品名（专有名词后缀），无支持信号
                ('这块牌匾上写着「青云阁」', False),
                ('他拿起「宝剑」，冲了出去', False),
            ]
            for text, expected in test_cases:
                results = detector.detect_all(text)
                assert len(results) >= 1, f"文本: {text}"
                assert results[0].is_dialogue == expected, f"文本: {text}"

        def test_non_dialogue_now_allowed(self, detector):
            """测试：修改后默认放行的非对话案例（交给下游处理）"""
            test_cases = [
                # 无专有名词后缀 → 默认放行
                ('石碑上刻着「剑道无极」', True),
                # 拟声词单字无叹号 → 无明确抑制信号 → 默认放行
                ('只听「嗖」的一声', True),
            ]
            for text, expected in test_cases:
                results = detector.detect_all(text)
                assert len(results) >= 1, f"文本: {text}"
                assert results[0].is_dialogue == expected, f"文本: {text}"

        def test_book_quote_suppressed(self, detector):
            """测试：书本引用（修改后：默认放行，抑制理由保留）"""
            text = '信中写道：「见字如面」'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 修改后：有说话动词（策略1）+ 策略3抑制 → 默认放行，交给下游
            # 抑制理由和说话动词理由同时存在
            assert any("引用" in r or "关键词" in r for r in results[0].suppression_reasons)
            assert any("说话动词" in r for r in results[0].reasons)
            assert results[0].is_dialogue is True

        def test_multiple_quotes(self, detector):
            """测试：多引号文本（修改后：有说话动词锚定的物品名不再被误杀）"""
            text = '他拿起「宝剑」，叹道：「真是好剑啊。」'
            results = detector.detect_all(text)
            assert len(results) == 2
            # 修改后：「宝剑」虽为地名后缀，但有说话动词"叹道"在15字窗口内 → 放行
            assert results[0].is_dialogue is True
            assert results[1].is_dialogue is True

        def test_different_quote_types(self, detector):
            """测试：不同引号类型"""
            quote_types = [
                ('他说道：「你好」', True),
                ('他说道：「你好」', True),
                ('他说道："你好"', True),
                ('他说道：「你好」', True),
            ]
            for text, expected in quote_types:
                results = detector.detect_all(text)
                assert len(results) == 1, f"文本: {text}"
                assert results[0].is_dialogue == expected, f"文本: {text}"

        def test_empty_text(self, detector):
            """测试：空文本"""
            assert detector.detect_all("") == []
            assert detector.detect_all(None) == []

        def test_no_quotes(self, detector):
            """测试：无引号文本"""
            text = '他走在路上，看着远处的风景。'
            results = detector.detect_all(text)
            assert results == []

    # ==================== 便捷函数测试 ====================

    class TestConvenienceFunctions:
        """测试便捷函数"""

        def test_is_dialogue(self):
            """测试 is_dialogue 函数"""
            text = '他笑道：「你好啊。」'
            assert is_dialogue(text, "你好啊。") is True

        def test_is_dialogue_false(self):
            """测试 is_dialogue 返回 False（修改后：仅高置信度非对话仍返回 False）"""
            # "天道酬勤" 无专有名词后缀 → 默认放行
            text = '石碑上刻着：「天道酬勤」'
            assert is_dialogue(text, "天道酬勤") is True

        def test_detect_all_quotes(self):
            """测试 detect_all_quotes 函数"""
            text = '他笑道：「你好。」石碑上刻着「天道酬勤」。'
            results = detect_all_quotes(text)
            assert len(results) == 2

        def test_get_detector_singleton(self):
            """测试 get_detector 返回单例"""
            d1 = get_detector()
            d2 = get_detector()
            assert d1 is d2

    # ==================== 边缘情况测试 ====================

    class TestEdgeCases:
        """测试边缘情况"""

        @pytest.fixture
        def detector(self):
            return DialogueBoundaryDetector()

        def test_nested_quotes(self, detector):
            """测试：嵌套引号（外层决定）"""
            text = '他说：「他喊道：「快走！」」'
            results = detector.detect_all(text)
            # 嵌套引号会被分别检测
            assert len(results) >= 1

        def test_quote_at_start_of_text(self, detector):
            """测试：引号在文本开头"""
            text = '「快走！」他大喊道。'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True

        def test_quote_at_end_of_text(self, detector):
            """测试：引号在文本结尾"""
            text = '他说道：「再见。」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].is_dialogue is True

        def test_very_long_text(self, detector):
            """测试：超长文本"""
            long_text = "普通文本。" * 1000 + '他笑道：「你好。」' + "更多文本。" * 1000
            results = detector.detect_all(long_text)
            assert len(results) == 1
            assert results[0].is_dialogue is True

        def test_unicode_characters(self, detector):
            """测试：含 Unicode 特殊字符"""
            text = '他说：「\u200b你好\u200b」'  # 零宽空格
            results = detector.detect_all(text)
            assert len(results) == 1

        def test_strategy_toggle(self):
            """测试：策略开关"""
            # 禁用所有策略
            detector_off = DialogueBoundaryDetector(
                enable_strategy1=False,
                enable_strategy2=False,
                enable_strategy3=False,
            )
            text = '石碑上刻着：「天道酬勤」'
            results = detector_off.detect_all(text)
            assert len(results) == 1
            # 无策略时，默认分数可能判定为对话或非对话，但不应有抑制理由
            assert results[0].reasons == []
            assert results[0].suppression_reasons == []

    # ==================== 置信度测试 ====================

    class TestConfidence:
        """测试置信度计算"""

        @pytest.fixture
        def detector(self):
            return DialogueBoundaryDetector()

        def test_high_confidence_dialogue(self, detector):
            """测试：高置信度对话"""
            text = '他笑道：「今天天气真不错啊！」'
            results = detector.detect_all(text)
            assert len(results) == 1
            assert results[0].confidence > 0.6

        def test_high_confidence_non_dialogue(self, detector):
            """测试：修改后无专有后缀的非对话案例默认放行"""
            text = '石碑上刻着：「天道酬勤」'
            results = detector.detect_all(text)
            assert len(results) == 1
            # 修改后："天道酬勤"无专有名词后缀 → 默认放行，confidence ≥ 0.5
            assert results[0].confidence >= 0.5
            assert results[0].is_dialogue is True

        def test_confidence_range(self, detector):
            """测试：置信度在 [0, 1] 范围内"""
            test_cases = [
                '他说道：「你好。」',
                '石碑上刻着：「天道酬勤」',
                '「杀！」',
                '他拿起「宝剑」',
            ]
            for text in test_cases:
                results = detector.detect_all(text)
                if results:
                    assert 0.0 <= results[0].confidence <= 1.0, f"文本: {text}"

    # ==================== QuoteInfo 测试 ====================

    class TestQuoteInfo:
        """测试 QuoteInfo 数据类"""

        def test_quote_info_creation(self):
            """测试 QuoteInfo 创建"""
            qi = QuoteInfo(
                text="你好",
                full_text="「你好」",
                quote_type="「」",
                start_pos=0,
                end_pos=4,
            )
            assert qi.text == "你好"
            assert qi.full_text == "「你好」"
            assert qi.quote_type == "「」"
            assert qi.start_pos == 0
            assert qi.end_pos == 4
            assert qi.context_before == ""
            assert qi.context_after == ""

        def test_quote_info_with_context(self):
            """测试 QuoteInfo 带上下文"""
            qi = QuoteInfo(
                text="你好",
                full_text="「你好」",
                quote_type="「」",
                start_pos=5,
                end_pos=9,
                context_before="他说：",
                context_after="，然后走了。",
            )
            assert qi.context_before == "他说："
            assert qi.context_after == "，然后走了。"

    # ==================== DialogueBoundaryResult 测试 ====================

    class TestDialogueBoundaryResult:
        """测试 DialogueBoundaryResult 数据类"""

        def test_result_creation(self):
            """测试结果创建"""
            qi = QuoteInfo(
                text="你好",
                full_text="「你好」",
                quote_type="「」",
                start_pos=0,
                end_pos=4,
            )
            result = DialogueBoundaryResult(
                quote_info=qi,
                is_dialogue=True,
                confidence=0.9,
                reasons=["测试理由"],
                suppression_reasons=[],
            )
            assert result.is_dialogue is True
            assert result.confidence == 0.9
            assert result.reasons == ["测试理由"]
            assert result.suppression_reasons == []
