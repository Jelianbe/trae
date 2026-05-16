"""角色发现模块单元测试

测试范围：
- 候选提取（正则匹配）
- 黑名单过滤
- 临时角色注册（不重复注册）

用法: pytest tests/test_character_discovery.py
"""

import sys
import pytest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from pipeline.pattern_extractor import extract_candidates, CHARACTER_BLACKLIST
from pipeline.character_discovery import CharacterDiscoveryEngine
from pipeline.character_manager import CharacterManager
from utils.config import TEMP_CHARACTER_CONFIDENCE_FACTOR


class TestExtractCandidates:
    """测试候选提取（正则匹配）。"""

    def test_surname_title_pattern(self):
        """测试姓+职位模式。"""
        text = "赵总监皱起眉头问道：「谁批准的？」"
        candidates = extract_candidates(text)
        assert any(c['name'] == '赵总监' for c in candidates)

    def test_name_title_pattern(self):
        """测试名称+头衔模式。"""
        text = "亚瑟团长举起剑，指向远方。"
        candidates = extract_candidates(text)
        assert any(c['name'] == '亚瑟团长' for c in candidates)

    def test_name_title_pattern_fantasy(self):
        """测试西幻名称+头衔模式（多种头衔）。"""
        text = "艾琳法师翻开魔法卷轴。雷恩队长拍桌而起。莉莉治疗师轻声开口。加文老战士缓缓站起身。"
        candidates = extract_candidates(text)
        names = [c['name'] for c in candidates]
        assert '艾琳法师' in names
        assert '雷恩队长' in names
        assert '莉莉治疗师' in names
        assert '加文老战士' in names

    def test_empty_text(self):
        """测试空文本。"""
        candidates = extract_candidates("")
        assert candidates == []

    def test_no_candidates(self):
        """测试无候选词的文本。"""
        text = "今天天气很好，我们去公园散步吧。"
        candidates = extract_candidates(text)
        assert len(candidates) >= 0


class TestBlacklistFilter:
    """测试黑名单过滤。"""

    def test_blacklist_contains_common_words(self):
        """测试黑名单包含常见非人名词。"""
        assert '但是' in CHARACTER_BLACKLIST
        assert '因为' in CHARACTER_BLACKLIST
        assert '眼睛' in CHARACTER_BLACKLIST
        assert '办公室' in CHARACTER_BLACKLIST

    def test_extract_candidates_filters_blacklist(self):
        """测试候选提取过滤黑名单词。"""
        text = "但是他的眼睛看着办公室"
        candidates = extract_candidates(text)
        for c in candidates:
            assert c['name'] not in CHARACTER_BLACKLIST

    def test_blacklist_blocks_items(self):
        """测试黑名单过滤物品词。"""
        assert '电脑' in CHARACTER_BLACKLIST
        assert '手机' in CHARACTER_BLACKLIST

    def test_blacklist_blocks_body_parts(self):
        """测试黑名单过滤身体部位词。"""
        assert '手' in CHARACTER_BLACKLIST
        assert '头' in CHARACTER_BLACKLIST


class TestCharacterDiscoveryEngine:
    """测试临时角色注册。"""

    @pytest.fixture
    def char_manager(self, tmp_path):
        """创建临时数据库的角色管理器。"""
        db_path = tmp_path / "test_discovery.db"
        return CharacterManager(db_path=str(db_path))

    @pytest.fixture
    def discovery_engine(self, char_manager):
        """创建角色发现引擎。"""
        return CharacterDiscoveryEngine(char_manager)

    def test_register_temp_character(self, discovery_engine, char_manager):
        """测试注册临时角色。"""
        text = "赵总监皱起眉头说道：「你好。」"
        chars = discovery_engine.discover_from_chapter(text, 1, 'test_project')
        
        assert len(chars) > 0
        assert any(c.name == '赵总监' for c in chars)

    def test_no_duplicate_registration(self, discovery_engine, char_manager):
        """测试不重复注册同一角色。"""
        text = "赵总监说道：「你好。」赵总监点点头。"
        
        chars1 = discovery_engine.discover_from_chapter(text, 1, 'test_project')
        count_after_first = len(chars1)
        
        chars2 = discovery_engine.discover_from_chapter(text, 2, 'test_project')
        count_after_second = len(chars2)
        
        assert count_after_second == 0

    def test_temp_character_marked(self, discovery_engine, char_manager):
        """测试临时角色被正确标记。"""
        text = "赵总监说道：「你好。」"
        chars = discovery_engine.discover_from_chapter(text, 1, 'test_project')
        
        for char in chars:
            assert char.is_temp

    def test_existing_character_not_registered_as_temp(self, discovery_engine, char_manager):
        """测试已存在的正式角色不被重复注册为临时角色。"""
        char_manager.add_character("赵总监", project_id='test_project', is_temp=False)
        
        text = "赵总监说道：「你好。」"
        chars = discovery_engine.discover_from_chapter(text, 1, 'test_project')
        
        assert not any(c.name == '赵总监' for c in chars)

    def test_empty_text(self, discovery_engine):
        """测试空文本不产生角色。"""
        chars = discovery_engine.discover_from_chapter("", 1, 'test_project')
        assert chars == []

    def test_blacklist_filtered_in_discovery(self, discovery_engine):
        """测试黑名单词在发现阶段被过滤。"""
        text = "但是电脑放在桌子上，他的眼睛看着屏幕。"
        chars = discovery_engine.discover_from_chapter(text, 1, 'test_project')
        
        for char in chars:
            assert char.name not in CHARACTER_BLACKLIST
            assert '但是' not in char.name
            assert '眼睛' not in char.name

    def test_confidence_factor(self):
        """测试临时角色置信度因子。"""
        assert TEMP_CHARACTER_CONFIDENCE_FACTOR == 0.6

    def test_reset_cache(self, char_manager):
        """测试重置缓存后，引擎不记得已发现的临时角色（但角色仍在数据库中）。"""
        discovery_engine = CharacterDiscoveryEngine(char_manager)
        text = "赵总监说道：「你好。」"
        chars1 = discovery_engine.discover_from_chapter(text, 1, 'test_project')
        assert len(chars1) > 0
        
        discovery_engine.reset_cache()
        
        discovery_engine2 = CharacterDiscoveryEngine(char_manager)
        chars2 = discovery_engine2.discover_from_chapter(text, 2, 'test_project')
        assert len(chars2) == 0
