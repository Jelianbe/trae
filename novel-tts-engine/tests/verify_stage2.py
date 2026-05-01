"""
阶段二改进直接验证脚本
通过直接读取文件验证，不依赖hanlp
"""
import re
from pathlib import Path

BASE = Path(__file__).parent.parent

def check_entity_confidence():
    f = BASE / 'pipeline' / 'nlp_basics.py'
    txt = f.read_text('utf-8')
    assert 'confidence: float = 1.0' in txt, "Entity类缺少confidence字段"
    assert 'confidence=0.95' in txt, "缺少高置信度规则(0.95)"
    assert 'confidence=0.90' in txt, "缺少中置信度规则(0.90)"
    assert 'confidence=0.85' in txt, "缺少低置信度规则(0.85)"
    print("✅ Entity置信度字段和分级规则已实现")

def check_sfx_dedup():
    f = BASE / 'pipeline' / 'sfx_detector.py'
    txt = f.read_text('utf-8')
    assert 'sfx_end = sfx.position + len(sfx.text)' in txt, "SFX去重未优化"
    assert 'contained = False' in txt, "SFX去重未优化"
    print("✅ SFX嵌套去重优化已实现")

def check_db_pragmas():
    f = BASE / 'db' / 'db_utils.py'
    txt = f.read_text('utf-8')
    assert 'PRAGMA foreign_keys = ON' in txt, "外键约束未启用"
    assert 'PRAGMA journal_mode = WAL' in txt, "WAL模式未启用"
    assert 'PRAGMA synchronous = NORMAL' in txt, "同步模式未优化"
    assert 'conn.rollback()' in txt, "缺少回滚机制"
    assert 'conn.commit()' in txt, "缺少自动提交"
    print("✅ 数据库外键+WAL+回滚已实现")

def check_schema_indexes():
    f = BASE / 'db' / 'schema.sql'
    txt = f.read_text('utf-8')
    assert 'ON DELETE CASCADE' in txt, "缺少ON DELETE CASCADE"
    assert 'ON DELETE SET NULL' in txt, "缺少ON DELETE SET NULL"
    assert 'UNIQUE(chapter_id, sentence_index)' in txt, "缺少唯一约束"
    assert 'gender TEXT DEFAULT' in txt, "缺少gender字段"
    assert 'activity_weight REAL DEFAULT' in txt, "缺少activity_weight字段"
    assert 'idx_sentences_chapter' in txt, "缺少索引"
    assert 'idx_progress_chapter_step' in txt, "缺少索引"
    print("✅ schema.sql索引+级联+字段已完善")

def check_merge_transaction():
    f = BASE / 'pipeline' / 'character_manager.py'
    txt = f.read_text('utf-8')
    assert 'conn.rollback()' in txt, "merge缺少回滚"
    assert 'except sqlite3.Error' in txt, "缺少异常捕获"
    assert 'min_confidence: float = 0.5' in txt, "find_or_create缺少min_confidence参数"
    print("✅ merge事务回滚+min_confidence已实现")

def check_speaker_calling():
    f = BASE / 'pipeline' / 'speaker_matcher.py'
    txt = f.read_text('utf-8')
    assert "if next_char in '，,':" in txt, "缺少逗号呼唤检测"
    assert "re.match(r'^[您你你我我他她我们你们他们]+'" in txt, "缺少代词检测"
    print("✅ 说话人呼唤句式过滤已实现")

def check_activity_persistence():
    f = BASE / 'pipeline' / 'character_manager.py'
    txt = f.read_text('utf-8')
    assert 'def update_activity_weight' in txt, "缺少update_activity_weight方法"
    assert 'activity_weight * 0.95' in txt, "缺少全局衰减"
    print("✅ 活动度持久化已实现")

if __name__ == '__main__':
    print("=" * 50)
    print("阶段二改进验证")
    print("=" * 50)
    
    checks = [
        check_entity_confidence,
        check_sfx_dedup,
        check_db_pragmas,
        check_schema_indexes,
        check_merge_transaction,
        check_speaker_calling,
        check_activity_persistence,
    ]
    
    passed = 0
    for check in checks:
        try:
            check()
            passed += 1
        except AssertionError as e:
            print(f"❌ {check.__name__}: {e}")
    
    print("=" * 50)
    print(f"通过: {passed}/{len(checks)}")
    print("=" * 50)
