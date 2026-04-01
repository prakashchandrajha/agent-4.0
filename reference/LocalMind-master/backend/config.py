"""Configuration management for LocalMind."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Backend Configuration
    llm_backend: Literal["ollama", "lmstudio", "gpt4all"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    lmstudio_base_url: str = "http://localhost:1234/v1"
    gpt4all_base_url: str = "http://localhost:4891/v1"
    default_model: str = "qwen2.5:3b"

    # Embedding Configuration
    embedding_backend: Literal["ollama", "local"] = "ollama"
    embedding_model: str = "nomic-embed-text"
    local_embedding_model: str = "all-MiniLM-L6-v2"

    # Fine-tuning Configuration
    finetune_backend: Literal["auto", "unsloth", "airllm", "hf"] = "auto"
    hf_base_model: str = "Qwen/Qwen2.5-3B-Instruct"
    finetune_qa_model: str = "qwen2.5-coder:3b"
    finetune_qa_pairs_per_chunk: int = 1
    finetune_batch_size: int = 4
    finetune_chunk_timeout: float = 15.0

    # Data Paths
    chroma_path: str = "./data/chromadb"
    upload_path: str = "./data/uploads"
    finetuned_path: str = "./data/finetuned"

    # RAG Configuration
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5

    # OCR Configuration
    tesseract_cmd: str = "/usr/bin/tesseract"

    @property
    def chroma_path_resolved(self) -> Path:
        """Get resolved ChromaDB path."""
        return Path(self.chroma_path).resolve()

    @property
    def upload_path_resolved(self) -> Path:
        """Get resolved upload path."""
        return Path(self.upload_path).resolve()

    @property
    def finetuned_path_resolved(self) -> Path:
        """Get resolved fine-tuned models path."""
        return Path(self.finetuned_path).resolve()

    def ensure_directories(self) -> None:
        """Ensure all data directories exist."""
        self.chroma_path_resolved.mkdir(parents=True, exist_ok=True)
        self.upload_path_resolved.mkdir(parents=True, exist_ok=True)
        self.finetuned_path_resolved.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
