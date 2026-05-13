# -*- coding: utf-8 -*-
"""修复 characters 表的 UNIQUE 约束
从 name UNIQUE 改为 (project_id, name) 联合 UNIQUE
"""
import sqlite3
import sys

db_path = "novel_tts.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("开始迁移：修复 characters 表 UNIQUE 约束...")

# 1. 备份旧数据
cursor.execute("SELECT id, project_id, name, aliases, gender, first_appearance, vector, is_locked, voice_id, color FROM characters")
old_data = cursor.fetchall()
print(f"  旧表中有 {len(old_data)} 条记录")

# 2. 重命名旧表
cursor.execute("ALTER TABLE characters RENAME TO characters_old")
print("  旧表已重命名为 characters_old")

# 3. 创建新表
cursor.execute("""
CREATE TABLE characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]',
    gender TEXT DEFAULT 'unknown' CHECK(gender IN ('male', 'female', 'unknown')),
    first_appearance INTEGER,
    vector BLOB,
    is_locked INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    voice_id TEXT DEFAULT '',
    color TEXT DEFAULT '',
    UNIQUE(project_id, name)
)
""")
print("  新表已创建")

# 4. 迁移数据
for row in old_data:
    cursor.execute(
        """INSERT INTO characters (id, project_id, name, aliases, gender, first_appearance, vector, is_locked, voice_id, color)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        row
    )
print(f"  已迁移 {len(old_data)} 条记录")

# 5. 删除旧表
cursor.execute("DROP TABLE characters_old")
print("  旧表已删除")

# 6. 创建索引
cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_project_name ON characters(project_id, name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_gender ON characters(gender)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_characters_first_appearance ON characters(first_appearance)")
print("  索引已创建")

conn.commit()
print("\n✅ 迁移完成！")

# 验证
cursor.execute("PRAGMA table_info(characters)")
cols = cursor.fetchall()
print("\n新表结构:")
for col in cols:
    print(f"  {col[1]} ({col[2]})")

cursor.execute("SELECT COUNT(*) FROM characters")
count = cursor.fetchone()[0]
print(f"\n新表中的记录数: {count}")

conn.close()
