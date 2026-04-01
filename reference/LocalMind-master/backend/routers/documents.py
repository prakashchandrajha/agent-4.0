"""Documents management router."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from backend.config import get_settings
from backend.db import Document, get_session
from backend.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    """Document response model."""

    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None
    processing_time: float | None
    accelerator_used: str | None
    created_at: datetime
    updated_at: datetime


@router.get("")
async def list_documents() -> list[DocumentResponse]:
    """List all uploaded documents."""
    async with get_session() as session:
        result = await session.exec(
            select(Document).order_by(Document.created_at.desc())
        )
        documents = result.all()

        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                chunk_count=doc.chunk_count,
                status=doc.status,
                error_message=doc.error_message,
                processing_time=doc.processing_time,
                accelerator_used=doc.accelerator_used,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]


@router.get("/{document_id}")
async def get_document(document_id: int) -> DocumentResponse:
    """Get a specific document."""
    async with get_session() as session:
        doc = await session.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            chunk_count=doc.chunk_count,
            status=doc.status,
            error_message=doc.error_message,
            processing_time=doc.processing_time,
            accelerator_used=doc.accelerator_used,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )


@router.delete("/{document_id}")
async def delete_document(document_id: int):
    """Delete a document and its chunks."""
    settings = get_settings()

    async with get_session() as session:
        doc = await session.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from vector store
        vector_store = get_vector_store()
        deleted_chunks = vector_store.delete_document(document_id)

        # Delete file from disk
        file_path = settings.upload_path_resolved / doc.filename
        if file_path.exists():
            file_path.unlink()

        # Delete from database
        await session.delete(doc)
        await session.commit()

        return {
            "id": document_id,
            "deleted_chunks": deleted_chunks,
            "message": "Document deleted successfully",
        }


@router.get("/{document_id}/chunks")
async def get_document_chunks(document_id: int):
    """Get all chunks for a document."""
    async with get_session() as session:
        doc = await session.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

    vector_store = get_vector_store()
    chunks = vector_store.get_document_chunks(document_id)

    return {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
