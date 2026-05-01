"""
全阶段改进验证脚本
验证阶段一、二、三的所有改进
"""
from pathlib import Path

BASE = Path(__file__).parent.parent

def check(name, condition, msg):
    if condition:
        print(f"✅ {msg}")
        return True
    else:
        print(f"❌ {msg}")
        return False

def check_stage1():
    """阶段一：基础架构修复"""
    print("\n阶段一：基础架构修复")
    print("-" * 30)
    
    db_utils = (BASE / 'db' / 'db_utils.py').read_text('utf-8')
    schema = (BASE / 'db' / 'schema.sql').read_text('utf-8')
    char_mgr = (BASE / 'pipeline' / 'character_manager.py').read_text('utf-8')
    migrate = (BASE / 'db' / 'migrate.py').read_text('utf-8')
    
    results = []
    results.append(check("1.1", 'PRAGMA foreign_keys = ON' in db_utils, "SQLite外键约束"))
    results.append(check("1.2", 'PRAGMA journal_mode = WAL' in db_utils, "WAL模式"))
    results.append(check("1.3", 'conn.rollback()' in db_utils, "事务回滚"))
    results.append(check("1.4", 'idx_sentences_chapter' in schema, "数据库索引"))
    results.append(check("1.5", 'ON DELETE CASCADE' in schema, "ON DELETE CASCADE"))
    results.append(check("1.6", 'gender TEXT DEFAULT' in schema, "characters.gender字段"))
    results.append(check("1.7", 'activity_weight REAL DEFAULT' in schema, "characters.activity_weight字段"))
    results.append(check("1.8", 'def migrate' in migrate, "数据库迁移脚本"))
    
    return sum(results)

def check_stage2():
    """阶段二：算法增强"""
    print("\n阶段二：算法增强")
    print("-" * 30)
    
    nlp = (BASE / 'pipeline' / 'nlp_basics.py').read_text('utf-8')
    speaker = (BASE / 'pipeline' / 'speaker_matcher.py').read_text('utf-8')
    char_mgr = (BASE / 'pipeline' / 'character_manager.py').read_text('utf-8')
    sfx = (BASE / 'pipeline' / 'sfx_detector.py').read_text('utf-8')
    
    results = []
    results.append(check("2.1", 'confidence: float = 1.0' in nlp, "Entity置信度字段"))
    results.append(check("2.2", 'confidence=0.95' in nlp, "NER高置信度规则"))
    results.append(check("2.3", 'confidence=0.90' in nlp, "NER中置信度规则"))
    results.append(check("2.4", 'confidence=0.85' in nlp, "NER低置信度规则"))
    results.append(check("2.5", "if next_char in '，,':" in speaker, "说话人呼唤句式过滤"))
    results.append(check("2.6", 'min_confidence: float = 0.5' in char_mgr, "find_or_create置信度过滤"))
    results.append(check("2.7", 'def update_activity_weight' in char_mgr, "活动度持久化"))
    results.append(check("2.8", 'contained = False' in sfx, "SFX嵌套去重优化"))
    
    return sum(results)

def check_stage3():
    """阶段三：性能优化"""
    print("\n阶段三：性能优化")
    print("-" * 30)
    
    sfx = (BASE / 'pipeline' / 'sfx_detector.py').read_text('utf-8')
    nlp = (BASE / 'pipeline' / 'nlp_basics.py').read_text('utf-8')
    logger_mod = (BASE / 'utils' / 'logger.py').read_text('utf-8') if (BASE / 'utils' / 'logger.py').exists() else ""
    
    results = []
    results.append(check("3.1", 'def _build_trie' in sfx, "SFX trie树优化"))
    results.append(check("3.2", 'self._trie' in sfx, "SFX trie数据结构"))
    results.append(check("3.3", 'import logging' in nlp, "NLP模块日志系统"))
    results.append(check("3.4", 'logger = logging.getLogger' in nlp, "NLP logger实例"))
    results.append(check("3.5", 'logger.info' in nlp, "NLP日志调用"))
    results.append(check("3.6", 'import logging' in sfx, "SFX模块日志系统"))
    results.append(check("3.7", 'logger.info' in sfx, "SFX日志调用"))
    results.append(check("3.8", 'def setup_logger' in logger_mod, "日志系统模块"))
    
    return sum(results)

if __name__ == '__main__':
    print("=" * 50)
    print("全阶段改进验证")
    print("=" * 50)
    
    s1 = check_stage1()
    s2 = check_stage2()
    s3 = check_stage3()
    
    total = s1 + s2 + s3
    max_total = 8 + 8 + 8
    
    print("\n" + "=" * 50)
    print(f"阶段一：{s1}/8 通过")
    print(f"阶段二：{s2}/8 通过")
    print(f"阶段三：{s3}/8 通过")
    print(f"总计：{total}/{max_total} 通过 ({total/max_total*100:.0f}%)")
    print("=" * 50)
    
    if total == max_total:
        print("\n🎉 所有改进全部完成！")
