"""Fine-tuning router."""

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select, update

from backend.config import get_settings
from backend.db import FineTuneJob, get_session
from backend.services.finetuner import (
    detect_hardware,
    emit,
    get_finetune_backend,
    get_finetuner,
    get_progress,
    subscribe_progress,
    unsubscribe_progress,
    _progress,
    set_cancel_flag,
    get_cancel_flag,
    clear_cancel_flag,
)

router = APIRouter(prefix="/api/finetune", tags=["finetune"])
logger = logging.getLogger(__name__)

# Store for active jobs (in production, use Redis or similar)
_active_jobs: dict[int, dict] = {}


class FineTuneStartRequest(BaseModel):
    """Fine-tune start request."""

    name: str
    document_ids: list[int] | None = None
    pairs_per_chunk: int = 5
    backend: str | None = None


class FineTuneExportRequest(BaseModel):
    """Fine-tune export request."""

    job_id: int
    output_name: str


class FineTuneJobResponse(BaseModel):
    """Fine-tune job response."""

    id: int
    name: str
    base_model: str
    status: str
    current_step: int
    total_steps: int
    current_loss: float | None
    eta_seconds: int | None
    output_path: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@router.get("/hardware")
async def get_hardware_info():
    """Get hardware information and fine-tuning recommendations."""
    return detect_hardware()


async def run_finetune_pipeline(job_id: int, request: FineTuneStartRequest):
    import sys
    import time as _time

    print(f"[FINETUNE] Pipeline entered for job {job_id}", flush=True)
    sys.stdout.flush()
    logger.info(f"[FINETUNE] Pipeline entered for job {job_id}")

    # Reset progress for this new run
    _progress.__init__()
    _progress.start_time = _time.time()
    finetuner = get_finetuner()

    try:
        # --- Filtering stage ---
        _backend = request.backend or get_finetune_backend()
        from backend.services.finetuner import DEVICE as _DEVICE
        await emit(
            stage="filtering",
            device=_DEVICE,
            backend=_backend,
        )

        # Generate Q&A pairs
        qa_pairs = []
        async for event in finetuner.generate_qa_pairs(
            document_ids=request.document_ids,
            pairs_per_chunk=request.pairs_per_chunk,
            job_id=job_id,
        ):
            _active_jobs[job_id] = event
            if event.get("type") == "complete":
                qa_pairs = event.get("pairs", [])
            elif event.get("type") == "error":
                raise Exception(event.get("message", "Q&A generation error"))

        if not qa_pairs:
            raise Exception("No Q&A pairs generated")

        # Save training data
        data_path = finetuner.save_training_data(qa_pairs, request.name)

        # --- Training stage ---
        await emit(
            stage="training",
            total_pairs=len(qa_pairs),
            backend=_backend,
        )

        async with get_session() as session:
            job = await session.get(FineTuneJob, job_id)
            job.status = "training"
            job.total_steps = len(qa_pairs)
            job.updated_at = datetime.utcnow()
            await session.commit()

        # Run training
        async for event in finetuner.start_training(data_path, request.name, _backend, job_id):
            _active_jobs[job_id] = event

            if event.get("type") == "progress":
                async with get_session() as session:
                    job = await session.get(FineTuneJob, job_id)
                    job.current_step = event.get("step", 0)
                    job.current_loss = event.get("loss")
                    job.updated_at = datetime.utcnow()
                    await session.commit()

            elif event.get("type") == "complete":
                await emit(stage="done")
                async with get_session() as session:
                    job = await session.get(FineTuneJob, job_id)
                    job.status = "completed"
                    job.output_path = event.get("output_dir")
                    job.updated_at = datetime.utcnow()
                    await session.commit()

            elif event.get("type") == "error":
                raise Exception(event.get("message", "Training error"))

    except Exception as e:
        await emit(stage="error", error=str(e))
        async with get_session() as session:
            job = await session.get(FineTuneJob, job_id)
            if job:
                job.status = "error"
                job.error_message = str(e)
                job.updated_at = datetime.utcnow()
                await session.commit()

