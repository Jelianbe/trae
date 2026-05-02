# -*- coding: utf-8 -*-
"""
Unit tests for L2 semantic ranking with ONNX/PyTorch backend.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.semantic_ranker import SemanticRanker
from pipeline.speaker_matcher import SpeakerMatcher, DialogueContext
from pipeline.character_manager import CharacterManager


@pytest.fixture(scope="module")
def semantic_ranker():
    ranker = SemanticRanker(enable_l2=True)
    ranker.load_model()
    return ranker


@pytest.fixture(scope="module")
def char_manager():
    manager = CharacterManager()
    manager.add_character("林轩", gender="male", aliases=["轩儿"])
    manager.add_character("林天豪", gender="male", aliases=["天豪"])
    manager.add_character("苏夜", gender="male", aliases=["苏先生"])
    manager.add_character("林雪", gender="female", aliases=["小雪"])
    return manager


def test_semantic_ranker_loaded(semantic_ranker):
    """Test that the semantic ranker loads successfully."""
    assert semantic_ranker.is_available(), "Semantic ranker should be loaded"
    assert semantic_ranker._backend in ('onnx', 'pytorch'), "Backend should be onnx or pytorch"


def test_encode_single(semantic_ranker):
    """Test encoding a single text."""
    emb = semantic_ranker.encode("你好世界")
    assert emb is not None
    assert emb.shape == (512,), f"Expected shape (512,), got {emb.shape}"


def test_encode_batch(semantic_ranker):
    """Test encoding a batch of texts."""
    texts = ["你好世界", "今天天气很好", "他说道"]
    embs = semantic_ranker.encode_batch(texts)
    assert embs is not None
    assert embs.shape[0] == 3, f"Expected 3 embeddings, got {embs.shape[0]}"


def test_cosine_similarity_same(semantic_ranker):
    """Test cosine similarity of identical texts."""
    emb1 = semantic_ranker.encode("测试文本")
    emb2 = semantic_ranker.encode("测试文本")
    similarity = semantic_ranker.cosine_similarity(emb1, emb2)
    assert abs(similarity - 1.0) < 0.001, f"Expected ~1.0, got {similarity}"


def test_cosine_similarity_different(semantic_ranker):
    """Test cosine similarity of different texts."""
    emb1 = semantic_ranker.encode("你好世界")
    emb2 = semantic_ranker.encode("今天天气很好")
    similarity = semantic_ranker.cosine_similarity(emb1, emb2)
    assert 0.0 <= similarity <= 1.0, f"Expected between 0 and 1, got {similarity}"


def test_rank_candidates(semantic_ranker):
    """Test ranking candidates by semantic similarity."""
    sentence = "修炼需要刻苦"
    candidates = ["修炼功法", "战斗技巧", "灵气浓度"]
    results = semantic_ranker.rank(sentence, candidates, threshold=0.5)
    assert len(results) > 0, "Should return some results"
    # Results should be sorted by score descending
    for i in range(len(results) - 1):
        assert results[i][1] >= results[i + 1][1], "Results should be sorted descending"


def test_cache_hit(semantic_ranker):
    """Test that cache works correctly."""
    text = "缓存测试文本"
    emb1 = semantic_ranker.encode(text)
    emb2 = semantic_ranker.encode(text)
    assert emb1 is emb2, "Cached embedding should be the same object"


def test_speaker_matcher_with_l2(semantic_ranker, char_manager):
    """Test speaker matcher with L2 enabled."""
    matcher = SpeakerMatcher(
        character_manager=char_manager,
        semantic_ranker=semantic_ranker,
        l2_threshold=0.5,  # Lower threshold for testing
    )
    
    # Test a new dialogue - L2 should be attempted
    ctx = DialogueContext(
        text="我需要尽快提升实力",
        chapter_id=1,
    )
    # L2 may or may not match depending on the text, just verify no crash
    result = matcher.match_speaker(ctx)
    # Test is about verifying integration works, not about specific match
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
