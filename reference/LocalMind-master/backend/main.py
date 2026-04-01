"""LocalMind FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.db import init_db
from backend.db.models import FineTuneJob
from backend.routers import (
    chat_router,
    documents_router,
    finetune_router,
    models_router,
    upload_router,
)
from backend.utils.hardware import detect_hardware, AcceleratorType


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    settings.ensure_directories()
    await init_db()
    
    # Mark stale fine-tune jobs as stopped (jobs interrupted by server restart)
    from backend.db import get_session
    from datetime import datetime
    from sqlmodel import update
    
    async with get_session() as session:
        stmt = (
            update(FineTuneJob)
            .where(FineTuneJob.status.in_(["generating_data", "training"]))
            .values(status="stale", updated_at=datetime.utcnow())
        )
        result = await session.exec(stmt)
        if result.rowcount > 0:
            print(f"Marked {result.rowcount} stale fine-tune jobs as 'stale'")
        await session.commit()

    # Show hardware banner using comprehensive hardware detection
    hw = detect_hardware()
    print("\n" + "=" * 60)
    print("LocalMind - 100% Offline RAG Application")
    print("=" * 60)
    print(f"LLM Backend: {settings.llm_backend}")
    print(f"Embedding Backend: {settings.embedding_backend}")
    print(f"CPU: {hw.cpu.name} ({hw.cpu.total_cores} threads)")
    if hw.primary_gpu.is_available:
        accel = hw.primary_gpu.accelerator
        if accel == AcceleratorType.NVIDIA_CUDA:
            print(f"  GPU: NVIDIA {hw.primary_gpu.name} ({hw.primary_gpu.vram_gb:.1f} GB VRAM)")
        elif accel == AcceleratorType.INTEL_OPENVINO:
            print(f"  GPU: Intel {hw.primary_gpu.name} (OpenVINO)")
        elif accel == AcceleratorType.AMD_ROCM:
            print(f"  GPU: AMD {hw.primary_gpu.name}")
    else:
        print("  GPU: None (CPU fallback)")
    print(f"Memory: {hw.memory.total_gb:.1f} GB total, {hw.memory.available_gb:.1f} GB available")
    print(f"Hardware: {hw.display_string}")
    print("=" * 60 + "\n")

    yield

    # Shutdown
    print("LocalMind shutting down...")


app = FastAPI(
    title="LocalMind",
    description="100% offline local RAG application with fine-tuning support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(finetune_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "LocalMind",
        "version": "1.0.0",
        "description": "100% offline local RAG application",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
