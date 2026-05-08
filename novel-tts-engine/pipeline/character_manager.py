import json
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Optional, List, Set, Dict, Tuple
from dataclasses import dataclass, field

from utils.config import (
    CHARACTER_MIN_CONFIDENCE,
    CONTEXT_HINT_CONFIDENCE_THRESHOLD,
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
                    name TEXT NOT NULL UNIQUE,
                    aliases TEXT,
                    gender TEXT DEFAULT 'unknown' CHECK(gender IN ('male', 'female', 'unknown')),
                    first_appearance INTEGER,
                    vector BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def add_character(self, name: str, aliases: Set[str] = None, 
                      gender: str = "unknown", first_appearance: int = None) -> Character:
        if aliases is None:
            aliases = set()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    """INSERT INTO characters (name, aliases, gender, first_appearance) 
                       VALUES (?, ?, ?, ?)""",
                    (name, json.dumps(list(aliases), ensure_ascii=False), gender, first_appearance)
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
                return self.get_character_by_name(name)
    
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
    
    def get_character_by_name(self, name: str) -> Optional[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, aliases, gender, first_appearance FROM characters WHERE name = ?", (name,))
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
    
    def get_character_by_alias(self, alias: str) -> Optional[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 首先尝试精确匹配 name
            cursor.execute(
                "SELECT id, name, aliases, gender, first_appearance FROM characters WHERE name = ?",
                (alias,)
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
                "SELECT id, name, aliases, gender, first_appearance FROM characters WHERE aliases LIKE '%' || ? || '%' ESCAPE '\\'",
                (escaped_alias,)
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
    
    def get_all_characters(self) -> List[Character]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, aliases, gender, first_appearance FROM characters")
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
    
    def find_or_create(self, name: str, context: str = None, 
                       chapter_id: int = None, min_confidence: float = None) -> Character:
        if min_confidence is None:
            min_confidence = CHARACTER_MIN_CONFIDENCE
        char = self.get_character_by_name(name)
        if char:
            return char
        
        char = self.get_character_by_alias(name)
        if char:
            return char
        
        gender = self.infer_gender(name, context)
        return self.add_character(name, gender=gender, first_appearance=chapter_id)
    
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
    
    def get_character_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM characters")
            return cursor.fetchone()[0]


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
