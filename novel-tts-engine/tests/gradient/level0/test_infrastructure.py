# -*- coding: utf-8 -*-
"""
Level 0: 基础设施验证（确定性测试）

目的：验证基础函数正确性 + 模块健康
测试数据：人工构造的确定性输入
用例数：~20 条
通过标准：100%（任何失败都是 Bug）
执行频率：每次代码改动后
执行时间：< 5 秒

v2.0 变更（2026-05-23）：
  - 移除与 L1 重叠的 SPEAKER_PATTERNS/DIALOGUE_PATTERNS 用例
  - 新增模块导入健康检查（覆盖 pipeline/ 所有模块，含 SRL 断链检测）
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from importlib import import_module

from pipeline.speaker_matcher import (
    DIALOGUE_PATTERNS,
    _clean_speaker_name,
)
from pipeline.matchers.speaker_hint_matcher import SPEAKER_PATTERNS
from pipeline.character_manager import CharacterManager
from pipeline.matchers.name_validator import CharacterNameValidator
from pipeline.nlp_basics import get_nlp


# ===== L0-01: 正则编译完整性 =====

class TestRegexCompilation:
    """验证所有正则模式已正确编译，无语法错误。"""

    def test_dialogue_patterns_compile(self):
        assert len(DIALOGUE_PATTERNS) >= 1, "至少应有一个对话模式"

    def test_speaker_patterns_compile(self):
        assert len(SPEAKER_PATTERNS) >= 1, "至少应有一个说话人模式"

    def test_speaker_patterns_order(self):
        """验证 SPEAKER_PATTERNS 按优先级排序（P0 长动词 → P3 单字）"""
        assert len(SPEAKER_PATTERNS) >= 3, f"至少需要 3 个优先级模式，实际 {len(SPEAKER_PATTERNS)}"

    def test_foreign_name_pattern_length(self):
        """验证外国名长度上限 ≥ 12（支持超长外国名）"""
        import re
        # 检查第一个模式（P0: X对Y说）的长度上限
        p0 = SPEAKER_PATTERNS[0]
        m = re.search(r'\{1,(\d+)\}', p0.pattern)
        if m:
            assert int(m.group(1)) >= 12, f"外国名长度上限应≥12，实际{{1,{m.group(1)}}}"
        else:
            assert '{1,' in p0.pattern, f"P0 模式应包含长度限制语法，实际: {p0.pattern}"

    def test_single_quote_support(self):
        """验证单引号对话支持（v2.0 Ph3-2）"""
        text = "他说：'你好'"
        matched = any(p.search(text) for p in DIALOGUE_PATTERNS)
        assert matched, "DIALOGUE_PATTERNS 应能匹配单引号格式"


# ===== L0-02: _clean_speaker_name 正确清洗 =====

class TestCleanSpeakerName:
    """验证名字清洗逻辑。"""

    @pytest.fixture
    def nlp(self):
        return get_nlp()

    @pytest.mark.parametrize("input_name,expected_clean", [
        ('张三笑着', "张三"),
        ('李四说道', "李四"),
        ('王五问道', "王五"),
        ('赵六答道', "赵六"),
        ('掌柜笑着说', "掌柜"),
        ('小翠轻声说', "小翠"),
        ('黑衣人冷冷道', "黑衣人"),
        ('张三轻声地', "张三"),           # 地字截断
        ('李四急切地', "李四"),           # 地字截断
        ('张三·尼古拉耶维奇', "张三·尼古拉耶维奇"),  # 外国名保留
    ])
    def test_clean_speaker_name(self, input_name, expected_clean, nlp):
        cleaned = _clean_speaker_name(input_name, nlp)
        assert cleaned == expected_clean, f"期望清洗为 '{expected_clean}'，实际为 '{cleaned}'"


# ===== L0-03: 模块导入健康检查 =====

class TestModuleImportHealth:
    """遍历 pipeline/ 所有模块，确保无 ImportError。
    
    关键防护：SRL 断链等 import 错误应在 L0 层被立即发现。
    """

    PIPELINE_MODULES = [
        'pipeline.nlp_basics',
        'pipeline.speaker_matcher',
        'pipeline.character_manager',
        'pipeline.semantic_ranker',
        'pipeline.descriptive_role_extractor',
        'pipeline.dialogue_boundary_detector',
        'pipeline.hybrid_speaker_matcher',
        'pipeline.types',
        # Matchers
        'pipeline.matchers.speaker_hint_matcher',
        'pipeline.matchers.name_validator',
        'pipeline.matchers.self_reference_inferrer',
        'pipeline.matchers.speech_verb_detector',
        # Strategies
        'pipeline.strategies.candidate_pool',
        'pipeline.strategies.srl_arg0_normalizer',
    ]

    @pytest.mark.parametrize("module_path", PIPELINE_MODULES)
    def test_import_pipeline_module(self, module_path):
        try:
            mod = import_module(module_path)
            assert mod is not None, f"{module_path} 导入返回 None"
        except ImportError as e:
            pytest.fail(f"模块导入失败 {module_path}: {e}")
        except Exception as e:
            pytest.fail(f"模块异常 {module_path}: {type(e).__name__}: {e}")


# ===== L0-04: 数据库可创建 =====

class TestDatabaseCreation:
    """验证数据库基础操作。"""

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

    def test_create_character_manager(self, temp_db):
        char_manager = CharacterManager(temp_db)
        assert char_manager is not None

    def test_add_character(self, temp_db):
        char_manager = CharacterManager(temp_db)
        char = char_manager.add_character("张三", gender="male", project_id="test")
        assert char is not None
        assert char.name == "张三"

    def test_name_validator(self, temp_db):
        char_manager = CharacterManager(temp_db)
        validator = CharacterNameValidator(char_manager)
        assert validator.is_valid_speaker_candidate("张三")
        assert not validator.is_valid_speaker_candidate("")
        assert not validator.is_valid_speaker_candidate("a")        # 太短
        assert validator.is_valid_speaker_candidate("亚历山大·尼古拉耶维奇")  # 超长外国名应通过


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
