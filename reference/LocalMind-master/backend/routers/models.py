"""Models and backend status router."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import get_settings
from backend.services.finetuner import detect_hardware as detect_finetune_hardware
from backend.services.llm_client import get_llm_client
from backend.utils.hardware import get_hardware_report_dict

router = APIRouter(prefix="/api", tags=["models"])


class ModelInfo(BaseModel):
    """Model information."""

    id: str
    name: str
    size: int | None = None
    modified: str | None = None
    owned_by: str | None = None


class BackendStatus(BaseModel):
    """Backend status information."""

    llm_backend: str
    llm_url: str
    llm_status: str
    llm_error: str | None = None
    embedding_backend: str
    embedding_model: str
    default_model: str
    hardware: dict


@router.get("/models")
async def list_models() -> list[ModelInfo]:
    """List available models from the active LLM backend."""
    llm_client = get_llm_client()
    models = await llm_client.list_models()

    return [
        ModelInfo(
            id=m.get("id", ""),
            name=m.get("name", ""),
            size=m.get("size"),
            modified=m.get("modified"),
            owned_by=m.get("owned_by"),
        )
        for m in models
    ]


@router.get("/backends/status")
async def get_backend_status() -> BackendStatus:
    """Get status of all backends."""
    settings = get_settings()
    llm_client = get_llm_client()

    # Check LLM health
    health = await llm_client.check_health()

    # Get hardware info (finetuner-specific detection for backward compat)
    hardware = detect_finetune_hardware()

    return BackendStatus(
        llm_backend=settings.llm_backend,
        llm_url=llm_client.base_url,
        llm_status=health.get("status", "unknown"),
        llm_error=health.get("error"),
        embedding_backend=settings.embedding_backend,
        embedding_model=(
            settings.embedding_model
            if settings.embedding_backend == "ollama"
            else settings.local_embedding_model
        ),
        default_model=settings.default_model,
        hardware=hardware,
    )


@router.get("/hardware-status")
async def get_hardware_status():
    """
    Get comprehensive hardware detection report.

    Returns CPU, GPU, memory info, accelerator priority,
    and performance recommendations.
    """
    return get_hardware_report_dict()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    llm_client = get_llm_client()
    health = await llm_client.check_health()

    return {
        "status": "healthy",
        "llm_backend": settings.llm_backend,
        "llm_status": health.get("status"),
    }
