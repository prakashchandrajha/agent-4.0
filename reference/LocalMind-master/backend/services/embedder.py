"""Embedding service with automatic CUDA/OpenVINO/CPU acceleration."""

import logging
from typing import Any

import httpx

from backend.config import get_settings
from backend.utils.hardware import AcceleratorType, detect_hardware

logger = logging.getLogger(__name__)


class Embedder:
    """
    Generates embeddings using configured backend with automatic GPU acceleration.
    
    Acceleration priority:
    1. NVIDIA CUDA - If available, uses GPU for embeddings
    2. CPU - Multi-threaded fallback with optimized batch processing
    """

    def __init__(self):
        """Initialize embedder with automatic device detection."""
        self.settings = get_settings()
        self._local_model = None
        self._device = None
        self._hardware = detect_hardware()
        
        # Determine optimal device
        self._init_device()

    def _init_device(self) -> None:
        """Initialize the optimal compute device."""
        recommendations = self._hardware.recommendations
        
        if recommendations.get("use_gpu_embeddings"):
            self._device = "cuda"
            logger.info(f"Embedder using CUDA: {self._hardware.primary_gpu.name}")
        else:
            self._device = "cpu"
            logger.info(f"Embedder using CPU with {self._hardware.cpu.total_cores} threads")

    @property
    def device(self) -> str:
        """Get the compute device being used."""
        return self._device

    @property
    def local_model(self):
        """Lazy load local sentence-transformers model with optimal device."""
        if self._local_model is None and self.settings.embedding_backend == "local":
            from sentence_transformers import SentenceTransformer
            
            model_name = self.settings.local_embedding_model
            
            # Load model on optimal device
            self._local_model = SentenceTransformer(
                model_name,
                device=self._device,
            )
            
            # Enable FP16 on CUDA for faster inference
            if self._device == "cuda" and self._hardware.primary_gpu.supports_fp16:
                self._local_model.half()
                logger.info("Embedder using FP16 precision for faster inference")
            
            logger.info(f"Loaded embedding model '{model_name}' on {self._device}")
        
        return self._local_model

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text.

        Returns:
            Embedding vector.
        """
        if self.settings.embedding_backend == "local":
            return self._embed_local(text)
        else:
            return self._embed_ollama(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts with adaptive batching.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding vectors.
        """
        if self.settings.embedding_backend == "local":
            return self._embed_local_batch(texts)
        else:
            # Ollama doesn't support batching, but we can parallelize
            return self._embed_ollama_batch(texts)

    def _embed_ollama(self, text: str) -> list[float]:
        """Generate embedding using Ollama."""
        try:
            response = httpx.post(
                f"{self.settings.ollama_base_url}/api/embeddings",
                json={
                    "model": self.settings.embedding_model,
                    "prompt": text,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {e}") from e

    def _embed_ollama_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for batch using Ollama with connection pooling."""
        embeddings = []
        
        # Use connection pooling for efficiency
        with httpx.Client(timeout=60) as client:
            for text in texts:
                try:
                    response = client.post(
                        f"{self.settings.ollama_base_url}/api/embeddings",
                        json={
                            "model": self.settings.embedding_model,
                            "prompt": text,
                        },
                    )
                    response.raise_for_status()
                    embeddings.append(response.json()["embedding"])
                except Exception as e:
                    raise RuntimeError(f"Ollama embedding failed: {e}") from e
        
        return embeddings

    def _embed_local(self, text: str) -> list[float]:
        """Generate embedding using local model."""
        embedding = self.local_model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embedding.tolist()

    def _embed_local_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for batch using local model with adaptive batching.
        
        Batch size is adjusted based on available memory and GPU VRAM.
        """
        # Adaptive batch size based on memory
        batch_size = self._hardware.recommendations.get("chunk_batch_size", 10)
        
        if self._device == "cuda":
            # Larger batches on GPU
            vram = self._hardware.primary_gpu.vram_gb
            if vram >= 8:
                batch_size = 64
            elif vram >= 4:
                batch_size = 32
            else:
                batch_size = 16
        else:
            # CPU batch size based on cores
            batch_size = min(32, self._hardware.cpu.total_cores * 2)
        
        embeddings = self.local_model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )
        
        return [emb.tolist() for emb in embeddings]

    def get_embedding_dimension(self) -> int:
        """Get dimension of embeddings."""
        if self.settings.embedding_backend == "local":
            return self.local_model.get_sentence_embedding_dimension()
        else:
            # nomic-embed-text dimension
            return 768

    def get_status(self) -> dict[str, Any]:
        """Get embedder status information."""
        return {
            "backend": self.settings.embedding_backend,
            "model": (
                self.settings.local_embedding_model
                if self.settings.embedding_backend == "local"
                else self.settings.embedding_model
            ),
            "device": self._device,
            "gpu_name": (
                self._hardware.primary_gpu.name
                if self._device == "cuda"
                else None
            ),
            "fp16_enabled": (
                self._device == "cuda" and self._hardware.primary_gpu.supports_fp16
            ),
        }


# Singleton instance
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Get embedder singleton."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def reset_embedder() -> None:
    """Reset embedder singleton (for testing)."""
    global _embedder
    _embedder = None
