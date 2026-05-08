#!/usr/bin/env python
"""
数据库迁移脚本 v1 → v2
迁移内容：
1. 移除 characters 表的 activity_weight、is_confirmed 字段
2. 删除 sfx_words 表
3. 删除 progress 表
4. 保留核心数据：characters、chapters、sentences
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "novel_tts.db"
BACKUP_PATH = Path(__file__).parent.parent / "novel_tts.db.backup"


def migrate():
    if not DB_PATH.exists():
        print(f"[INFO] 数据库不存在: {DB_PATH}")
        print("[INFO] 跳过迁移，将使用新 schema 创建数据库")
        return True
    
    print(f"[INFO] 开始迁移数据库: {DB_PATH}")
    print(f"[INFO] 创建备份: {BACKUP_PATH}")
    
    # 创建备份
    import shutil
    shutil.copy2(DB_PATH, BACKUP_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 记录迁移前的数据量
        cursor.execute("SELECT COUNT(*) FROM characters")
        chars_before = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chapters")
        chapters_before = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sentences")
        sentences_before = cursor.fetchone()[0]
        
        print(f"[INFO] 迁移前数据量:")
        print(f"  - characters: {chars_before}")
        print(f"  - chapters: {chapters_before}")
        print(f"  - sentences: {sentences_before}")
        
        # 1. 迁移 characters 表（移除 activity_weight、is_confirmed）
        print("[INFO] 迁移 characters 表...")
        cursor.execute("""
            CREATE TABLE characters_new (
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
        
        cursor.execute("""
            INSERT INTO characters_new (id, name, aliases, gender, first_appearance, vector, created_at, updated_at)
            SELECT id, name, aliases, gender, first_appearance, vector, created_at, updated_at
            FROM characters
        """)
        
        cursor.execute("DROP TABLE characters")
        cursor.execute("ALTER TABLE characters_new RENAME TO characters")
        
        # 2. 删除 sfx_words 表
        print("[INFO] 删除 sfx_words 表...")
        cursor.execute("DROP TABLE IF EXISTS sfx_words")
        
        # 3. 删除 progress 表
        print("[INFO] 删除 progress 表...")
        cursor.execute("DROP TABLE IF EXISTS progress")
        
        # 4. 重建索引
        print("[INFO] 重建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentences_chapter ON sentences(chapter_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentences_speaker ON sentences(speaker_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentences_chapter_index ON sentences(chapter_id, sentence_index)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_gender ON characters(gender)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_first_appearance ON characters(first_appearance)")
        
        conn.commit()
        
        # 验证迁移后的数据量
        cursor.execute("SELECT COUNT(*) FROM characters")
        chars_after = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chapters")
        chapters_after = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sentences")
        sentences_after = cursor.fetchone()[0]
        
        print(f"[INFO] 迁移后数据量:")
        print(f"  - characters: {chars_after}")
        print(f"  - chapters: {chapters_after}")
        print(f"  - sentences: {sentences_after}")
        
        # 验证数据无损
        assert chars_before == chars_after, f"characters 数据丢失: {chars_before} → {chars_after}"
        assert chapters_before == chapters_after, f"chapters 数据丢失: {chapters_before} → {chapters_after}"
        assert sentences_before == sentences_after, f"sentences 数据丢失: {sentences_before} → {sentences_after}"
        
        print("[INFO] ✅ 数据迁移成功，数据无损")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 迁移失败: {e}", file=sys.stderr)
        print(f"[ERROR] 备份文件位于: {BACKUP_PATH}")
        print(f"[ERROR] 请从备份恢复后重试")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)