"""Database models for LocalMind."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    """Document metadata stored in SQLite."""

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)
    original_filename: str
    file_type: str
    file_size: int
    mime_type: str
    chunk_count: int = 0
    status: str = "pending"  # pending, processing, ready, error
    error_message: Optional[str] = None
    processing_time: Optional[float] = None  # seconds taken to parse/ingest
    accelerator_used: Optional[str] = None  # e.g. "Intel Iris Xe (OpenVINO)"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FineTuneJob(SQLModel, table=True):
    """Fine-tuning job tracking."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    base_model: str
    status: str = "pending"  # pending, generating_data, training, exporting, completed, error
    current_step: int = 0
    total_steps: int = 0
    current_loss: Optional[float] = None
    eta_seconds: Optional[int] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(SQLModel, table=True):
    """Chat session for conversation history."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    """Individual chat messages."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id", index=True)
    role: str  # user, assistant
    content: str
    sources: Optional[str] = None  # JSON string of source references
    created_at: datetime = Field(default_factory=datetime.utcnow)
