#!/usr/bin/env python3
"""
Standalone migration script to add missing columns to the document table.
Run this script if the backend fails to start with "no such column" errors.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings


def main():
    print("Running database migration...")
    
    try:
        # Get database path from settings
        settings = get_settings()
        db_path = settings.chroma_path_resolved.parent / "localmind.db"
        
        print(f"Database file: {db_path}")
        
        # Check if database exists
        if not db_path.exists():
            print("Database file not found. It will be created automatically on first run.")
            return True
            
        # Run migration (we'll run it synchronously for simplicity)
        engine = create_engine(f"sqlite:///{db_path}")
        
        with engine.begin() as conn:
            # Check if document table exists first
            table_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='document'")
            ).fetchone() is not None
            
            if table_exists:
                # Check if columns exist
                columns_query = conn.execute(text("PRAGMA table_info(document)")).fetchall()
                existing_columns = [row[1] for row in columns_query]
                
                print(f"Existing columns: {existing_columns}")
                
                # Add processing_time if missing
                if "processing_time" not in existing_columns:
                    print("Adding processing_time column...")
                    conn.execute(text("ALTER TABLE document ADD COLUMN processing_time REAL"))
                
                # Add accelerator_used if missing
                if "accelerator_used" not in existing_columns:
                    print("Adding accelerator_used column...")
                    conn.execute(text("ALTER TABLE document ADD COLUMN accelerator_used TEXT"))
                    
                print("Migration completed successfully!")
            else:
                print("Document table not found. It will be created automatically on first run.")
                
        return True
        
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)