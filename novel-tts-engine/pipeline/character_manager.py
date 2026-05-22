import json
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Optional, List, Set, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from utils.config import (
    CHARACTER_MIN_CONFIDENCE,
    CONTEXT_HINT_CONFIDENCE_THRESHOLD,
    CHARACTER_ELIGIBLE_MIN_FREQ,
    PROMOTION_THRESHOLD,
)
from pathlib import Path
import numpy as np

from utils.config import DB_PATH
logger = logging.getLogger(__name__)


@dataclass
class Character:
    id: Optional[int] = None
    name: str = ""
    aliases: Set[str] = field(default_factory=set)
    vector: Optional[np.ndarray] = None
    gender: str = "unknown"
    first_appearance: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": list(self.aliases),
            "gender": self.gender,
            "first_appearance": self.first_appearance
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Character":
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            aliases=set(data.get("aliases", [])),
            gender=data.get("gender", "unknown"),
            first_appearance=data.get("first_appearance")
        )


@dataclass
class TempCharacterInfo:
    """临时角色信息（仅存在于当前 chapter 内存中）。
    
    用途：SRL/NER/规则发现的陌生角色名，频次达标后晋升为正式角色
    来源：角色频率晋升机制（2026-05-16）
    边界：
      - 不入 SQLite，仅内存存储
      - 章节结束时，mention_count < PROMOTION_THRESHOLD 的角色被清理
      - _frequency 跨章节存活，用于累计频次
    更新日期：2026-05-22
    维护者：角色库开发
    """
    name: str
    mention_count: int = 0
    project_id: str = ''
    gender: str = 'unknown'
    first_seen_at: Optional[datetime] = None


GENDER_HINTS = {
    'male': {'他', '先生', '公子', '少爷', '老爷', '王爷', '将军', '掌门', '师兄', '师弟', '大哥', '二哥', '三哥', '管家'},
    'female': {'她', '小姐', '姑娘', '夫人', '奶奶', '公主', '娘娘', '师姐', '师妹', '大姐', '二姐', '三姐'},
}

TITLE_PATTERNS = {
    '管家', '老爷', '夫人', '少爷', '小姐', '公子', '姑娘',
    '掌柜', '老板', '掌门', '长老', '堂主', '舵主',
    '将军', '大人', '王爷', '皇上', '皇后', '贵妃',
    '师父', '师叔', '师兄', '师弟', '师姐', '师妹',
}

MALE_TITLES = ['师父', '师叔', '师兄', '师弟', '管家', '老爷', '少爷', '公子', '掌柜', '老板', '掌门', '长老', '堂主', '舵主', '将军', '大人', '王爷', '皇上']
FEMALE_TITLES = ['夫人', '小姐', '姑娘', '奶奶', '公主', '娘娘', '贵妃', '皇后', '师姐', '师妹']


