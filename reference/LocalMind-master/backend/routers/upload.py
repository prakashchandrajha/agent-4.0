"""Document upload router."""

import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlmodel import select

from backend.config import get_settings
from backend.db import Document, get_session
from backend.services.chunker import get_chunker
from backend.services.parsers import get_file_type, is_supported, parser_factory
from backend.services.vector_store import get_vector_store
from backend.utils.hardware import detect_hardware, AcceleratorType

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.

    Supports: PDF, Word, Excel, CSV, Images, PowerPoint, Text/Markdown
    """
    settings = get_settings()

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not is_supported(file.filename, file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.filename}",
        )

    file_type = get_file_type(file.filename, file.content_type)

    # Generate unique filename
    suffix = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4()}{suffix}"
    file_path = settings.upload_path_resolved / unique_name

    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    file_size = file_path.stat().st_size

    # Create database record
    async with get_session() as session:
        doc = Document(
            filename=unique_name,
            original_filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            status="processing",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        doc_id = doc.id

    # Determine accelerator display string
    hardware = detect_hardware()
    if hardware.primary_gpu.is_available:
        accel = hardware.primary_gpu.accelerator
        name = hardware.primary_gpu.name
        if accel == AcceleratorType.INTEL_OPENVINO:
            accelerator_label = f"Intel {name}"
        elif accel == AcceleratorType.NVIDIA_CUDA:
            accelerator_label = f"NVIDIA {name}"
        elif accel == AcceleratorType.AMD_ROCM:
            accelerator_label = f"AMD {name}"
        else:
            accelerator_label = name
    else:
        accelerator_label = "CPU"

    # Process document
    try:
        # Time the full parse → chunk → embed pipeline
        t_start = time.perf_counter()

        # Parse document
        parsed_chunks = parser_factory(file_path, file.content_type)

        if not parsed_chunks:
            processing_time = round(time.perf_counter() - t_start, 2)
            async with get_session() as session:
                doc = await session.get(Document, doc_id)
                doc.status = "ready"
                doc.chunk_count = 0
                doc.processing_time = processing_time
                doc.accelerator_used = accelerator_label
                doc.updated_at = datetime.utcnow()
                await session.commit()

            return {
                "id": doc_id,
                "filename": file.filename,
                "status": "ready",
                "chunk_count": 0,
                "processing_time": processing_time,
                "accelerator_used": accelerator_label,
                "warning": "No extractable content found in document",
            }

        # Chunk the parsed content
        chunker = get_chunker()
        chunks = chunker.chunk_documents(parsed_chunks)

        # Add to vector store
        vector_store = get_vector_store()
        chunk_count = vector_store.add_documents(doc_id, chunks)

        processing_time = round(time.perf_counter() - t_start, 2)

        # Update database
        async with get_session() as session:
            doc = await session.get(Document, doc_id)
            doc.status = "ready"
            doc.chunk_count = chunk_count
            doc.processing_time = processing_time
            doc.accelerator_used = accelerator_label
            doc.updated_at = datetime.utcnow()
            await session.commit()

        return {
            "id": doc_id,
            "filename": file.filename,
            "file_type": file_type,
            "file_size": file_size,
            "status": "ready",
            "chunk_count": chunk_count,
            "processing_time": processing_time,
            "accelerator_used": accelerator_label,
        }

    except Exception as e:
        # Update status to error
        async with get_session() as session:
            doc = await session.get(Document, doc_id)
            doc.status = "error"
            doc.error_message = str(e)
            doc.updated_at = datetime.utcnow()
            await session.commit()

        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")
