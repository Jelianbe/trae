# -*- coding: utf-8 -*-
"""
引号内容分类器单元测试
"""
import pytest
from pipeline.quotation_classifier import (
    QuotationClassifier, QuotationType, QuotationResult, get_quotation_classifier
)


class TestQuotationClassifier:
    """引号内容分类器测试"""
    
    def test_dialogue_classification(self):
        """测试：角色对话被正确分类为DIALOGUE"""
        text = '萧炎冷笑道："我会回来的。"'
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        assert result.type == QuotationType.DIALOGUE
        assert result.confidence >= 0.8
    
    def test_written_content_classification(self):
        """测试：石碑刻字被正确分类为WRITTEN"""
        text = '石碑上刻着："斗之力，三段！"'
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        assert result.type == QuotationType.WRITTEN
        assert result.confidence >= 0.85
        assert '刻着' in result.reason or '写着' in result.reason
    
    def test_thought_classification(self):
        """测试：内心独白被正确分类为THOUGHT"""
        text = '他心想："我肯定完蛋了。"'
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        assert result.type == QuotationType.THOUGHT
        assert result.confidence >= 0.85
        assert '心想' in result.reason
    
    def test_thought_with_dark_verb(self):
        """测试：暗想类内心独白"""
        text = '萧炎暗忖道："这老者究竟是什么人？"'
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        assert result.type == QuotationType.THOUGHT
        assert result.confidence >= 0.85
    
    def test_written_with_letter(self):
        """测试：书信内容"""
        text = '信中写道："见此信后，速来后山一叙。"'
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        assert result.type == QuotationType.WRITTEN
        assert result.confidence >= 0.85
    
    def test_classify_all(self):
        """测试：批量分类多个引号"""
        text = '''
        萧炎道："你好。"
        石碑上写着："斗之力，三段。"
        他心想："这是怎么回事？"
        '''
        
        classifier = QuotationClassifier()
        results = classifier.classify_all(text)
        
        # 应该有3个引号
        assert len(results) == 3
        
        # 检查分类结果
        types = [r.type for r in results]
        assert QuotationType.DIALOGUE in types
        assert QuotationType.WRITTEN in types
        assert QuotationType.THOUGHT in types
    
    def test_unknown_type(self):
        """测试：无法确定的类型返回UNKNOWN"""
        text = '他说："这是一个测试。"'  # "他说"可能是对话也可能是转述
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        # 应该被识别为DIALOGUE（因为"说"是对话引导词）
        assert result.type in [QuotationType.DIALOGUE, QuotationType.UNKNOWN]
    
    def test_chinese_quotation_marks(self):
        """测试：中文引号"""
        text = '萧炎道："我会回来的。"'
        
        classifier = QuotationClassifier()
        start = text.find('"')
        end = text.find('"', start + 1) + 1
        
        result = classifier.classify(text, start, end)
        
        assert result.type == QuotationType.DIALOGUE
    
    def test_get_quotation_classifier(self):
        """测试：全局实例获取"""
        classifier1 = get_quotation_classifier()
        classifier2 = get_quotation_classifier()
        
        # 应该是同一个实例
        assert classifier1 is classifier2
    
    def test_context_window(self):
        """测试：上下文窗口大小影响"""
        # 小窗口可能捕获不到远处的标识词
        text_short = '刻着："斗之力，三段。"'  # 窗口小，能捕获
        text_long = '很久以前，这块石碑上就刻着几个大字："斗之力，三段。"'  # 窗口大，能捕获
        
        classifier_small = QuotationClassifier(context_window=10)
        classifier_large = QuotationClassifier(context_window=50)
        
        # 小窗口测试
        start = text_short.find('"')
        end = text_short.find('"', start + 1) + 1
        result_small = classifier_small.classify(text_short, start, end)
        
        # 大窗口测试
        start = text_long.find('"')
        end = text_long.find('"', start + 1) + 1
        result_large = classifier_large.classify(text_long, start, end)
        
        # 大窗口应该能正确识别为WRITTEN
        assert result_large.type == QuotationType.WRITTEN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
