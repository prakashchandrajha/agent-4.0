"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import get_settings

settings = get_settings()

DATABASE_URL = f"sqlite+aiosqlite:///{settings.chroma_path_resolved.parent}/localmind.db"

engine = create_async_engine(DATABASE_URL, echo=False)


async def migrate_document_table() -> None:
    """Safety migration to add missing columns to document table."""
    async with engine.begin() as conn:
        # Check if document table exists first
        table_exists = await conn.run_sync(
            lambda sync_conn: sync_conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='document'")
            ).fetchone() is not None
        )
        
        if table_exists:
            # Check if columns exist
            columns_query = await conn.run_sync(
                lambda sync_conn: sync_conn.execute(
                    text("PRAGMA table_info(document)")
                ).fetchall()
            )
            
            existing_columns = [row[1] for row in columns_query]
            
            # Add processing_time if missing
            if "processing_time" not in existing_columns:
                await conn.run_sync(
                    lambda sync_conn: sync_conn.execute(
                        text("ALTER TABLE document ADD COLUMN processing_time REAL")
                    )
                )
            
            # Add accelerator_used if missing
            if "accelerator_used" not in existing_columns:
                await conn.run_sync(
                    lambda sync_conn: sync_conn.execute(
                        text("ALTER TABLE document ADD COLUMN accelerator_used TEXT")
                    )
                )


async def init_db() -> None:
    """Initialize database tables and apply migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        # Apply safety migration for existing databases
        await migrate_document_table()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSession(engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
