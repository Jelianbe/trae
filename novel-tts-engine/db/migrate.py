"""
数据库迁移脚本 - 添加新字段和索引
用于将旧版数据库升级到新版schema
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "novel_tts.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    # 1. 添加characters表缺失字段（如果不存在）
    try:
        cursor.execute("ALTER TABLE characters ADD COLUMN gender TEXT DEFAULT 'unknown'")
        print("✅ 添加 characters.gender 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⏭️  characters.gender 已存在")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE characters ADD COLUMN first_appearance INTEGER")
        print("✅ 添加 characters.first_appearance 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⏭️  characters.first_appearance 已存在")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE characters ADD COLUMN activity_weight REAL DEFAULT 1.0")
        print("✅ 添加 characters.activity_weight 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⏭️  characters.activity_weight 已存在")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE characters ADD COLUMN is_confirmed INTEGER DEFAULT 1")
        print("✅ 添加 characters.is_confirmed 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⏭️  characters.is_confirmed 已存在")
        else:
            raise
    
    # 2. 添加progress表updated_at字段
    try:
        cursor.execute("ALTER TABLE progress ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("✅ 添加 progress.updated_at 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⏭️  progress.updated_at 已存在")
        else:
            raise
    
    # 3. 添加索引（如果不存在）
    indexes = [
        ("idx_sentences_chapter", "CREATE INDEX IF NOT EXISTS idx_sentences_chapter ON sentences(chapter_id)"),
        ("idx_sentences_speaker", "CREATE INDEX IF NOT EXISTS idx_sentences_speaker ON sentences(speaker_id)"),
        ("idx_sentences_chapter_index", "CREATE INDEX IF NOT EXISTS idx_sentences_chapter_index ON sentences(chapter_id, sentence_index)"),
        ("idx_progress_chapter_step", "CREATE INDEX IF NOT EXISTS idx_progress_chapter_step ON progress(chapter_id, step)"),
        ("idx_characters_gender", "CREATE INDEX IF NOT EXISTS idx_characters_gender ON characters(gender)"),
        ("idx_characters_first_appearance", "CREATE INDEX IF NOT EXISTS idx_characters_first_appearance ON characters(first_appearance)"),
        ("idx_sfx_words_word", "CREATE INDEX IF NOT EXISTS idx_sfx_words_word ON sfx_words(word)"),
    ]
    
    for name, sql in indexes:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{name}'")
        if cursor.fetchone():
            print(f"⏭️  索引 {name} 已存在")
        else:
            cursor.execute(sql)
            print(f"✅ 创建索引 {name}")
    
    conn.commit()
    conn.close()
    print("\n✅ 数据库迁移完成！")

if __name__ == "__main__":
    migrate()
