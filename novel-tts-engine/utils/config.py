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

# 结果缓存容量限制（最多缓存多少本书的结果）
MAX_RESULT_CACHE_SIZE: int = int(os.environ.get('MAX_RESULT_CACHE_SIZE', '200'))

# Pipeline 硬编码阈值外置（2026-05-07）
EMOTION_EXTRACT_WINDOW: int = int(os.environ.get('EMOTION_EXTRACT_WINDOW', '20'))
DIALOGUE_EMOTION_CONFIDENCE_THRESHOLD: float = float(os.environ.get('DIALOGUE_EMOTION_CONFIDENCE_THRESHOLD', '0.5'))
NARRATION_EMOTION_CONFIDENCE_THRESHOLD: float = float(os.environ.get('NARRATION_EMOTION_CONFIDENCE_THRESHOLD', '0.4'))
CHARACTER_ACTIVITY_DECAY: float = float(os.environ.get('CHARACTER_ACTIVITY_DECAY', '0.95'))
CHARACTER_MIN_CONFIDENCE: float = float(os.environ.get('CHARACTER_MIN_CONFIDENCE', '0.5'))
CONTEXT_HINT_CONFIDENCE_THRESHOLD: float = float(os.environ.get('CONTEXT_HINT_CONFIDENCE_THRESHOLD', '0.3'))
EMOTION_LOW_SCORE_THRESHOLD: float = float(os.environ.get('EMOTION_LOW_SCORE_THRESHOLD', '0.25'))
