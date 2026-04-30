import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

db_path = Path(__file__).parent.parent / "novel_tts.db"

if not db_path.exists():
    from db.db_utils import init_db
    init_db()
    print("数据库初始化完成")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("=== 数据库表 ===")
for t in tables:
    print(f"  - {t[0]}")

for table in tables:
    cursor.execute(f"PRAGMA table_info({table[0]})")
    cols = cursor.fetchall()
    print(f"\n=== {table[0]} 表结构 ===")
    for col in cols:
        print(f"  {col[1]:20s} {col[2]:15s} PK={col[5]}")

conn.close()