class CharacterManager:
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._local = threading.local()
        self._ensure_tables()
        
        # H-20260516-10: 角色频次追踪
        self._frequency_map: Dict[str, Dict[str, int]] = {}
        
        # 角色频率晋升机制：临时角色存储
        self._temp_chars: Dict[str, TempCharacterInfo] = {}
    
    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接的上下文管理器（连接池模式）
        使用线程本地存储确保线程安全
        """
        conn = getattr(self._local, 'connection', None)
        created = False
        
        if conn is None:
            # 每个线程独立连接，确保线程安全
            # timeout=30.0 避免数据库锁竞争时立即失败
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            self._local.connection = conn
            created = True
        
        try:
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
                logger.error(f"数据库操作失败: {e}", exc_info=True)
            raise
        finally:
            if created:
                conn.close()
                self._local.connection = None
    
    @contextmanager
    def _transaction(self):
        """
        事务上下文管理器，确保操作的原子性
        """
        with self._get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"事务执行失败，已回滚: {e}", exc_info=True)
                raise
    
    def _ensure_tables(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL,
                    aliases TEXT,
                    gender TEXT DEFAULT 'unknown' CHECK(gender IN ('male', 'female', 'unknown')),
                    first_appearance INTEGER,
                    vector BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, name)
                )
            """)
            # 为已有数据库添加 project_id 字段（数据迁移）
            try:
                cursor.execute("ALTER TABLE characters ADD COLUMN project_id TEXT NOT NULL DEFAULT ''")
                conn.commit()
                logger.info("已为 characters 表添加 project_id 字段")
            except sqlite3.OperationalError:
                pass  # 字段已存在
            
            # 为已有数据库添加 is_locked 字段（数据迁移）
            try:
                cursor.execute("ALTER TABLE characters ADD COLUMN is_locked INTEGER DEFAULT 0")
                conn.commit()
                logger.info("已为 characters 表添加 is_locked 字段")
            except sqlite3.OperationalError:
                pass  # 字段已存在
    
    def add_character(self, name: str, project_id: str = '', aliases: Set[str] = None, 
                      gender: str = "unknown", first_appearance: int = None) -> Character:
        if aliases is None:
            aliases = set()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    """INSERT INTO characters (project_id, name, aliases, gender, first_appearance) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (project_id, name, json.dumps(list(aliases), ensure_ascii=False), gender, first_appearance)
                )
                conn.commit()
                char_id = cursor.lastrowid
                return Character(
                    id=char_id,
                    name=name,
                    aliases=aliases,
                    gender=gender,
                    first_appearance=first_appearance
                )
            except sqlite3.IntegrityError:
                conn.rollback()
                return self.get_character_by_name(name, project_id)
    
    def get_character_by_id(self, char_id: int) -> Optional[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, aliases, gender, first_appearance FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            
            if row:
                return Character(
                    id=row[0],
                    name=row[1],
                    aliases=set(json.loads(row[2])) if row[2] else set(),
                    gender=row[3] or "unknown",
                    first_appearance=row[4]
                )
            return None
    
    def get_character_by_name(self, name: str, project_id: str = '') -> Optional[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, aliases, gender, first_appearance FROM characters WHERE project_id = ? AND name = ?", (project_id, name))
            row = cursor.fetchone()
            
            if row:
                return Character(
                    id=row[0],
                    name=row[1],
                    aliases=set(json.loads(row[2])) if row[2] else set(),
                    gender=row[3] or "unknown",
                    first_appearance=row[4]
                )
            return None
    
    def _escape_like_pattern(self, pattern: str) -> str:
        """
        转义 LIKE 查询中的特殊字符
        
        SQLite LIKE 查询中，% 和 _ 是通配符，需要转义
        必须先转义反斜杠本身，然后再转义其他特殊字符
        """
        return pattern.replace('\\', r'\\').replace('%', r'\%').replace('_', r'\_')
    
    def get_character_by_alias(self, alias: str, project_id: str = '') -> Optional[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 首先尝试精确匹配 name（按项目过滤）
            cursor.execute(
                "SELECT id, name, aliases, gender, first_appearance FROM characters WHERE project_id = ? AND name = ?",
                (project_id, alias)
            )
            row = cursor.fetchone()
            if row:
                return Character(
                    id=row[0],
                    name=row[1],
                    aliases=set(json.loads(row[2])) if row[2] else set(),
                    gender=row[3] or "unknown",
                    first_appearance=row[4]
                )
            
            # 使用更安全的参数化方式，将通配符与参数完全分离
            # 对特殊字符进行转义，防止SQL注入
            escaped_alias = self._escape_like_pattern(alias)
            cursor.execute(
                "SELECT id, name, aliases, gender, first_appearance FROM characters WHERE project_id = ? AND aliases LIKE '%' || ? || '%' ESCAPE '\\'",
                (project_id, escaped_alias,)
            )
            row = cursor.fetchone()
            
            if row:
                aliases = set(json.loads(row[2])) if row[2] else set()
                if alias in aliases:
                    return Character(
                        id=row[0],
                        name=row[1],
                        aliases=aliases,
                        gender=row[3] or "unknown",
                        first_appearance=row[4]
                    )
            return None
    
    def get_all_characters(self, project_id: str = '') -> List[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, aliases, gender, first_appearance FROM characters WHERE project_id = ?", (project_id,))
            rows = cursor.fetchall()
            
            characters = []
            for row in rows:
                characters.append(Character(
                    id=row[0],
                    name=row[1],
                    aliases=set(json.loads(row[2])) if row[2] else set(),
                    gender=row[3] or "unknown",
                    first_appearance=row[4]
                ))
            return characters
    
    def update_character(self, char_id: int, name: str = None, 
                         aliases: Set[str] = None, gender: str = None) -> bool:
        # 验证 gender 参数
        if gender is not None and gender not in ('male', 'female', 'unknown'):
            raise ValueError(f"Invalid gender: {gender}. Must be 'male', 'female', or 'unknown'")
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            # 使用参数化查询，避免SQL注入
            if name is not None:
                cursor.execute(
                    "UPDATE characters SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (name, char_id)
                )
            
            if aliases is not None:
                cursor.execute(
                    "UPDATE characters SET aliases = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(list(aliases), ensure_ascii=False), char_id)
                )
            
            if gender is not None:
                cursor.execute(
                    "UPDATE characters SET gender = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (gender, char_id)
                )
            
            return cursor.rowcount > 0
    
    def add_alias(self, char_id: int, alias: str) -> bool:
        char = self.get_character_by_id(char_id)
        if not char:
            return False
        
        char.aliases.add(alias)
        return self.update_character(char_id, aliases=char.aliases)
    
    def remove_alias(self, char_id: int, alias: str) -> bool:
        char = self.get_character_by_id(char_id)
        if not char:
            return False
        
        char.aliases.discard(alias)
        return self.update_character(char_id, aliases=char.aliases)
    
    def delete_character(self, char_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM characters WHERE id = ?", (char_id,))
            conn.commit()
            return cursor.rowcount > 0

    # H-20260516-10: 角色频次追踪（2026-05-16）
    #
    # 用途：为角色候选池频次过滤提供后台计数支持
    # 来源：基于长文本 vs 短文本准确率差异分析
    # 边界：纯内存计数器，不持久化到 SQLite，不影响现有 CRUD 逻辑
    # 更新日期：2026-05-16
    # 维护者：H-20260516-10
    #
    # 规则：
    #   - freq == 0 → 预注册角色，始终可用（从未被 increment）
    #   - freq >= 1 → 自动发现的角色，需要 >= min_freq 才能进入候选池
    def increment_frequency(self, name: str, project_id: str = ''):
        if project_id not in self._frequency_map:
            self._frequency_map[project_id] = {}
        self._frequency_map[project_id][name] = self._frequency_map[project_id].get(name, 0) + 1
        
        # 检测临时角色晋升
        if name in self._temp_chars:
            self._temp_chars[name].mention_count += 1
            if self._temp_chars[name].mention_count >= PROMOTION_THRESHOLD:
                self._promote_temp_character(name, project_id)

    def get_frequency(self, name: str, project_id: str = '') -> int:
        return self._frequency_map.get(project_id, {}).get(name, 0)

    def get_eligible_characters(self, project_id: str = '', min_freq: int = None) -> list:
        if min_freq is None:
            min_freq = CHARACTER_ELIGIBLE_MIN_FREQ
        if min_freq <= 0:
            return self.get_all_characters(project_id)
        all_chars = self.get_all_characters(project_id)
        result = []
        for c in all_chars:
            freq = self.get_frequency(c.name, project_id)
            if freq == 0 or freq >= min_freq:
                result.append(c)
        return result

    # ========== 角色频率晋升机制 ==========

    def add_temp_character(self, name: str, project_id: str = '',
                           gender: str = 'unknown') -> bool:
        """注册临时角色（不入 SQLite）。
        
        跨章节继承：如果 _frequency_map 中已有此角色名
        （上一个章节出现过但未达标），作为初始计数。
        """
        if name in self._temp_chars:
            return False
        
        # 检查跨章节频次历史
        prev_count = self._frequency_map.get(project_id, {}).get(name, 0)
        
        self._temp_chars[name] = TempCharacterInfo(
            name=name, project_id=project_id, gender=gender,
            mention_count=prev_count,
            first_seen_at=datetime.now()
        )
        
        # 如果历史频次已达阈值，直接晋升
        if prev_count >= PROMOTION_THRESHOLD:
            self._promote_temp_character(name, project_id)
        
        return True

    def get_temp_character(self, name: str) -> Optional[TempCharacterInfo]:
        return self._temp_chars.get(name)

    def get_all_temp_characters(self) -> List[TempCharacterInfo]:
        return list(self._temp_chars.values())

    def _promote_temp_character(self, name: str, project_id: str):
        """将临时角色晋升为正式角色（写入 SQLite）。"""
        temp_info = self._temp_chars.get(name)
        if not temp_info:
            return None
        
        char = self.add_character(
            name=name,
            project_id=project_id,
            aliases=set(),
            gender=temp_info.gender
        )
        if char:
            logger.info(f"临时角色晋升: {name} (提及{temp_info.mention_count}次)")
            del self._temp_chars[name]
        return char

    def cleanup_temp_characters(self):
        """章节结束时清理不达标的临时角色。
        
        未达标角色记录日志后清除；_frequency_map 保留，跨章节累计。
        """
        below = [
            info for info in self._temp_chars.values()
            if info.mention_count < PROMOTION_THRESHOLD
        ]
        if below:
            logger.debug(f"清理未达标临时角色: "
                         f"{[(t.name, t.mention_count) for t in below]}")
        self._temp_chars.clear()

    def get_all_character_names(self, project_id: str = '') -> Set[str]:
        """返回所有可匹配的角色名（正式 + 临时）。"""
        names = set()
        # 正式角色
        for char in self.get_all_characters(project_id):
            names.add(char.name)
            names.update(char.aliases)
        # 临时角色
        for info in self._temp_chars.values():
            if info.project_id == project_id:
                names.add(info.name)
        return names

    def get_eligible_character_names(self, project_id: str = '') -> Set[str]:
        """返回所有可参与匹配的角色名（过滤低频临时角色）。
        
        正式角色全部返回，临时角色按 mention_count 过滤。
        """
        names = set()
        # 正式角色
        for char in self.get_all_characters(project_id):
            freq = self.get_frequency(char.name, project_id)
            if freq == 0 or freq >= CHARACTER_ELIGIBLE_MIN_FREQ:
                names.add(char.name)
                names.update(char.aliases)
        # 临时角色（仅返回 mention_count >= CHARACTER_ELIGIBLE_MIN_FREQ 的）
        for info in self._temp_chars.values():
            if info.project_id == project_id and info.mention_count >= CHARACTER_ELIGIBLE_MIN_FREQ:
                names.add(info.name)
        return names

    def import_from_role_extractor(self, role_data: Dict, project_id: str = ''):
        """从角色提取器输出导入角色库。
        
        Args:
            role_data: extract_roles.py 输出的 JSON 数据
                {
                    "named_characters": {角色名: [位置列表]},
                    "descriptive_references": {描述性称呼: [位置列表]},
                    ...
                }
            project_id: 项目ID
        """
        imported_count = 0
        promoted_count = 0
        
        # 导入命名角色
        for name, positions in role_data.get("named_characters", {}).items():
            freq = len(positions)
            # 记录频次
            if project_id not in self._frequency_map:
                self._frequency_map[project_id] = {}
            self._frequency_map[project_id][name] = freq
            
            # 添加到临时角色
            self.add_temp_character(name, project_id)
            imported_count += 1
            
            # 检查是否需要晋升
            if freq >= PROMOTION_THRESHOLD:
                self._promote_temp_character(name, project_id)
                promoted_count += 1
        
        # 导入描述性称呼（作为临时角色，不参与匹配）
        for desc, positions in role_data.get("descriptive_references", {}).items():
            if project_id not in self._frequency_map:
                self._frequency_map[project_id] = {}
            self._frequency_map[project_id][desc] = len(positions)
            # 描述性称呼只记录频次，不加入匹配池
            # 后续可以通过 _extract_context_speakers 使用
        
        logger.info(f"角色库导入完成: {imported_count}个角色, {promoted_count}个已晋升")

    def infer_gender(self, name: str, context: str = None) -> str:
        for title in MALE_TITLES:
            if name.endswith(title) or title in name:
                return 'male'
        
        for title in FEMALE_TITLES:
            if name.endswith(title) or title in name:
                return 'female'
        
        if context:
            context_lower = context.lower()
            male_indicators = sum(1 for h in GENDER_HINTS['male'] if h in context_lower)
            female_indicators = sum(1 for h in GENDER_HINTS['female'] if h in context_lower)
            
            if male_indicators > female_indicators:
                return 'male'
            elif female_indicators > male_indicators:
                return 'female'
        
        return 'unknown'
    
    def merge_characters(self, primary_id: int, secondary_id: int) -> bool:
        """
        合并两个角色，将别名合并到主角色，并更新所有相关句子
        使用事务确保数据一致性
        """
        primary = self.get_character_by_id(primary_id)
        secondary = self.get_character_by_id(secondary_id)
        
        if not primary or not secondary:
            return False
        
        merged_aliases = primary.aliases | secondary.aliases | {secondary.name}
        
        with self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE characters SET aliases = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(list(merged_aliases), ensure_ascii=False), primary_id)
            )
            
            try:
                cursor.execute(
                    "UPDATE sentences SET speaker_id = ? WHERE speaker_id = ?",
                    (primary_id, secondary_id)
                )
            except sqlite3.OperationalError as e:
                if "no such table: sentences" not in str(e):
                    raise
                logger.warning("sentences表不存在，跳过更新")
            
            cursor.execute("DELETE FROM characters WHERE id = ?", (secondary_id,))
            
            logger.info(
                f"成功合并角色: ID {secondary_id} ({secondary.name}) -> ID {primary_id} ({primary.name})"
            )
            return True
    
    def find_or_create(self, name: str, project_id: str = '', context: str = None, 
                       chapter_id: int = None, min_confidence: float = None) -> Character:
        if min_confidence is None:
            min_confidence = CHARACTER_MIN_CONFIDENCE
        char = self.get_character_by_name(name, project_id)
        if char:
            return char
        
        char = self.get_character_by_alias(name, project_id)
        if char:
            return char
        
        gender = self.infer_gender(name, context)
        return self.add_character(name, project_id, gender=gender, first_appearance=chapter_id)
    
    def get_characters_by_chapter(self, chapter_id: int) -> List[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT c.id, c.name, c.aliases, c.gender, c.first_appearance
                FROM characters c
                JOIN sentences s ON s.speaker_id = c.id
                WHERE s.chapter_id = ?
            """, (chapter_id,))
            rows = cursor.fetchall()
            
            characters = []
            for row in rows:
                characters.append(Character(
                    id=row[0],
                    name=row[1],
                    aliases=set(json.loads(row[2])) if row[2] else set(),
                    gender=row[3] or "unknown",
                    first_appearance=row[4]
                ))
            return characters
    
    def get_character_count(self, project_id: str = '') -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM characters WHERE project_id = ?", (project_id,))
            return cursor.fetchone()[0]
    
    def lock_character(self, char_id: int, project_id: str = '') -> bool:
        """锁定角色
        
        用途：用户手动锁定关键角色，锁定后在旁白匹配中获得最高优先级
        来源：说话人识别改进方案 P1
        边界：
          - 只有属于指定项目的角色才能被锁定
          - 锁定状态存储在 is_locked 字段
        更新日期：2026-05-09
        维护者：说话人识别改进方案
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE characters SET is_locked = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND project_id = ?",
                (char_id, project_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def unlock_character(self, char_id: int, project_id: str = '') -> bool:
        """解锁角色
        
        用途：取消角色的锁定状态
        来源：说话人识别改进方案 P1
        边界：
          - 只有属于指定项目的角色才能被解锁
        更新日期：2026-05-09
        维护者：说话人识别改进方案
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE characters SET is_locked = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND project_id = ?",
                (char_id, project_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_locked_characters(self, project_id: str = '') -> List[Character]:
        """获取所有锁定角色
        
        用途：返回当前项目所有锁定角色列表
        来源：说话人识别改进方案 P1
        边界：
          - 只返回 is_locked=1 的角色
          - 按项目过滤
        更新日期：2026-05-09
        维护者：说话人识别改进方案
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, aliases, gender, first_appearance FROM characters "
                "WHERE project_id = ? AND is_locked = 1",
                (project_id,)
            )
            rows = cursor.fetchall()
            
            characters = []
            for row in rows:
                characters.append(Character(
                    id=row[0],
                    name=row[1],
                    aliases=set(json.loads(row[2])) if row[2] else set(),
                    gender=row[3] or "unknown",
                    first_appearance=row[4]
                ))
            return characters

    def build_candidate_list(
        self, project_id: str, chapter_cache=None,
        max_candidates: int = 6
    ) -> list:
        """构建说话人候选人列表，按活跃度排序。

        用途：为 LLM 兜底提供候选人列表。
        顺序：已确认角色优先，活跃度高的在前。

        Args:
            project_id: 项目 ID
            chapter_cache: 可选章节缓存
            max_candidates: 最大候选人数量

        Returns:
            Character 列表
        """
        all_chars = self.get_all_characters(project_id)
        all_chars.sort(
                key=lambda c: (
                    0 if c.id and c.id > 0 else 1,
                    -(getattr(c, 'first_appearance', 0) or 0)
                )
            )
        return all_chars[:max_candidates]


class ChapterRoleCache:
    """章节级角色缓存（用于 LLM 候选人列表构建）。

    用途：在章节处理过程中缓存角色信息，避免重复数据库查询。
    设计：简单的 dict 包装，按章节 ID 维护角色列表。
    """

    def __init__(self):
        self._cache: Dict[int, list] = {}

    def get(self, chapter_id: int, default=None):
        return self._cache.get(chapter_id, default)

    def set(self, chapter_id: int, characters: list):
        self._cache[chapter_id] = characters

    def clear(self):
        self._cache.clear()


_character_manager: Optional[CharacterManager] = None
_character_manager_lock = threading.Lock()


def get_character_manager(db_path: str = None) -> CharacterManager:
    """获取或创建全局角色管理器实例（线程安全，双重检查锁）"""
    global _character_manager
    if _character_manager is None:
        with _character_manager_lock:
            if _character_manager is None:
                _character_manager = CharacterManager(db_path)
    return _character_manager


def reset_character_manager() -> None:
    """重置全局角色管理器实例，用于测试或重新初始化"""
    global _character_manager
    with _character_manager_lock:
        _character_manager = None
