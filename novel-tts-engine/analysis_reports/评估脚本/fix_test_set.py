"""修正测试集标注错误并重新生成 gt_context_mapping.json

修正项目:
  C-1: 移除斗破10条（GT设计问题，同一长段落拆成10条）
  C-2: 修正non_dialogue标签（B2/B4/B5移至dialogue）
  C-3: 修正内心独白标注（GT-修仙-010/055期望改为未知）
  C-4: 修正GT-都市-018（博士→男子）
"""

import json
import os
import sys

GT_MAPPING_FILE = os.path.join(os.path.dirname(__file__), 'gt_context_mapping.json')
TEST_DATA_FILE = os.path.join(os.path.dirname(__file__), 'test_data_unified.py')

def fix_gt_mapping():
    """修正 gt_context_mapping.json"""
    print("=" * 50)
    print("C-1~C-4: 修正测试集标注")
    print("=" * 50)

    with open(GT_MAPPING_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data)
    print(f"\n原始条目数: {original_count}")

    # C-1: 移除斗破10条
    doupo_entries = [d for d in data if d.get('gt_id', '').startswith('GT-玄幻(斗破)-')]
    print(f"\nC-1: 移除斗破10条 ({len(doupo_entries)} 条)")
    data = [d for d in data if not d.get('gt_id', '').startswith('GT-玄幻(斗破)-')]

    # C-3: 修正内心独白标注（GT-修仙-010/055期望改为未知）
    monologue_fixes = []
    for d in data:
        if d.get('gt_id') in ('GT-修仙-010', 'GT-修仙-055'):
            old_speaker = d.get('speaker')
            d['speaker'] = '未知'
            monologue_fixes.append((d['gt_id'], old_speaker))
            print(f"\nC-3: 修正 {d['gt_id']}: {old_speaker} → 未知")

    # C-4: 修正GT-都市-018（博士→男子）
    for d in data:
        if d.get('gt_id') == 'GT-都市异能-018':
            old_speaker = d.get('speaker')
            d['speaker'] = '男子'
            print(f"\nC-4: 修正 {d['gt_id']}: {old_speaker} → 男子")

    # 保存修正后的文件
    new_count = len(data)
    print(f"\n修正后条目数: {new_count} (移除了 {original_count - new_count} 条)")

    # 备份原始文件
    backup_file = GT_MAPPING_FILE.replace('.json', '_backup_20260513.json')
    if not os.path.exists(backup_file):
        import shutil
        shutil.copy2(GT_MAPPING_FILE, backup_file)
        print(f"\n已备份原始文件: {backup_file}")

    with open(GT_MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已保存修正后的文件: {GT_MAPPING_FILE}")

    # 统计修正后的分布
    style_counts = {}
    for d in data:
        style = d.get('style', 'unknown')
        style_counts[style] = style_counts.get(style, 0) + 1

    print("\n修正后的风格分布:")
    for style, count in sorted(style_counts.items()):
        print(f"  {style}: {count}")

    return data

def fix_test_data_unified():
    """修正 test_data_unified.py 中的 B2/B4/B5 类别"""
    print("\n" + "=" * 50)
    print("C-2: 修正non_dialogue标签（B2/B4/B5移至dialogue）")
    print("=" * 50)

    with open(TEST_DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 备份原始文件
    backup_file = TEST_DATA_FILE.replace('.py', '_backup_20260513.py')
    if not os.path.exists(backup_file):
        import shutil
        shutil.copy2(TEST_DATA_FILE, backup_file)
        print(f"已备份原始文件: {backup_file}")

    # 替换 B2-混, B4-混, B5-混 的 category 从 non_dialogue 改为 dialogue
    replacements = [
        ('"id": "B2-混",\n    "source": "new",\n    "category": "non_dialogue"',
         '"id": "B2-混",\n    "source": "new",\n    "category": "dialogue"'),
        ('"id": "B4-混",\n    "source": "new",\n    "category": "non_dialogue"',
         '"id": "B4-混",\n    "source": "new",\n    "category": "dialogue"'),
        ('"id": "B5-混",\n    "source": "new",\n    "category": "non_dialogue"',
         '"id": "B5-混",\n    "source": "new",\n    "category": "dialogue"'),
    ]

    for old, new in replacements:
        search_key = '"id": "'
        if search_key in old:
            case_id = old.split(search_key)[1].split('",')[0]
        else:
            case_id = 'unknown'
        if old in content:
            content = content.replace(old, new, 1)
            print(f"  已修正: {case_id}: non_dialogue → dialogue")
        else:
            print(f"  ⚠ 未找到: {old[:30]}...")

    with open(TEST_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"已保存修正后的文件: {TEST_DATA_FILE}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    fix_gt_mapping()
    fix_test_data_unified()
    print("\n✅ 所有修正完成！可以运行 run_regression.py 重新测试。")
