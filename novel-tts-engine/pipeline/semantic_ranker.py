"""
L2 Semantic Speaker Ranking Module

Uses BGE-small-zh model to compute sentence embeddings and rank candidate speakers
by semantic similarity to the current dialogue context.

Supports both ONNX (preferred) and PyTorch backends with automatic fallback.
"""
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import logging
import time
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_LOCAL_PATH = str(Path(__file__).parent.parent / "models" / "bge-small-zh-v1.5")
ONNX_MODEL_PATH = str(Path(__file__).parent.parent / "models" / "bge-small-onnx")


@dataclass
class SemanticCache:
    """Thread-safe embedding cache to avoid recomputation."""
    max_size: int = 1000

    def __post_init__(self):
        self._cache: Dict[str, np.ndarray] = {}
        self._lock = Lock()

    def get(self, text: str) -> Optional[np.ndarray]:
        with self._lock:
            return self._cache.get(text)

    def put(self, text: str, embedding: np.ndarray):
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[text] = embedding

    def clear(self):
        with self._lock:
            self._cache.clear()

    def __len__(self):
        return len(self._cache)


class SemanticRanker:
    """Rank candidate speakers by semantic similarity using BGE model."""

    def __init__(self, model_name: str = MODEL_NAME, cache_size: int = 1000, enable_l2: bool = True):
        self.model_name = model_name
        self._enable_l2 = enable_l2
        self._backend = None  # 'onnx' or 'pytorch'
        self._onnx_session = None
        self._onnx_tokenizer = None
        self._tokenizer = None
        self._model = None
        self._device = None
        self._cache = SemanticCache(max_size=cache_size)
        self._loaded = False
        self._load_error = None

    def is_available(self) -> bool:
        return self._enable_l2 and self._loaded and (self._model is not None or self._onnx_session is not None)

    def load_model(self):
        """Lazy load the embedding model, preferring ONNX backend."""
        if self._loaded:
            return

        if not self._enable_l2:
            logger.info("L2 semantic matching disabled")
            return

        if self._load_error:
            return

        # Try ONNX first (faster, lighter)
        try:
            self._load_onnx()
            self._loaded = True
            return
        except Exception as e:
            logger.info(f"ONNX backend not available: {e}")

        # Fallback to PyTorch
        try:
            self._load_pytorch()
            self._loaded = True
            return
        except Exception as e:
            self._load_error = str(e)
            logger.warning(f"L2 semantic model load failed (all backends): {e}")
            self._loaded = False

    def _load_onnx(self):
        """Load ONNX runtime model."""
        from transformers import AutoTokenizer
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        import torch

        onnx_path = ONNX_MODEL_PATH if Path(ONNX_MODEL_PATH).exists() else None
        if not onnx_path:
            raise FileNotFoundError(f"ONNX model not found at {ONNX_MODEL_PATH}")

        logger.info(f"Loading L2 semantic model (ONNX) from: {onnx_path}")
        start = time.time()

        self._onnx_tokenizer = AutoTokenizer.from_pretrained(
            onnx_path,
            use_fast=True,
            local_files_only=True,
        )
        self._onnx_session = ORTModelForFeatureExtraction.from_pretrained(onnx_path)
        self._onnx_session.eval()

        self._device = torch.device("cpu")
        elapsed = time.time() - start
        logger.info(f"L2 semantic model (ONNX) loaded in {elapsed:.1f}s")
        self._backend = 'onnx'

    def _load_pytorch(self):
        """Load PyTorch model as fallback."""
        from transformers import AutoTokenizer, AutoModel
        import torch

        model_path = MODEL_LOCAL_PATH if Path(MODEL_LOCAL_PATH).exists() else self.model_name
        
        logger.info(f"Loading L2 semantic model (PyTorch) from: {model_path}")
        start = time.time()

        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            use_fast=True,
            trust_remote_code=True,
            local_files_only=Path(MODEL_LOCAL_PATH).exists(),
        )
        self._model = AutoModel.from_pretrained(
            model_path,
            local_files_only=Path(MODEL_LOCAL_PATH).exists(),
        )
        self._model.eval()

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

        elapsed = time.time() - start
        logger.info(f"L2 semantic model (PyTorch) loaded in {elapsed:.1f}s on {self._device}")
        self._backend = 'pytorch'

    def encode(self, text: str) -> Optional[np.ndarray]:
        """Encode single text to embedding vector."""
        if not self.is_available():
            self.load_model()
        if not self.is_available():
            return None

        cached = self._cache.get(text)
        if cached is not None:
            return cached

        if self._backend == 'onnx':
            result = self._encode_onnx(text)
        else:
            result = self._encode_pytorch(text)

        if result is not None:
            self._cache.put(text, result)
        return result

    def _encode_onnx(self, text: str) -> Optional[np.ndarray]:
        """Encode using ONNX runtime."""
        import torch
        
        inputs = self._onnx_tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )

        with torch.no_grad():
            outputs = self._onnx_session(**inputs)
            embeddings = outputs.last_hidden_state[:, 0]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy()[0]

    def _encode_pytorch(self, text: str) -> Optional[np.ndarray]:
        """Encode using PyTorch."""
        import torch
        
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy()[0]

    def encode_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """Encode batch of texts to embedding vectors."""
        if not self.is_available():
            self.load_model()
        if not self.is_available():
            return None

        import torch

        to_encode = []
        to_encode_indices = []
        result = [None] * len(texts)

        for i, text in enumerate(texts):
            cached = self._cache.get(text)
            if cached is not None:
                result[i] = cached
            else:
                to_encode.append(text)
                to_encode_indices.append(i)

        if not to_encode:
            return np.array([r for r in result if r is not None])

        if self._backend == 'onnx':
            encoded = self._encode_batch_onnx(to_encode)
        else:
            encoded = self._encode_batch_pytorch(to_encode)

        if encoded is not None:
            for idx, emb in zip(to_encode_indices, encoded):
                result[idx] = emb
                self._cache.put(to_encode[to_encode_indices.index(idx)], emb)

        return np.array([r for r in result if r is not None])

    def _encode_batch_onnx(self, texts: List[str]) -> Optional[np.ndarray]:
        import torch
        
        inputs = self._onnx_tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )

        batch_size = 32
        all_embeddings = []
        for start in range(0, len(texts), batch_size):
            batch_inputs = {k: v[start:start + batch_size] for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._onnx_session(**batch_inputs)
                embeddings = outputs.last_hidden_state[:, 0]
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    def _encode_batch_pytorch(self, texts: List[str]) -> Optional[np.ndarray]:
        import torch

        inputs = self._tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        batch_size = 32
        all_embeddings = []
        for start in range(0, len(texts), batch_size):
            batch_inputs = {k: v[start:start + batch_size] for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._model(**batch_inputs)
                embeddings = outputs.last_hidden_state[:, 0]
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        if a is None or b is None:
            return 0.0
        a = a.flatten()
        b = b.flatten()
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def rank(
        self,
        sentence: str,
        candidates: List[str],
        threshold: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """Rank candidates by semantic similarity to sentence.

        Args:
            sentence: The current dialogue sentence.
            candidates: List of candidate speaker profile texts.
            threshold: Minimum similarity score to include.

        Returns:
            List of (candidate_text, similarity_score) sorted by score descending.
        """
        if not self.is_available():
            self.load_model()
        if not self.is_available():
            return []

        sentence_emb = self.encode(sentence)
        if sentence_emb is None:
            return []

        results = []
        for candidate in candidates:
            candidate_emb = self.encode(candidate)
            if candidate_emb is not None:
                score = self.cosine_similarity(sentence_emb, candidate_emb)
                if score >= threshold:
                    results.append((candidate, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def rank_with_profiles(
        self,
        sentence: str,
        profiles: List[Tuple[str, str]],
        threshold: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """Rank candidates with pre-built profiles.

        Args:
            sentence: The current dialogue sentence.
            profiles: List of (candidate_id, profile_text) tuples.
            threshold: Minimum similarity score.

        Returns:
            List of (candidate_id, similarity_score) sorted descending.
        """
        if not profiles:
            return []

        if not self.is_available():
            self.load_model()
        if not self.is_available():
            return []

        sentence_emb = self.encode(sentence)
        if sentence_emb is None:
            return []

        profile_texts = [p[1] for p in profiles]
        embeddings = self.encode_batch(profile_texts)
        if embeddings is None:
            return []

        results = []
        for i, (candidate_id, _) in enumerate(profiles):
            if i < len(embeddings):
                score = self.cosine_similarity(sentence_emb, embeddings[i])
                if score >= threshold:
                    results.append((candidate_id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_cache_stats(self) -> Dict[str, int]:
        return {"cache_size": len(self._cache)}

    def clear_cache(self):
        self._cache.clear()


_singleton_lock = Lock()
_semantic_ranker: Optional[SemanticRanker] = None


def get_semantic_ranker(enable_l2: bool = True) -> SemanticRanker:
    """Get or create singleton SemanticRanker instance."""
    global _semantic_ranker
    if _semantic_ranker is None:
        with _singleton_lock:
            if _semantic_ranker is None:
                _semantic_ranker = SemanticRanker(enable_l2=enable_l2)
    return _semantic_ranker
