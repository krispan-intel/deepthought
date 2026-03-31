"""
vectordb/embedder.py

Local embedding engine for DeepThought.
Runs 100% on local hardware - no data leaves the machine.

Primary:  sentence-transformers (CPU/GPU local)
Fallback: internal API endpoint (if local model unavailable)
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, Optional

import numpy as np
from loguru import logger


# ─────────────────────────────────────────────────────────────────
# Embedding Backend Enum
# ─────────────────────────────────────────────────────────────────

class EmbeddingBackend(str, Enum):
    LOCAL_ST   = "local_sentence_transformers"  # 優先
    LOCAL_API  = "local_api"                    # 備用 (internal endpoint)


# ─────────────────────────────────────────────────────────────────
# Recommended Local Models
# ─────────────────────────────────────────────────────────────────

RECOMMENDED_MODELS = {
    # 最佳技術文件效果，支援多語言
    "bge-m3": "BAAI/bge-m3",

    # 輕量快速，英文技術文件夠用
    "bge-base": "BAAI/bge-base-en-v1.5",

    # 更強但更慢
    "e5-large": "intfloat/e5-large-v2",

    # 程式碼專用
    "codebert": "microsoft/codebert-base",

    # 平衡選擇 (建議預設)
    "bge-small": "BAAI/bge-small-en-v1.5",
}

DEFAULT_MODEL = "BAAI/bge-m3"


# ─────────────────────────────────────────────────────────────────
# Local Sentence-Transformers Embedder
# ─────────────────────────────────────────────────────────────────

class LocalEmbedder:
    """
    100% Local embedding using sentence-transformers.

    Runs on CPU or GPU depending on availability.
    Intel hardware: uses IPEX optimization if available.

    Recommended models for DeepThought:
    - BAAI/bge-m3          : Best for technical docs, multilingual
    - BAAI/bge-base-en-v1.5: Lighter, fast, good for English
    - intfloat/e5-large-v2 : Strong general purpose
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        batch_size: int = 32,
        normalize: bool = True,
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize = normalize
        self.cache_dir = cache_dir or Path("./data/models")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Auto-detect device
        self.device = device or self._detect_device()

        # Load model
        self._model = None
        self._load_model()

    def _detect_device(self) -> str:
        """Auto-detect best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("  Device: CUDA GPU")
                return "cuda"
            # Check for Intel XPU (Gaudi / Arc)
            if hasattr(torch, "xpu") and torch.xpu.is_available():
                logger.info("  Device: Intel XPU")
                return "xpu"
        except ImportError:
            pass
        logger.info("  Device: CPU")
        return "cpu"

    def _load_model(self):
        """Load sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(
                f"📦 Loading local embedding model: {self.model_name}"
            )
            logger.info(f"   Device: {self.device}")
            logger.info(f"   Cache:  {self.cache_dir}")

            model_basename = self.model_name.split("/")[-1]
            local_model_path = self.cache_dir / model_basename

            if local_model_path.exists() and local_model_path.is_dir():
                logger.info(f"📂 Detected local clone at: {local_model_path}, forcing offline mode.")
                load_path = str(local_model_path)
                offline_mode = True
            else:
                load_path = self.model_name
                offline_mode = False

            self._model = SentenceTransformer(
                model_name_or_path=load_path,
                device=self.device,
                cache_folder=str(self.cache_dir),
                local_files_only=offline_mode
            )

            # Try Intel IPEX optimization
            self._try_ipex_optimize()

            # Warm up
            _ = self._model.encode(
                ["warmup"],
                normalize_embeddings=self.normalize,
            )

            dim = self._model.get_sentence_embedding_dimension()
            logger.info(
                f"✅ Local embedder ready | "
                f"model={self.model_name} | "
                f"dim={dim} | "
                f"device={self.device}"
            )

        except ImportError:
            logger.error(
                "sentence-transformers not installed.\n"
                "Run: pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _try_ipex_optimize(self):
        """Try to apply Intel IPEX optimization for CPU inference."""
        if self.device != "cpu":
            return
        try:
            import intel_extension_for_pytorch as ipex
            self._model = ipex.optimize(self._model)
            logger.info("  ✅ Intel IPEX optimization applied")
        except ImportError:
            pass  # IPEX not available, that's fine
        except Exception as e:
            logger.debug(f"  IPEX optimization skipped: {e}")

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        if self._model is None:
            raise RuntimeError("Model not loaded")
        return self._model.get_sentence_embedding_dimension()

    # ── Core Embedding Methods ────────────────────────────────────

    def embed(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed a list of texts locally.

        Args:
            texts: List of strings to embed

        Returns:
            List of L2-normalized numpy float32 arrays
        """
        if not texts:
            return []

        if self._model is None:
            raise RuntimeError("Embedder not initialized")

        # Filter empty strings
        clean_texts = [t if t.strip() else " " for t in texts]

        try:
            embeddings = self._model.encode(
                clean_texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=len(clean_texts) > 100,
                convert_to_numpy=True,
            )

            # Ensure float32
            return [
                np.array(emb, dtype=np.float32)
                for emb in embeddings
            ]

        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return self.embed([text])[0]

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query.

        BGE models support query instructions for better retrieval.
        """
        # BGE models benefit from query instruction prefix
        if "bge" in self.model_name.lower():
            query = f"Represent this sentence for searching relevant passages: {query}"

        # E5 models use "query: " prefix
        elif "e5" in self.model_name.lower():
            query = f"query: {query}"

        return self.embed_one(query)

    def embed_document(self, text: str) -> np.ndarray:
        """
        Embed a document (passage).

        BGE/E5 models use different prefixes for documents vs queries.
        """
        # E5 models use "passage: " prefix for documents
        if "e5" in self.model_name.lower():
            text = f"passage: {text}"

        return self.embed_one(text)

    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        """Embed a list of documents (passages)."""
        if "e5" in self.model_name.lower():
            texts = [f"passage: {t}" for t in texts]
        return self.embed(texts)


# ─────────────────────────────────────────────────────────────────
# Fallback: Internal API Embedder
# ─────────────────────────────────────────────────────────────────

class APIEmbedder:
    """
    Fallback embedder using internal OpenAI-compatible API.
    Only used if local model is unavailable.
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        from configs.settings import settings

        self.model = model
        self._client = OpenAI(
            base_url=settings.internal_llm_base_url,
            api_key=settings.internal_llm_api_key,
        )
        logger.warning(
            f"⚠️  Using API embedder: {model} "
            f"(data leaves local environment!)"
        )

    @property
    def dimension(self) -> int:
        return 1536  # text-embedding-3-small default

    def embed(self, texts: List[str]) -> List[np.ndarray]:
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=texts,
            )
            embeddings = []
            for item in response.data:
                vec = np.array(item.embedding, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                embeddings.append(vec)
            return embeddings
        except Exception as e:
            logger.error(f"API embedding failed: {e}")
            raise

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_one(query)

    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        return self.embed(texts)


# ─────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────

def create_embedder(
    model_name: Optional[str] = None,
    force_local: bool = True,
) -> LocalEmbedder | APIEmbedder:
    """
    Create the best available embedder.

    Args:
        model_name:  Override default model
        force_local: If True, raise error if local model unavailable

    Returns:
        LocalEmbedder (preferred) or APIEmbedder (fallback)
    """
    model = model_name or DEFAULT_MODEL

    try:
        embedder = LocalEmbedder(model_name=model)
        logger.info("✅ Using local embedder (100% private)")
        return embedder

    except Exception as e:
        if force_local:
            logger.error(
                f"Local embedder failed and force_local=True: {e}"
            )
            raise

        logger.warning(
            f"Local embedder unavailable ({e}), "
            f"falling back to API embedder"
        )
        return APIEmbedder()
