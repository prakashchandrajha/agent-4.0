"""Vector store service using ChromaDB."""

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import get_settings
from backend.services.embedder import get_embedder


class VectorStore:
    """ChromaDB vector store for document embeddings."""

    COLLECTION_NAME = "localmind_documents"

    def __init__(self):
        """Initialize ChromaDB client with persistent storage."""
        settings = get_settings()

        # Always persist to disk
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_path_resolved),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self.embedder = get_embedder()
        self._collection = None

    @property
    def collection(self):
        """Get or create the documents collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_documents(
        self,
        document_id: int,
        chunks: list[dict[str, Any]],
    ) -> int:
        """
        Add document chunks to vector store.

        Args:
            document_id: Database document ID.
            chunks: List of chunks with text and metadata.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_texts(texts)

        ids = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"doc_{document_id}_chunk_{idx}"
            ids.append(chunk_id)

            metadata = {
                **chunk.get("metadata", {}),
                "document_id": document_id,
            }
            # Ensure all metadata values are strings or numbers (ChromaDB requirement)
            metadata = {
                k: str(v) if not isinstance(v, (int, float, bool)) else v
                for k, v in metadata.items()
            }
            metadatas.append(metadata)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        document_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            document_ids: Optional filter by document IDs.

        Returns:
            List of results with text, metadata, and score.
        """
        settings = get_settings()
        top_k = top_k or settings.top_k

        query_embedding = self.embedder.embed_text(query)

        where_filter = None
        if document_ids:
            where_filter = {
                "document_id": {"$in": document_ids},
            }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Convert to list of dicts
        output = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity score (cosine)
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # Cosine distance to similarity

                output.append(
                    {
                        "id": doc_id,
                        "text": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": score,
                    }
                )

        # Sort by score descending
        output.sort(key=lambda x: x["score"], reverse=True)
        return output

    def delete_document(self, document_id: int) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Database document ID.

        Returns:
            Number of chunks deleted.
        """
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={"document_id": document_id},
            include=[],
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])

        return 0

    def get_document_chunks(self, document_id: int) -> list[dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Database document ID.

        Returns:
            List of chunks with text and metadata.
        """
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )

        output = []
        if results["ids"]:
            for i, chunk_id in enumerate(results["ids"]):
                output.append(
                    {
                        "id": chunk_id,
                        "text": results["documents"][i] if results["documents"] else "",
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    }
                )

        return output

    def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        return {
            "collection_name": self.COLLECTION_NAME,
            "total_chunks": self.collection.count(),
        }


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get vector store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
