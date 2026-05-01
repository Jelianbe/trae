# -*- coding: utf-8 -*-
"""L2 Semantic Ranker Unit Tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from pipeline.semantic_ranker import SemanticRanker, SemanticCache, get_semantic_ranker


class TestSemanticCache:
    def test_cache_put_get(self):
        cache = SemanticCache(max_size=5)
        arr = np.array([1.0, 2.0, 3.0])
        cache.put("test", arr)
        result = cache.get("test")
        assert result is not None
        assert np.allclose(result, arr)

    def test_cache_missing(self):
        cache = SemanticCache(max_size=5)
        assert cache.get("nonexistent") is None

    def test_cache_max_size(self):
        cache = SemanticCache(max_size=3)
        for i in range(5):
            cache.put(f"key{i}", np.array([i]))
        assert len(cache) == 3
        # Oldest key should be evicted
        assert cache.get("key0") is None

    def test_cache_clear(self):
        cache = SemanticCache(max_size=5)
        cache.put("a", np.array([1]))
        cache.put("b", np.array([2]))
        cache.clear()
        assert len(cache) == 0

    def test_thread_safety(self):
        cache = SemanticCache(max_size=100)
        import threading
        def add_items(start, count):
            for i in range(start, start + count):
                cache.put(f"key{i}", np.array([i]))
        threads = [threading.Thread(target=add_items, args=(i*10, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(cache) == 50


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert abs(SemanticRanker.cosine_similarity(a, b) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert abs(SemanticRanker.cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert abs(SemanticRanker.cosine_similarity(a, b) + 1.0) < 1e-6

    def test_none_vector(self):
        a = np.array([1.0, 0.0])
        assert SemanticRanker.cosine_similarity(a, None) == 0.0
        assert SemanticRanker.cosine_similarity(None, a) == 0.0

    def test_zero_vector(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert SemanticRanker.cosine_similarity(a, b) == 0.0


class TestSemanticRanker:
    def test_init_default(self):
        ranker = SemanticRanker()
        assert ranker.model_name == "BAAI/bge-small-zh-v1.5"
        assert not ranker.is_available()

    def test_init_custom_model(self):
        ranker = SemanticRanker(model_name="custom-model")
        assert ranker.model_name == "custom-model"

    def test_init_custom_cache(self):
        ranker = SemanticRanker(cache_size=500)
        assert ranker._cache.max_size == 500

    def test_load_local_model(self):
        ranker = SemanticRanker()
        ranker.load_model()
        assert ranker.is_available()

    def test_load_model_once(self):
        ranker = SemanticRanker()
        ranker.load_model()
        first_model = ranker._model
        ranker.load_model()
        assert ranker._model is first_model

    def test_encode_single(self):
        ranker = get_semantic_ranker()
        emb = ranker.encode("这是一个测试句子")
        assert emb is not None
        assert isinstance(emb, np.ndarray)
        assert emb.shape[0] > 0

    def test_encode_caching(self):
        ranker = get_semantic_ranker()
        ranker.clear_cache()
        text = "测试缓存"
        emb1 = ranker.encode(text)
        emb2 = ranker.encode(text)
        assert np.allclose(emb1, emb2)
        assert ranker._cache.get(text) is not None

    def test_encode_batch(self):
        ranker = get_semantic_ranker()
        texts = ["句子一", "句子二", "句子三"]
        embs = ranker.encode_batch(texts)
        assert embs is not None
        assert len(embs) == 3

    def test_encode_batch_with_cache(self):
        ranker = get_semantic_ranker()
        ranker.clear_cache()
        texts = ["句子一", "句子二", "句子三"]
        embs1 = ranker.encode_batch(texts)
        embs2 = ranker.encode_batch(texts)
        assert np.allclose(embs1, embs2)

    def test_rank_basic(self):
        ranker = get_semantic_ranker()
        sentence = "林轩说今天天气很好"
        candidates = ["林轩", "小翠", "王管家"]
        results = ranker.rank(sentence, candidates, threshold=0.3)
        assert len(results) > 0
        assert results[0][0] == "林轩"
        assert results[0][1] >= 0.3

    def test_rank_threshold(self):
        ranker = get_semantic_ranker()
        sentence = "测试句子"
        candidates = ["完全不相关的候选", "另一个不相关的"]
        results = ranker.rank(sentence, candidates, threshold=0.95)
        assert len(results) == 0

    def test_rank_ordering(self):
        ranker = get_semantic_ranker()
        sentence = "少爷今天心情很好"
        candidates = ["少爷", "小翠", "管家", "少爷林轩"]
        results = ranker.rank(sentence, candidates, threshold=0.3)
        assert len(results) > 0
        assert results[0][1] >= results[-1][1]

    def test_rank_empty_candidates(self):
        ranker = get_semantic_ranker()
        results = ranker.rank("测试", [], threshold=0.7)
        assert len(results) == 0

    def test_rank_with_profiles(self):
        ranker = get_semantic_ranker()
        sentence = "少爷吩咐小翠去准备"
        profiles = [
            ("char1", "林轩 少爷 男性 吩咐下人"),
            ("char2", "小翠 丫鬟 女性 听从吩咐"),
        ]
        results = ranker.rank_with_profiles(sentence, profiles, threshold=0.3)
        assert len(results) > 0
        assert results[0][0] in ("char1", "char2")

    def test_rank_with_profiles_empty(self):
        ranker = get_semantic_ranker()
        results = ranker.rank_with_profiles("测试", [], threshold=0.7)
        assert len(results) == 0

    def test_cache_stats(self):
        ranker = get_semantic_ranker()
        ranker.clear_cache()
        ranker.encode("统计测试")
        stats = ranker.get_cache_stats()
        assert "cache_size" in stats
        assert stats["cache_size"] >= 1

    def test_singleton(self):
        r1 = get_semantic_ranker()
        r2 = get_semantic_ranker()
        assert r1 is r2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
