import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "novel_tts.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -2000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, 'r', encoding='utf-8') as f:
            cursor.executescript(f.read())
        conn.commit()


class CharacterManager:
    def create(self, name: str, aliases: List[str] = None, vector: bytes = None) -> int:
        with get_connection() as conn:
            cursor = conn.cursor()
            aliases_json = json.dumps(aliases, ensure_ascii=False) if aliases else None
            cursor.execute(
                "INSERT INTO characters (name, aliases, vector) VALUES (?, ?, ?)",
                (name, aliases_json, vector)
            )
            conn.commit()
            return cursor.lastrowid

    def get_by_id(self, character_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all(self) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def update(self, character_id: int, **kwargs) -> bool:
        allowed_fields = {'name', 'aliases', 'vector'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        
        if 'aliases' in updates and isinstance(updates['aliases'], list):
            updates['aliases'] = json.dumps(updates['aliases'], ensure_ascii=False)
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [character_id]
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE characters SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, character_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM characters WHERE id = ?", (character_id,))
            conn.commit()
            return cursor.rowcount > 0


class ChapterManager:
    def create(self, title: str, content: str = None) -> int:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chapters (title, content) VALUES (?, ?)",
                (title, content)
            )
            conn.commit()
            return cursor.lastrowid

    def get_by_id(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all(self) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chapters ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]

    def update_status(self, chapter_id: int, status: str) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chapters SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, chapter_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, chapter_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
            conn.commit()
            return cursor.rowcount > 0


class SentenceManager:
    def create(self, chapter_id: int, sentence_index: int, content: str, **kwargs) -> int:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sentences 
                   (chapter_id, sentence_index, content, sentence_type, speaker_id, emotion, speed, tone)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (chapter_id, sentence_index, content, 
                 kwargs.get('sentence_type'), kwargs.get('speaker_id'),
                 kwargs.get('emotion'), kwargs.get('speed', 1.0), kwargs.get('tone'))
            )
            conn.commit()
            return cursor.lastrowid

    def get_by_chapter(self, chapter_id: int) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sentences WHERE chapter_id = ? ORDER BY sentence_index",
                (chapter_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update(self, sentence_id: int, **kwargs) -> bool:
        allowed_fields = {'content', 'sentence_type', 'speaker_id', 'emotion', 'speed', 'tone'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [sentence_id]
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE sentences SET {set_clause}, is_edited = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_by_chapter(self, chapter_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sentences WHERE chapter_id = ?", (chapter_id,))
            conn.commit()
            return cursor.rowcount > 0


class SfxWordManager:
    def add(self, word: str) -> int:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO sfx_words (word) VALUES (?)", (word,))
            conn.commit()
            return cursor.lastrowid

    def get_all(self) -> List[str]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM sfx_words ORDER BY word")
            return [row['word'] for row in cursor.fetchall()]

    def remove(self, word: str) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sfx_words WHERE word = ?", (word,))
            conn.commit()
            return cursor.rowcount > 0


class ProgressManager:
    def create(self, chapter_id: int, step: str) -> int:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO progress (chapter_id, step) VALUES (?, ?)",
                (chapter_id, step)
            )
            conn.commit()
            return cursor.lastrowid

    def update_status(self, chapter_id: int, step: str, status: str) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE progress SET status = ? 
                   WHERE chapter_id = ? AND step = ?""",
                (status, chapter_id, step)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_chapter_progress(self, chapter_id: int) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM progress WHERE chapter_id = ? ORDER BY id",
                (chapter_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_progress(self) -> Dict[int, Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM progress ORDER BY chapter_id, id")
            result = {}
            for row in cursor.fetchall():
                chapter_id = row['chapter_id']
                if chapter_id not in result:
                    result[chapter_id] = {}
                result[chapter_id][row['step']] = row['status']
            return result
