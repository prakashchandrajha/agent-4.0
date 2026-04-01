"""Text chunking service for RAG."""

from typing import Any

import tiktoken

from backend.config import get_settings


class Chunker:
    """Splits text into overlapping chunks for embedding."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Maximum tokens per chunk.
            chunk_overlap: Overlap tokens between chunks.
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        # Use cl100k_base tokenizer (GPT-4 / most modern models)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text to chunk.

        Returns:
            List of text chunks.
        """
        if not text.strip():
            return []

        tokens = self.tokenizer.encode(text)

        if len(tokens) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)

            # Move start with overlap
            start = end - self.chunk_overlap
            if start >= len(tokens):
                break

        return chunks

    def chunk_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Chunk parsed documents while preserving metadata.

        Args:
            documents: List of parsed document chunks with text and metadata.

        Returns:
            List of smaller chunks with updated metadata.
        """
        result = []
        global_chunk_idx = 0

        for doc in documents:
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})

            # Special handling for images - don't split
            if metadata.get("file_type") == "image":
                result.append(
                    {
                        "text": text,
                        "metadata": {
                            **metadata,
                            "chunk_index": global_chunk_idx,
                        },
                    }
                )
                global_chunk_idx += 1
                continue

            # Special handling for Excel - already chunked by rows
            if metadata.get("file_type") in ("excel", "csv"):
                # Only split if very large
                if self.count_tokens(text) > self.chunk_size * 2:
                    text_chunks = self.chunk_text(text)
                else:
                    text_chunks = [text]
            else:
                text_chunks = self.chunk_text(text)

            for chunk_text in text_chunks:
                result.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **metadata,
                            "chunk_index": global_chunk_idx,
                        },
                    }
                )
                global_chunk_idx += 1

        return result


# Singleton instance
_chunker: Chunker | None = None


def get_chunker() -> Chunker:
    """Get chunker singleton."""
    global _chunker
    if _chunker is None:
        _chunker = Chunker()
    return _chunker
