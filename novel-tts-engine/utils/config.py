from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DB_PATH = PROJECT_ROOT / "novel_tts.db"

# 流水线冷启动阈值配置
COLD_START_CHARS_THRESHOLD = 3000

MEMORY_LIMIT_GB = 3.0
