from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

# 数据库路径（可通过环境变量覆盖）
DB_PATH = Path(os.environ.get("NOVEL_TTS_DB_PATH", str(PROJECT_ROOT / "novel_tts.db")))

# 流水线冷启动阈值配置
COLD_START_CHARS_THRESHOLD = 3000

MEMORY_LIMIT_GB = 3.0

# 输入文本长度限制（10MB）
MAX_INPUT_CHARS = 10 * 1024 * 1024
