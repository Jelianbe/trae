import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.character_manager import CharacterManager, Character
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext, MatchResult


class TestSpeakerMatcher:
    
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except PermissionError:
                pass
    
    @pytest.fixture
    def char_manager(self, temp_db):
        return CharacterManager(temp_db)
    
    @pytest.fixture
    def matcher(self, char_manager):
        return SpeakerMatcher(char_manager)
    
    @pytest.fixture
    def setup_characters(self, char_manager):
        char_manager.add_character("林轩", gender="male", aliases={"轩儿", "林少爷"})
        char_manager.add_character("小翠", gender="female", aliases={"翠儿"})
        char_manager.add_character("王管家", gender="male")
    
    def test_extract_speaker_hint(self, matcher):
        speaker, hint_type = matcher.extract_speaker_hint('林轩说道："你好。"')
        assert speaker == "林轩"
        
        speaker, hint_type = matcher.extract_speaker_hint('"你好。"')
        assert speaker is None
    
    def test_match_by_name(self, matcher, setup_characters):
        result = matcher.match_by_name("林轩")
        assert result is not None
        assert result.character.name == "林轩"
        assert result.confidence == 1.0
        assert result.match_type == "exact_name"
    
    def test_match_by_name_not_found(self, matcher, setup_characters):
        result = matcher.match_by_name("不存在")
        assert result is None
    
    def test_match_by_alias(self, matcher, setup_characters):
        result = matcher.match_by_alias("轩儿")
        assert result is not None
        assert result.character.name == "林轩"
        assert result.confidence == 0.9
        assert result.match_type == "alias"
    
    def test_match_by_pronoun_male(self, matcher, setup_characters):
        context = DialogueContext(text="他走了过来")
        result = matcher.match_by_pronoun("他", context)
        
        assert result is not None
        assert result.character.gender == "male"
    
    def test_match_by_pronoun_female(self, matcher, setup_characters):
        context = DialogueContext(text="她走了过来")
        result = matcher.match_by_pronoun("她", context)
        
        assert result is not None
        assert result.character.gender == "female"
    
    def test_match_speaker_with_hint(self, matcher, setup_characters):
        context = DialogueContext(
            text='林轩说道："你好。"',
            speaker_hint="林轩"
        )
        result = matcher.match_speaker(context)
        
        assert result is not None
        assert result.character.name == "林轩"
    
    def test_match_speaker_with_alias(self, matcher, setup_characters):
        context = DialogueContext(
            text='轩儿说道："你好。"',
            speaker_hint="轩儿"
        )
        result = matcher.match_speaker(context)
        
        assert result is not None
        assert result.character.name == "林轩"
    
    def test_match_speaker_with_pronoun(self, matcher, setup_characters):
        matcher.update_activity(matcher.char_manager.get_character_by_name("林轩").id, "林轩")
        
        context = DialogueContext(
            text="他点了点头",
            speaker_hint="他"
        )
        result = matcher.match_speaker(context)
        
        assert result is not None
        assert result.character.gender == "male"
    
    def test_update_activity(self, matcher, setup_characters):
        char = matcher.char_manager.get_character_by_name("林轩")
        
        matcher.update_activity(char.id, "林轩")
        matcher.update_activity(char.id, "林轩")
        matcher.update_activity(char.id, "林轩")
        
        assert matcher._character_activity[char.id] == 3
    
    def test_reset_activity(self, matcher, setup_characters):
        char = matcher.char_manager.get_character_by_name("林轩")
        matcher.update_activity(char.id, "林轩")
        
        matcher.reset_activity()
        
        assert matcher._character_activity[char.id] == 0
    
    def test_get_speaker_for_sentence(self, matcher, setup_characters):
        char, name = matcher.get_speaker_for_sentence('林轩说道："你好。"', prev_speaker=None)
        
        assert char is not None
        assert char.name == "林轩"
    
    def test_analyze_dialogue(self, matcher, setup_characters):
        text = '林轩说道："你好。"小翠回应道："你好呀。"'
        results = matcher.analyze_dialogue(text)
        
        assert len(results) == 2
        assert results[0][1].name == "林轩"
        assert results[1][1].name == "小翠"


class TestDialogueContext:
    
    def test_default_mentioned_characters(self):
        context = DialogueContext(text="测试文本")
        assert context.mentioned_characters == []
    
    def test_custom_mentioned_characters(self):
        context = DialogueContext(
            text="测试文本",
            mentioned_characters=["林轩", "小翠"]
        )
        assert context.mentioned_characters == ["林轩", "小翠"]


class TestMatchResult:
    
    def test_match_result(self):
        char = Character(id=1, name="林轩", gender="male")
        result = MatchResult(
            character=char,
            confidence=0.9,
            match_type="alias"
        )
        
        assert result.character.name == "林轩"
        assert result.confidence == 0.9
        assert result.match_type == "alias"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
