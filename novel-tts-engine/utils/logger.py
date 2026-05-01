"""
日志系统模块
替代print()，提供可追踪的日志输出
"""
import logging
import sys
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取或创建logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
