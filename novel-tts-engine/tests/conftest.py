# -*- coding: utf-8 -*-
"""
Pytest 配置文件

作用：统一处理测试路径配置，确保所有测试文件能正确导入项目模块。
"""
import sys
import os
from pathlib import Path

# 将项目根目录添加到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 设置环境变量（避免测试中使用真实模型文件）
os.environ.setdefault("PYTEST_RUNNING", "1")


import pytest


@pytest.fixture(scope="session")
def nlp_basics():
    """PERF-P0-1: session 级 NLPBasics，避免每个测试类重复 HanLP 冷启动"""
    from pipeline.nlp_basics import NLPBasics
    nlp = NLPBasics()
    return nlp


@pytest.fixture(autouse=True)
def setup_test_environment():
    """自动应用：为每个测试设置干净的环境"""
    yield
    pass


@pytest.fixture
def char_manager():
    """临时数据库隔离 fixture：每个测试函数独立 temp db，互不污染"""
    import tempfile
    from pipeline.character_manager import CharacterManager
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        yield CharacterManager(db_path)
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass


@pytest.fixture
def fantasy_characters(char_manager):
    """注册西幻角色到 char_manager"""
    characters = [
        ('亚瑟', 'male', {'亚瑟团长', '团长'}),
        ('艾琳', 'female', {'艾琳法师'}),
        ('雷恩', 'male', {'雷恩队长', '队长'}),
        ('莉莉', 'female', {'莉莉治疗师', '治疗师'}),
        ('加文', 'male', {'加文老战士', '老战士'}),
    ]
    for name, gender, aliases in characters:
        char_manager.add_character(
            name=name, project_id='fantasy_baseline',
            aliases=aliases, gender=gender
        )
    return char_manager


@pytest.fixture
def speaker_matcher(char_manager, nlp_basics):
    """预配角色库的 SpeakerMatcher（西幻）"""
    from pipeline.speaker_matcher import SpeakerMatcher
    matcher = SpeakerMatcher(character_manager=char_manager)
    matcher._current_project_id = 'fantasy_baseline'
    return matcher
