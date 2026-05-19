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
CHARACTER_MIN_CONFIDENCE: float = float(os.environ.get('CHARACTER_MIN_CONFIDENCE', '0.5'))
CONTEXT_HINT_CONFIDENCE_THRESHOLD: float = float(os.environ.get('CONTEXT_HINT_CONFIDENCE_THRESHOLD', '0.3'))
EMOTION_LOW_SCORE_THRESHOLD: float = float(os.environ.get('EMOTION_LOW_SCORE_THRESHOLD', '0.25'))

# P2-2 近因衰减阈值（2026-05-15）
#
# 用途：连续对话中最近说话人的衰减量，避免粘着效应
# 来源：基于通用对话轮换原则（Turn-taking），刚说完的人不应立即再次说话
# 边界：衰减系数应在 0.10~0.30 范围内，不宜过小（无法纠正排序）或过大（误杀）
# 上限：固定 3 个系数，不应无限制增加
# P0-2 (2026-05-15): 从 0.15/0.10/0.05 提升至 0.25/0.15/0.08，增强排序纠正能力
# 维护者：v7.0 改进方案
RECENCY_DECAY_RECENT: float = float(os.environ.get('RECENCY_DECAY_RECENT', '0.25'))
RECENCY_DECAY_SECOND: float = float(os.environ.get('RECENCY_DECAY_SECOND', '0.15'))
RECENCY_DECAY_OTHER: float = float(os.environ.get('RECENCY_DECAY_OTHER', '0.08'))

# P2-1 角色频率衰减阈值（2026-05-15）
#
# 用途：角色活动度的指数衰减系数和增量
# 来源：基于时间衰减的通用信号衰减原则，长时间未活动的角色权重应逐渐降低
# 边界：
#   - ACTIVITY_DECAY_FACTOR: 应在 0.01~0.10 范围内，不宜过大
#   - ACTIVITY_INCREMENT: 每次活动增加的权重，应在 0.5~2.0 范围内
# 上限：固定 2 个参数
# 维护者：v7.0 改进方案
ACTIVITY_DECAY_FACTOR: float = float(os.environ.get('ACTIVITY_DECAY_FACTOR', '0.05'))
ACTIVITY_INCREMENT: float = float(os.environ.get('ACTIVITY_INCREMENT', '1.0'))

# QUAL-P0-1: dialogue_boundary_detector 锚点窗口（2026-05-15）
#
# 用途：说话动词周围用于提取说话人名和说话方式的字符窗口大小
# 来源：基于对话常用句式长度统计，50 个字符可覆盖绝大多数"XXX说道"模式
# 边界：应在 30~100 范围内，过小可能遗漏上下文，过大会引入噪声
# 上限：固定 1 个参数
# 维护者：R-021 第一阶段修复
SPEECH_VERB_ANCHOR_WINDOW: int = int(os.environ.get('SPEECH_VERB_ANCHOR_WINDOW', '50'))

# H-20260516-10: 角色候选池频次过滤阈值（2026-05-16）
#
# 用途：角色进入候选人池的最低出现频次。频次 < 此值时角色虽在 DB 中
#       但不参与候选人匹配，仅做后台频次堆积。
# 来源：基于长文本 vs 短文本准确率差异分析——临时角色（频次低）污染候选池
# 边界：应在 3~10 范围内，过小（<3）则无效过滤，过大（>10）会遗漏低频主要角色
# 上限：固定 1 个参数
# 更新日期：2026-05-16
# 维护者：H-20260516-10
CHARACTER_ELIGIBLE_MIN_FREQ: int = int(os.environ.get('CHARACTER_ELIGIBLE_MIN_FREQ', '5'))
