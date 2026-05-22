# -*- coding: utf-8 -*-
"""测试角色频率晋升机制

验证：
1. 临时角色注册
2. 频次递增
3. 自动晋升
4. 章节清理
5. 从角色提取器导入
"""

import sys
import os
import json
import tempfile

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.character_manager import CharacterManager

def _create_test_db():
    """创建测试用临时数据库文件"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    return path

def test_basic_operations():
    """测试基本操作"""
    print("=== 测试 1: 基本操作 ===")
    db_path = _create_test_db()
    try:
        cm = CharacterManager(db_path)
        
        # 添加正式角色
        cm.add_character("孙项明", "xiuxian", {"项明"})
        cm.add_character("郭垣", "xiuxian")
        
        chars = cm.get_all_characters("xiuxian")
        print(f"正式角色数: {len(chars)}")
        assert len(chars) == 2, f"期望2个正式角色，实际{len(chars)}"
        print("✅ 正式角色添加成功")
        
        # 添加临时角色
        cm.add_temp_character("管事", "xiuxian")
        temp = cm.get_temp_character("管事")
        assert temp is not None, "临时角色应为管事"
        print(f"临时角色: {temp.name} (mention_count={temp.mention_count})")
        print("✅ 临时角色添加成功")
        
        # 获取所有角色名
        all_names = cm.get_all_character_names("xiuxian")
        print(f"所有角色名: {all_names}")
        assert "孙项明" in all_names
        assert "管事" in all_names
        print("✅ get_all_character_names 正确")
        
        print()
    finally:
        os.unlink(db_path)

def test_frequency_promotion():
    """测试频次晋升"""
    print("=== 测试 2: 频次晋升 ===")
    db_path = _create_test_db()
    try:
        cm = CharacterManager(db_path)
        
        # 注册临时角色
        cm.add_temp_character("神秘人", "xiuxian")
        
        # 递增频次
        for i in range(3):
            cm.increment_frequency("神秘人", "xiuxian")
            temp = cm.get_temp_character("神秘人")
            if temp:
                print(f"  第{i+1}次提及后: mention_count={temp.mention_count} (仍在临时)")
            else:
                print(f"  第{i+1}次提及后: 已晋升为正式角色")
        
        # 检查是否晋升
        temp = cm.get_temp_character("神秘人")
        assert temp is None, "提及3次后应晋升为正式角色"
        
        # 检查正式角色
        chars = cm.get_all_characters("xiuxian")
        names = [c.name for c in chars]
        assert "神秘人" in names, f"神秘人应在正式角色中，当前: {names}"
        print("✅ 频次晋升成功")
        print()
    finally:
        os.unlink(db_path)

def test_cleanup():
    """测试章节清理"""
    print("=== 测试 3: 章节清理 ===")
    db_path = _create_test_db()
    try:
        cm = CharacterManager(db_path)
        
        # 添加临时角色
        cm.add_temp_character("角色A", "xiuxian")
        cm.add_temp_character("角色B", "xiuxian")
        
        # 角色A提及2次（未达标）
        cm.increment_frequency("角色A", "xiuxian")
        cm.increment_frequency("角色A", "xiuxian")
        
        # 角色B提及3次（达标，应晋升）
        cm.increment_frequency("角色B", "xiuxian")
        cm.increment_frequency("角色B", "xiuxian")
        cm.increment_frequency("角色B", "xiuxian")
        
        print(f"清理前: 临时角色数={len(cm.get_all_temp_characters())}")
        print(f"清理前: 正式角色数={len(cm.get_all_characters('xiuxian'))}")
        
        # 清理
        cm.cleanup_temp_characters()
        
        print(f"清理后: 临时角色数={len(cm.get_all_temp_characters())}")
        assert len(cm.get_all_temp_characters()) == 0, "临时角色应全部清理"
        print("✅ 章节清理成功")
        print()
    finally:
        os.unlink(db_path)

def test_import_from_extractor():
    """测试从角色提取器导入"""
    print("=== 测试 4: 从角色提取器导入 ===")
    db_path = _create_test_db()
    try:
        cm = CharacterManager(db_path)
        
        # 模拟角色提取器输出
        role_data = {
            "named_characters": {
                "孙项明": [100, 500, 1000, 1500],  # 4次
                "郭垣": [200, 600],  # 2次
                "新角色": [300],  # 1次
            },
            "descriptive_references": {
                "管事": [150, 700],
                "老者": [250],
            },
            "statistics": {
                "total_quotes": 10,
                "unique_named_characters": 3,
            }
        }
        
        cm.import_from_role_extractor(role_data, "xiuxian")
        
        # 检查导入结果
        all_names = cm.get_all_character_names("xiuxian")
        print(f"导入后角色名: {all_names}")
        
        # 孙项明出现4次 >= 3，应晋升为正式角色
        chars = cm.get_all_characters("xiuxian")
        char_names = [c.name for c in chars]
        assert "孙项明" in char_names, "孙项明应晋升为正式角色"
        print("✅ 孙项明已晋升")
        
        # 郭垣出现2次 < 3，应为临时角色
        temp = cm.get_temp_character("郭垣")
        assert temp is not None, "郭垣应为临时角色"
        assert temp.mention_count == 2, f"郭垣 mention_count 应为2，实际{temp.mention_count}"
        print("✅ 郭垣为临时角色 (mention_count=2)")
        
        # 新角色出现1次 < 3，应为临时角色
        temp = cm.get_temp_character("新角色")
        assert temp is not None, "新角色应为临时角色"
        print("✅ 新角色为临时角色 (mention_count=1)")
        
        print()
    finally:
        os.unlink(db_path)

def test_real_novel_import():
    """测试从修仙传导入"""
    print("=== 测试 5: 从修仙传导入 ===")
    
    # 检查提取结果文件是否存在
    output_path = os.path.join(PROJECT_ROOT, "output", "extracted_roles_v3.json")
    if not os.path.exists(output_path):
        print(f"⚠️ 提取结果文件不存在: {output_path}")
        print("   请先运行: python scripts/extract_roles.py data/novels/修仙传.txt")
        return
    
    with open(output_path, 'r', encoding='utf-8') as f:
        role_data = json.load(f)
    
    db_path = _create_test_db()
    try:
        cm = CharacterManager(db_path)
        cm.import_from_role_extractor(role_data, "xiuxian")
        
        stats = role_data.get("statistics", {})
        print(f"提取统计:")
        print(f"  对话总数: {stats.get('total_quotes', 'N/A')}")
        print(f"  唯一角色名: {stats.get('unique_named_characters', 'N/A')}")
        print(f"  唯一描述性称呼: {stats.get('unique_descriptive_references', 'N/A')}")
        
        # 检查角色库
        chars = cm.get_all_characters("xiuxian")
        temps = cm.get_all_temp_characters()
        
        print(f"\n角色库状态:")
        print(f"  正式角色数: {len(chars)}")
        print(f"  临时角色数: {len(temps)}")
        
        # 检查目标角色
        target_chars = ["孙项明", "郭垣"]
        for target in target_chars:
            is_formal = any(c.name == target for c in chars)
            is_temp = any(t.name == target for t in temps)
            status = "正式" if is_formal else ("临时" if is_temp else "未找到")
            print(f"  {target}: {status}")
        
        print()
        print("✅ 修仙传导入测试完成")
    finally:
        os.unlink(db_path)

def main():
    print("=" * 50)
    print("角色频率晋升机制测试")
    print("=" * 50)
    print()
    
    test_basic_operations()
    test_frequency_promotion()
    test_cleanup()
    test_import_from_extractor()
    test_real_novel_import()
    
    print("=" * 50)
    print("所有测试通过！")
    print("=" * 50)

if __name__ == "__main__":
    main()
