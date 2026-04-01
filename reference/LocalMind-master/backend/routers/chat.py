"""Chat router with RAG and streaming support."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services.rag_engine import get_rag_engine

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request model."""

    query: str
    model: str | None = None
    top_k: int | None = None
    document_ids: list[int] | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Chat response model (non-streaming)."""

    answer: str
    sources: list[dict]
    model: str


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with documents using RAG.

    Supports streaming (SSE) and non-streaming responses.
    For streaming, returns text/event-stream with JSON events.
    """
    rag_engine = get_rag_engine()

    if request.stream:
        return StreamingResponse(
            rag_engine.stream_query(
                question=request.query,
                model=request.model,
                top_k=request.top_k,
                document_ids=request.document_ids,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        result = await rag_engine.query(
            question=request.query,
            model=request.model,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )
        return ChatResponse(**result)
