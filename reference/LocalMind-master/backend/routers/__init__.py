"""API routers module."""

from backend.routers.chat import router as chat_router
from backend.routers.documents import router as documents_router
from backend.routers.finetune import router as finetune_router
from backend.routers.models import router as models_router
from backend.routers.upload import router as upload_router

__all__ = [
    "chat_router",
    "documents_router",
    "finetune_router",
    "models_router",
    "upload_router",
]
