#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据库迁移脚本：为 characters 表添加 project_id 字段"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "novel_tts.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查 project_id 列是否存在
    cursor.execute("PRAGMA table_info(characters)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "project_id" not in columns:
        print("Adding project_id column...")
        cursor.execute("ALTER TABLE characters ADD COLUMN project_id TEXT NOT NULL DEFAULT ''")
        conn.commit()
        print("✅ project_id column added")
    else:
        print("✅ project_id column already exists")
    
    # 显示现有角色
    cursor.execute("SELECT project_id, name FROM characters")
    rows = cursor.fetchall()
    print(f"\nTotal characters: {len(rows)}")
    for pid, name in rows:
        print(f"  project_id='{pid}', name='{name}'")
    
    conn.close()

if __name__ == "__main__":
    migrate()
