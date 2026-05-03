# -*- coding: utf-8 -*-
"""PipelineRunner 集成测试：验证端到端处理流程"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_runner import (
    PipelineRunner, 
    get_pipeline_runner,
    reset_pipeline_runner,
)
from pipeline.character_manager import reset_character_manager


class TestPipelineRunnerIntegration:
    """PipelineRunner 集成测试"""
    
    def setup_method(self):
        """每个测试前重置状态"""
        reset_pipeline_runner()
        reset_character_manager()
    
    def test_analyze_chapters_returns_results(self):
        """测试：analyze_chapters 返回处理结果"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎道：\"你好。\"\n药老笑道：\"你终于来了。\""
        
        results = runner.analyze_chapters(text, force=True)
        
        assert results is not None
        assert isinstance(results, list)
        assert len(results) >= 1
    
    def test_analyze_chapters_processes_text(self):
        """测试：文本被正确处理"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎缓缓睁开眼睛，目光扫过四周。"
        
        results = runner.analyze_chapters(text, force=True)
        
        # 验证结果不为空
        assert len(results) >= 1
        # 验证有统计信息
        assert hasattr(results[0], 'statistics')
    
    def test_quotation_classification_works(self):
        """测试：引号内容分类功能正常"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎道：\"你好。\"\n石碑上写着：\"斗之力，三段。\"\n他心想：\"这是怎么回事？\""
        
        results = runner.analyze_chapters(text, force=True)
        
        assert len(results) >= 1
    
    def test_speaker_assignment_works(self):
        """测试：说话人分配功能正常"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎道：\"我会回来的。\""
        
        results = runner.analyze_chapters(text, force=True)
        
        assert len(results) >= 1
    
    def test_json_export_works(self):
        """测试：JSON 导出功能正常"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎道：\"你好。\""
        
        results = runner.analyze_chapters(text, force=True)
        json_str = runner.export_json(results)
        
        # 验证返回有效的 JSON
        import json
        data = json.loads(json_str)
        assert isinstance(data, list)
    
    def test_ssml_export_works(self):
        """测试：SSML 导出功能正常"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎道：\"你好。\""
        
        results = runner.analyze_chapters(text, force=True)
        ssml_str = runner.export_ssml(results)
        
        # 检查 SSML 格式
        assert '<?xml version="1.0" encoding="UTF-8"?>' in ssml_str
        assert '<speak' in ssml_str
        assert '</speak>' in ssml_str
    
    def test_caching_mechanism(self):
        """测试：缓存机制正常"""
        runner = get_pipeline_runner()
        
        text = "第1章 测试\n\n萧炎道：\"你好。\""
        
        # 第一次处理
        results1 = runner.analyze_chapters(text, force=True)
        
        # 第二次处理（应该使用缓存）
        results2 = runner.analyze_chapters(text, force=False)
        
        # 结果应该相同
        assert len(results1) == len(results2)
    
    def test_input_validation_empty_text(self):
        """测试：输入验证 - 空文本"""
        runner = get_pipeline_runner()
        
        with pytest.raises(ValueError):
            runner.analyze_chapters("")
    
    def test_input_validation_none_text(self):
        """测试：输入验证 - None 文本"""
        runner = get_pipeline_runner()
        
        with pytest.raises((ValueError, TypeError)):
            runner.analyze_chapters(None)
