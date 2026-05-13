# -*- coding: utf-8 -*-
"""追踪 add_character 失败的具体原因"""
import sys
sys.path.insert(0, '.')
import json
import sqlite3
import traceback

from pipeline.character_manager import CharacterManager

print("=" * 60)
print("追踪 add_character 异常")
print("=" * 60)

char_manager = CharacterManager()

# 手动模拟 add_character 的过程
project_id = "test_add_debug"
name = "测试角色"
gender = "unknown"
first_appearance = None
aliases = set()

conn = char_manager._get_connection()
cursor = conn.cursor()

print(f"连接类型: {type(conn)}")
print(f"isolation_level: {conn.isolation_level}")

try:
    sql = """INSERT INTO characters (project_id, name, aliases, gender, first_appearance) 
             VALUES (?, ?, ?, ?, ?)"""
    params = (project_id, name, json.dumps(list(aliases), ensure_ascii=False), gender, first_appearance)
    
    print(f"\nSQL: {sql}")
    print(f"参数: {params}")
    
    cursor.execute(sql, params)
    print(f"execute 成功, lastrowid={cursor.lastrowid}")
    
    conn.commit()
    print("commit 成功")
    
    # 验证
    cursor.execute("SELECT id, name FROM characters WHERE project_id=?", (project_id,))
    row = cursor.fetchone()
    print(f"查询结果: {row}")
    
except Exception as e:
    print(f"\n异常: {type(e).__name__}: {e}")
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()

# 清理
print("\n清理测试数据...")
conn2 = char_manager._get_connection()
conn2.execute("DELETE FROM characters WHERE project_id=?", (project_id,))
conn2.commit()
conn2.close()
print("清理完成")
