"""清理生产库中的历史测试角色

来源：R-022 架构重构
功能：清理 novel_tts.db 中非用户手动添加的测试角色
"""
import sqlite3
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
db_path = project_root / 'novel_tts.db'

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("【清理前】角色库状态")
cursor.execute("SELECT COUNT(*) FROM characters")
print(f"  总角色数: {cursor.fetchone()[0]}")

cursor.execute("SELECT name FROM characters WHERE project_id = ''")
empty_project_chars = [row[0] for row in cursor.fetchall()]
print(f"  project_id='' 的角色: {len(empty_project_chars)} 个")
for name in empty_project_chars:
    print(f"    - {name}")

print("\n【清理操作】")
test_names = [
    '赵总监', '李经理', '吴工程师', '孙工', '刘秘书', '张总',
    '亚瑟', '艾琳', '雷恩', '莉莉', '加文',
    '一名黑衣男子', '丫鬟', '中年男人', '人紧紧握着老铁匠', '元帅', '剑客',
    '名浑身是血的斥候', '圣骑士', '在绣花的年轻女子', '她蹲在失忆的少年',
    '少年', '巡逻队长', '年轻士兵', '弟子', '护卫',
    '抬起头对苏夜', '挺燕尾服的老管家', '未知', '林轩', '林雪',
    '病床上的老人', '盯着新来的护卫', '看完弟子',
    "着那块刻着'族长",
    '老丞相', '老人', '老剑客', '老将军', '老总管', '老者', '老铁匠', '老陈',
    '苏夜', '药老', '萧炎', '跪在面前的圣骑士', '轻声',
    '那年轻弟子', '金发骑士', '韩将军', '骑士', '黑甲', '黑甲骑士', '黑袍法师',
]

for name in test_names:
    cursor.execute("DELETE FROM characters WHERE name = ? AND project_id = ''", (name,))
    deleted = cursor.rowcount
    if deleted > 0:
        print(f"  删除: {name}")

print(f"\n【清理后】角色库状态")
cursor.execute("SELECT COUNT(*) FROM characters")
print(f"  总角色数: {cursor.fetchone()[0]}")

conn.commit()
conn.close()
print("\n清理完成")
