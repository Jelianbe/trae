import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_utils import (
    init_db, get_connection,
    ChapterManager, SentenceManager,
    SfxWordManager, ProgressManager
)
from pipeline.character_manager import CharacterManager, get_character_manager
from pathlib import Path

TEST_DB_PATH = Path(__file__).parent.parent / "test_novel_tts.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    import db.db_utils as db_module
    monkeypatch.setattr(db_module, 'DB_PATH', TEST_DB_PATH)
    
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    
    init_db()
    yield
    
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


class TestCharacterManager:
    def test_create_character(self):
        manager = get_character_manager()
        char = manager.add_character("张三", {"小张", "老张"})
        assert char is not None
        assert char.id > 0

    def test_get_character_by_id(self):
        manager = get_character_manager()
        char = manager.add_character("李四")
        retrieved = manager.get_character_by_id(char.id)
        assert retrieved is not None
        assert retrieved.name == "李四"

    def test_get_character_by_name(self):
        manager = get_character_manager()
        manager.add_character("王五")
        char = manager.get_character_by_name("王五")
        assert char is not None
        assert char.name == "王五"

    def test_get_all_characters(self):
        manager = get_character_manager()
        manager.add_character("角色A")
        manager.add_character("角色B")
        chars = manager.get_all_characters()
        assert len(chars) >= 2

    def test_update_character(self):
        manager = get_character_manager()
        char = manager.add_character("原名称")
        result = manager.update_character(char.id, name="新名称")
        assert result is True
        retrieved = manager.get_character_by_id(char.id)
        assert retrieved.name == "新名称"

    def test_delete_character(self):
        manager = get_character_manager()
        char = manager.add_character("待删除")
        result = manager.delete_character(char.id)
        assert result is True
        retrieved = manager.get_character_by_id(char.id)
        assert retrieved is None


class TestChapterManager:
    def test_create_chapter(self):
        manager = ChapterManager()
        chapter_id = manager.create("第一章 开端")
        assert chapter_id is not None

    def test_get_chapter_by_id(self):
        manager = ChapterManager()
        chapter_id = manager.create("测试章节")
        chapter = manager.get_by_id(chapter_id)
        assert chapter is not None
        assert chapter['title'] == "测试章节"

    def test_update_chapter_status(self):
        manager = ChapterManager()
        chapter_id = manager.create("状态测试章节")
        result = manager.update_status(chapter_id, "completed")
        assert result is True
        chapter = manager.get_by_id(chapter_id)
        assert chapter['status'] == "completed"


class TestSentenceManager:
    def test_create_sentence(self):
        chapter_mgr = ChapterManager()
        chapter_id = chapter_mgr.create("第一章")
        
        sentence_mgr = SentenceManager()
        sentence_id = sentence_mgr.create(
            chapter_id=chapter_id,
            sentence_index=0,
            content="这是一句测试文本。",
            sentence_type="dialogue",
            emotion="neutral"
        )
        assert sentence_id is not None

    def test_get_sentences_by_chapter(self):
        chapter_mgr = ChapterManager()
        chapter_id = chapter_mgr.create("第二章")
        
        sentence_mgr = SentenceManager()
        sentence_mgr.create(chapter_id, 0, "第一句")
        sentence_mgr.create(chapter_id, 1, "第二句")
        
        sentences = sentence_mgr.get_by_chapter(chapter_id)
        assert len(sentences) == 2

    def test_update_sentence(self):
        chapter_mgr = ChapterManager()
        chapter_id = chapter_mgr.create("第三章")
        
        sentence_mgr = SentenceManager()
        sentence_id = sentence_mgr.create(chapter_id, 0, "原内容")
        
        result = sentence_mgr.update(sentence_id, content="新内容", emotion="happy")
        assert result is True
        
        sentences = sentence_mgr.get_by_chapter(chapter_id)
        assert sentences[0]['content'] == "新内容"
        assert sentences[0]['emotion'] == "happy"
        assert sentences[0]['is_edited'] == 1


class TestSfxWordManager:
    def test_add_sfx_word(self):
        manager = SfxWordManager()
        result = manager.add("哗啦")
        assert result is not None

    def test_get_all_sfx_words(self):
        manager = SfxWordManager()
        manager.add("咚咚")
        manager.add("哗啦")
        words = manager.get_all()
        assert "咚咚" in words
        assert "哗啦" in words

    def test_remove_sfx_word(self):
        manager = SfxWordManager()
        manager.add("测试词")
        result = manager.remove("测试词")
        assert result is True
        words = manager.get_all()
        assert "测试词" not in words


class TestProgressManager:
    def test_create_progress(self):
        chapter_mgr = ChapterManager()
        chapter_id = chapter_mgr.create("进度测试章节")
        
        progress_mgr = ProgressManager()
        progress_id = progress_mgr.create(chapter_id, "nlp_analysis")
        assert progress_id is not None

    def test_update_progress_status(self):
        chapter_mgr = ChapterManager()
        chapter_id = chapter_mgr.create("状态更新章节")
        
        progress_mgr = ProgressManager()
        progress_mgr.create(chapter_id, "dialogue_classify")
        
        result = progress_mgr.update_status(chapter_id, "dialogue_classify", "completed")
        assert result is True

    def test_get_chapter_progress(self):
        chapter_mgr = ChapterManager()
        chapter_id = chapter_mgr.create("进度查询章节")
        
        progress_mgr = ProgressManager()
        progress_mgr.create(chapter_id, "step1")
        progress_mgr.create(chapter_id, "step2")
        
        progress = progress_mgr.get_chapter_progress(chapter_id)
        assert len(progress) == 2


class TestDatabaseSchema:
    def test_tables_exist(self):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]
            
            assert 'characters' in tables
            assert 'chapters' in tables
            assert 'sentences' in tables
            assert 'sfx_words' in tables
            assert 'progress' in tables

    def test_characters_table_schema(self):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(characters)")
            columns = {row['name']: row['type'] for row in cursor.fetchall()}
            
            assert 'id' in columns
            assert 'name' in columns
            assert 'aliases' in columns
            assert 'vector' in columns

    def test_sentences_table_schema(self):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(sentences)")
            columns = {row['name']: row['type'] for row in cursor.fetchall()}
            
            assert 'chapter_id' in columns
            assert 'sentence_index' in columns
            assert 'content' in columns
            assert 'sentence_type' in columns
            assert 'speaker_id' in columns
            assert 'emotion' in columns
            assert 'speed' in columns
            assert 'tone' in columns
            assert 'is_edited' in columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
