"""调试声音指示模式匹配"""
import sys, os
import re, tempfile, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pipeline.character_manager import CharacterManager

P7_CTX_BEFORE = '萧炎接过丹药，仔细端详着。药老的声音在他脑海中响起：'

db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = db_file.name
db_file.close()

cm = CharacterManager(db_path=db_path)
project_id = 'test_12345'

# 添加角色
cm.add_character(name='药老', project_id=project_id, aliases=set(), gender='male')
cm.add_character(name='萧炎', project_id=project_id, aliases=set(), gender='male')

print(f'context_before: {P7_CTX_BEFORE}')
print()

# 获取项目角色
project_chars = cm.get_all_characters(project_id=project_id)
print(f'项目角色: {[c.name for c in project_chars]}')
print()

# 测试声音指示模式
for char in project_chars:
    patterns = [
        rf'{char.name}的声音',
        rf'{char.name}在脑海',
        rf'{char.name}心中',
        rf'{char.name}传音',
    ]
    for pattern in patterns:
        match = re.search(pattern, P7_CTX_BEFORE)
        if match:
            print(f'  ✅ 匹配到: {char.name} (pattern={pattern}, match={match.group()})')
        else:
            print(f'  ❌ 未匹配: {char.name} (pattern={pattern})')

try:
    os.unlink(db_path)
except:
    pass
