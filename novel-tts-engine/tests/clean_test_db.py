"""清理测试数据库中积累的临时角色"""
import sqlite3

db_path = r'd:\trae\novel-tts-engine\novel_tts.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM characters')
print(f'Before: {cursor.fetchone()[0]} chars')

# 删除测试项目中的角色
cursor.execute("SELECT name, project_id FROM characters WHERE project_id LIKE 'test%' OR name LIKE '%扎%' OR name LIKE '%穿%' OR name LIKE '%戴%'")
rows = cursor.fetchall()
print(f'测试相关角色: {len(rows)} 条')
for name, pid in rows:
    print(f'  {name} (project: {pid})')

cursor.execute("DELETE FROM characters WHERE project_id LIKE 'test%' OR name LIKE '%扎%' OR name LIKE '%穿%' OR name LIKE '%戴%' OR name LIKE '%马%'")
cursor.execute('SELECT COUNT(*) FROM characters')
print(f'After: {cursor.fetchone()[0]} chars')

conn.commit()
conn.close()
