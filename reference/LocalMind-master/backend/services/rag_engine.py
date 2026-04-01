"""RAG engine for document-based question answering."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from backend.config import get_settings
from backend.services.llm_client import get_llm_client
from backend.services.vector_store import get_vector_store


SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided context documents. 

Guidelines:
- Answer based ONLY on the information in the provided context
- If the context doesn't contain enough information to answer, say so clearly
- Cite your sources by mentioning the document name and page/section when relevant
- Be concise but thorough
- If asked about something not in the context, explain that you can only answer based on the uploaded documents"""


class RAGEngine:
    """RAG engine for document Q&A with streaming support."""

    def __init__(self):
        """Initialize RAG engine."""
        self.settings = get_settings()
        self.vector_store = get_vector_store()
        self.llm_client = get_llm_client()

    def _build_context(self, results: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """
        Build context string from search results.

        Args:
            results: Vector search results.

        Returns:
            Tuple of (context string, sources list).
        """
        if not results:
            return "", []

        context_parts = []
        sources = []

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            source = metadata.get("source", "Unknown")
            location = metadata.get("page_or_sheet_or_slide", "")
            file_type = metadata.get("file_type", "")

            # Build location label
            if file_type == "pdf":
                location_label = f"Page {location}"
            elif file_type in ("excel", "csv"):
                location_label = f"Sheet: {location}"
            elif file_type == "pptx":
                location_label = f"Slide {location}"
            else:
                location_label = f"Section {location}"

            context_parts.append(
                f"[Source {i}: {source}, {location_label}]\n{result['text']}"
            )

            sources.append({
                "source": source,
                "location": str(location),
                "location_label": location_label,
                "file_type": file_type,
                "score": result.get("score", 0),
                "chunk_index": metadata.get("chunk_index", 0),
            })

        context = "\n\n---\n\n".join(context_parts)
        return context, sources

    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build the final prompt with context.

        Args:
            query: User question.
            context: Retrieved context.

        Returns:
            Complete prompt string.
        """
        if not context:
            return f"""No relevant documents were found for your question.

Question: {query}

Please note: I can only answer questions based on uploaded documents. If you haven't uploaded any documents yet, please do so first."""

        return f"""Based on the following context from uploaded documents, answer the user's question.

CONTEXT:
{context}

---

USER QUESTION: {query}

Please provide a helpful answer based on the context above. Cite the sources when relevant."""

    async def query(
        self,
        question: str,
        model: str | None = None,
        top_k: int | None = None,
        document_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Answer a question using RAG (non-streaming).

        Args:
            question: User question.
            model: LLM model to use.
            top_k: Number of chunks to retrieve.
            document_ids: Optional filter by document IDs.

        Returns:
            Response dict with answer and sources.
        """
        top_k = top_k or self.settings.top_k

        # Retrieve relevant chunks
        results = self.vector_store.search(
            query=question,
            top_k=top_k,
            document_ids=document_ids,
        )

        # Build context and prompt
        context, sources = self._build_context(results)
        prompt = self._build_prompt(question, context)

        # Generate response
        response = await self.llm_client.generate(
            prompt=prompt,
            model=model,
            system_prompt=SYSTEM_PROMPT,
        )

        return {
            "answer": response,
            "sources": sources,
            "model": model or self.settings.default_model,
        }

    async def stream_query(
        self,
        question: str,
        model: str | None = None,
        top_k: int | None = None,
        document_ids: list[int] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Answer a question using RAG with streaming.

        Yields SSE-formatted events:
        - data: {"type": "sources", "sources": [...]}
        - data: {"type": "chunk", "content": "..."}
        - data: {"type": "done"}

        Args:
            question: User question.
            model: LLM model to use.
            top_k: Number of chunks to retrieve.
            document_ids: Optional filter by document IDs.

        Yields:
            SSE event strings.
        """
        top_k = top_k or self.settings.top_k

        # Retrieve relevant chunks
        results = self.vector_store.search(
            query=question,
            top_k=top_k,
            document_ids=document_ids,
        )

        # Build context and prompt
        context, sources = self._build_context(results)
        prompt = self._build_prompt(question, context)

        # Send sources first
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        # Stream response
        async for chunk in self.llm_client.stream_generate(
            prompt=prompt,
            model=model,
            system_prompt=SYSTEM_PROMPT,
        ):
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


# Singleton instance
_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    """Get RAG engine singleton."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
