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
    # 测试前清理（如果需要）
    yield
    # 测试后清理（如果需要）
    pass