@router.post("/start")
async def start_finetune(
    request: FineTuneStartRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a fine-tuning job.

    Returns job ID immediately, training runs in background.
    Use /status/{job_id} SSE endpoint to monitor progress.
    """
    settings = get_settings()

    # Create job record
    async with get_session() as session:
        job = FineTuneJob(
            name=request.name,
            base_model=settings.hf_base_model,
            status="generating_data",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    background_tasks.add_task(run_finetune_pipeline, job_id, request)

    return {
        "job_id": job_id,
        "name": request.name,
        "status": "started",
        "message": "Fine-tuning job started. Monitor progress via /status/{job_id}",
    }


@router.get("/status")
async def finetune_global_status():
    """
    Global fine-tuning progress as an SSE stream.

    Emits real-time progress for the currently running or most recent job.
    Clients should connect here after calling /start to receive live progress.
    """
    async def event_stream():
        import json as _json

        # Send current state immediately on connect
        yield f"data: {_json.dumps(vars(get_progress()))}\n\n"
        q = await subscribe_progress()
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {_json.dumps(data)}\n\n"
                    if data.get("stage") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield 'data: {"ping": true}\n\n'  # keep-alive
        finally:
            unsubscribe_progress(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/status/{job_id}")
async def get_finetune_status_stream(job_id: int):
    """
    Get fine-tuning job status as SSE stream.

    Returns events: progress, status updates, completion/error.
    """
    async with get_session() as session:
        job = await session.get(FineTuneJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        import asyncio

        last_event = None

        while True:
            # Get current event
            current_event = _active_jobs.get(job_id)

            if current_event and current_event != last_event:
                yield f"data: {json.dumps(current_event)}\n\n"
                last_event = current_event

                # Check if done
                if current_event.get("type") in ("complete", "error"):
                    break

            # Check database status
            async with get_session() as session:
                job = await session.get(FineTuneJob, job_id)
                if job.status in ("completed", "error"):
                    yield f"data: {json.dumps({'type': 'done', 'status': job.status})}\n\n"
                    break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/jobs")
async def list_finetune_jobs() -> list[FineTuneJobResponse]:
    """List all fine-tuning jobs."""
    async with get_session() as session:
        result = await session.exec(
            select(FineTuneJob).order_by(FineTuneJob.created_at.desc())
        )
        jobs = result.all()

        return [
            FineTuneJobResponse(
                id=job.id,
                name=job.name,
                base_model=job.base_model,
                status=job.status,
                current_step=job.current_step,
                total_steps=job.total_steps,
                current_loss=job.current_loss,
                eta_seconds=job.eta_seconds,
                output_path=job.output_path,
                error_message=job.error_message,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job in jobs
        ]


@router.get("/jobs/{job_id}")
async def get_finetune_job(job_id: int) -> FineTuneJobResponse:
    """Get a specific fine-tuning job."""
    async with get_session() as session:
        job = await session.get(FineTuneJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return FineTuneJobResponse(
            id=job.id,
            name=job.name,
            base_model=job.base_model,
            status=job.status,
            current_step=job.current_step,
            total_steps=job.total_steps,
            current_loss=job.current_loss,
            eta_seconds=job.eta_seconds,
            output_path=job.output_path,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


@router.post("/export")
async def export_finetune(request: FineTuneExportRequest):
    """Export fine-tuned model to GGUF format."""
    async with get_session() as session:
        job = await session.get(FineTuneJob, request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != "completed":
            raise HTTPException(status_code=400, detail="Job not completed")

        if not job.output_path:
            raise HTTPException(status_code=400, detail="No output path available")

    finetuner = get_finetuner()
    result = await finetuner.export_to_gguf(
        adapter_path=Path(job.output_path),
        output_name=request.output_name,
    )

    return result


@router.post("/jobs/{job_id}/stop")
async def stop_finetune_job(job_id: int):
    """Stop a running fine-tuning job."""
    async with get_session() as session:
        job = await session.get(FineTuneJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in ("generating_data", "training"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot stop job with status '{job.status}'"
            )
        
        # Set cancel flag
        set_cancel_flag(job_id, True)
        
        # Update job status
        job.status = "stopped"
        job.updated_at = datetime.utcnow()
        await session.commit()
    
    return {"stopped": job_id}


@router.delete("/jobs/{job_id}")
async def delete_finetune_job(job_id: int | str):
    """Delete a fine-tuning job and its associated files."""
    # Handle both int and string job_id
    try:
        job_id_int = int(job_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid job_id")
    
    async with get_session() as session:
        job = await session.get(FineTuneJob, job_id_int)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Set cancel flag to stop any running job
        set_cancel_flag(job_id_int, True)
        
        # Get the job's output path before deletion
        job_output_path = job.output_path
        
        # Delete job from database
        await session.delete(job)
        await session.commit()
    
    # Delete job folder if it exists
    if job_output_path:
        job_folder = Path(job_output_path)
        if job_folder.exists():
            try:
                shutil.rmtree(job_folder, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to delete job folder {job_folder}: {e}")
    
    # Also try to delete by job_id in finetuned path
    settings = get_settings()
    job_folder_by_id = settings.finetuned_path_resolved / str(job_id_int)
    if job_folder_by_id.exists():
        try:
            shutil.rmtree(job_folder_by_id, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to delete job folder {job_folder_by_id}: {e}")
    
    # Clear cancel flag
    clear_cancel_flag(job_id_int)
    
    return {"deleted": job_id_int}
