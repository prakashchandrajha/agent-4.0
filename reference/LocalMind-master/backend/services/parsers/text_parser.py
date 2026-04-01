"""Text and Markdown file parser."""

from pathlib import Path
from typing import Any


def parse_text(file_path: Path) -> list[dict[str, Any]]:
    """
    Parse plain text or markdown files.

    Args:
        file_path: Path to the text file.

    Returns:
        List of chunks with text and metadata.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    if not content.strip():
        return []

    return [
        {
            "text": content,
            "metadata": {
                "source": file_path.name,
                "file_type": "text",
                "page_or_sheet_or_slide": 1,
            },
        }
    ]
