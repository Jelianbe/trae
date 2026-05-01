import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.character_manager import CharacterManager, Character


class TestCharacterManager:
    
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.remove(db_path)
    
    @pytest.fixture
    def manager(self, temp_db):
        return CharacterManager(temp_db)
    
    def test_add_character(self, manager):
        char = manager.add_character("林轩", gender="male")
        assert char.id is not None
        assert char.name == "林轩"
        assert char.gender == "male"
    
    def test_add_duplicate_character(self, manager):
        char1 = manager.add_character("林轩")
        char2 = manager.add_character("林轩")
        assert char1.id == char2.id
    
    def test_get_character_by_id(self, manager):
        char = manager.add_character("林轩")
        retrieved = manager.get_character_by_id(char.id)
        assert retrieved is not None
        assert retrieved.name == "林轩"
    
    def test_get_character_by_name(self, manager):
        manager.add_character("林轩")
        char = manager.get_character_by_name("林轩")
        assert char is not None
        assert char.name == "林轩"
    
    def test_get_character_by_name_not_found(self, manager):
        char = manager.get_character_by_name("不存在")
        assert char is None
    
    def test_add_and_get_by_alias(self, manager):
        char = manager.add_character("林轩", aliases={"林少爷", "轩儿"})
        assert char is not None
        
        retrieved = manager.get_character_by_alias("林少爷")
        assert retrieved is not None
        assert retrieved.name == "林轩"
        
        retrieved2 = manager.get_character_by_alias("轩儿")
        assert retrieved2 is not None
        assert retrieved2.name == "林轩"
    
    def test_update_character(self, manager):
        char = manager.add_character("林轩")
        success = manager.update_character(char.id, name="林轩轩", gender="male")
        assert success
        
        updated = manager.get_character_by_id(char.id)
        assert updated.name == "林轩轩"
        assert updated.gender == "male"
    
    def test_add_alias(self, manager):
        char = manager.add_character("林轩")
        success = manager.add_alias(char.id, "林少爷")
        assert success
        
        updated = manager.get_character_by_id(char.id)
        assert "林少爷" in updated.aliases
    
    def test_remove_alias(self, manager):
        char = manager.add_character("林轩", aliases={"林少爷", "轩儿"})
        success = manager.remove_alias(char.id, "林少爷")
        assert success
        
        updated = manager.get_character_by_id(char.id)
        assert "林少爷" not in updated.aliases
        assert "轩儿" in updated.aliases
    
    def test_delete_character(self, manager):
        char = manager.add_character("林轩")
        success = manager.delete_character(char.id)
        assert success
        
        deleted = manager.get_character_by_id(char.id)
        assert deleted is None
    
    def test_get_all_characters(self, manager):
        manager.add_character("林轩")
        manager.add_character("小翠")
        manager.add_character("王管家")
        
        chars = manager.get_all_characters()
        assert len(chars) == 3
        names = {c.name for c in chars}
        assert names == {"林轩", "小翠", "王管家"}
    
    def test_infer_gender_male(self, manager):
        assert manager.infer_gender("王管家") == "male"
        assert manager.infer_gender("林少爷") == "male"
        assert manager.infer_gender("李公子") == "male"
    
    def test_infer_gender_female(self, manager):
        assert manager.infer_gender("小翠") == "unknown"
        assert manager.infer_gender("林小姐") == "female"
        assert manager.infer_gender("王夫人") == "female"
    
    def test_infer_gender_from_context(self, manager):
        context = "他缓缓站起身来"
        assert manager.infer_gender("某人", context) == "male"
        
        context = "她轻轻一笑"
        assert manager.infer_gender("某人", context) == "female"
    
    def test_merge_characters(self, manager):
        char1 = manager.add_character("林轩", aliases={"轩儿"})
        char2 = manager.add_character("林少爷", aliases={"小林"})
        
        success = manager.merge_characters(char1.id, char2.id)
        assert success
        
        merged = manager.get_character_by_id(char1.id)
        assert "林少爷" in merged.aliases
        assert "轩儿" in merged.aliases
        assert "小林" in merged.aliases
        
        deleted = manager.get_character_by_id(char2.id)
        assert deleted is None
    
    def test_find_or_create_existing(self, manager):
        char1 = manager.add_character("林轩")
        char2 = manager.find_or_create("林轩")
        assert char1.id == char2.id
    
    def test_find_or_create_by_alias(self, manager):
        manager.add_character("林轩", aliases={"林少爷"})
        char = manager.find_or_create("林少爷")
        assert char.name == "林轩"
    
    def test_find_or_create_new(self, manager):
        char = manager.find_or_create("新角色", context="他走了过来")
        assert char.id is not None
        assert char.name == "新角色"
        assert char.gender == "male"
    
    def test_get_character_count(self, manager):
        assert manager.get_character_count() == 0
        
        manager.add_character("林轩")
        manager.add_character("小翠")
        
        assert manager.get_character_count() == 2


class TestCharacter:
    
    def test_to_dict(self):
        char = Character(id=1, name="林轩", aliases={"轩儿"}, gender="male")
        d = char.to_dict()
        
        assert d["id"] == 1
        assert d["name"] == "林轩"
        assert set(d["aliases"]) == {"轩儿"}
        assert d["gender"] == "male"
    
    def test_from_dict(self):
        d = {"id": 1, "name": "林轩", "aliases": ["轩儿"], "gender": "male"}
        char = Character.from_dict(d)
        
        assert char.id == 1
        assert char.name == "林轩"
        assert char.aliases == {"轩儿"}
        assert char.gender == "male"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
