"""
Parser factory for document ingestion with automatic hardware acceleration.

This module provides a unified interface for parsing various document types
with automatic detection and utilization of available hardware accelerators.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Generator

from backend.services.parsers.excel_parser import parse_excel
from backend.services.parsers.image_parser import parse_image
from backend.services.parsers.pdf_parser import (
    parse_pdf,
    parse_pdf_streaming,
    get_ocr_engine,
    get_pdf_parser,
)
from backend.services.parsers.pptx_parser import parse_pptx
from backend.services.parsers.text_parser import parse_text
from backend.services.parsers.word_parser import parse_word
from backend.utils.hardware import detect_hardware, get_hardware_report_dict

logger = logging.getLogger(__name__)

# Type alias for parser functions
ParserFunc = Callable[[Path], list[dict[str, Any]]]

# Supported file types and their parsers
SUPPORTED_EXTENSIONS: dict[str, tuple[str, ParserFunc]] = {
    # PDF
    ".pdf": ("pdf", parse_pdf),
    # Word
    ".docx": ("word", parse_word),
    ".doc": ("word", parse_word),
    # Excel/CSV
    ".xlsx": ("excel", parse_excel),
    ".xls": ("excel", parse_excel),
    ".csv": ("csv", parse_excel),
    # Images
    ".jpg": ("image", parse_image),
    ".jpeg": ("image", parse_image),
    ".png": ("image", parse_image),
    ".webp": ("image", parse_image),
    ".bmp": ("image", parse_image),
    ".tiff": ("image", parse_image),
    ".tif": ("image", parse_image),
    # PowerPoint
    ".pptx": ("pptx", parse_pptx),
    # Text
    ".txt": ("text", parse_text),
    ".md": ("text", parse_text),
    ".markdown": ("text", parse_text),
    ".rst": ("text", parse_text),
    ".json": ("text", parse_text),
    ".xml": ("text", parse_text),
    ".yaml": ("text", parse_text),
    ".yml": ("text", parse_text),
}

MIME_TYPE_MAP = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/json": ".json",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "application/x-yaml": ".yaml",
    "text/yaml": ".yaml",
}


def get_file_type(filename: str, mime_type: str | None = None) -> str | None:
    """
    Determine file type from filename or MIME type.

    Args:
        filename: Original filename.
        mime_type: Optional MIME type.

    Returns:
        File type string or None if unsupported.
    """
    ext = Path(filename).suffix.lower()

    if ext in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[ext][0]

    if mime_type and mime_type in MIME_TYPE_MAP:
        mapped_ext = MIME_TYPE_MAP[mime_type]
        if mapped_ext in SUPPORTED_EXTENSIONS:
            return SUPPORTED_EXTENSIONS[mapped_ext][0]

    return None


def is_supported(filename: str, mime_type: str | None = None) -> bool:
    """Check if a file type is supported."""
    return get_file_type(filename, mime_type) is not None


def parser_factory(
    file_path: Path,
    mime_type: str | None = None,
    streaming: bool = False,
) -> list[dict[str, Any]] | Generator[dict[str, Any], None, None]:
    """
    Parse a document using the appropriate parser with automatic acceleration.

    Args:
        file_path: Path to the file.
        mime_type: Optional MIME type.
        streaming: If True, return a generator for memory-efficient processing.

    Returns:
        List of chunks with text and metadata, or generator if streaming=True.

    Raises:
        ValueError: If file type is not supported.
    """
    ext = file_path.suffix.lower()
    parser_func = None
    file_type = None

    if ext in SUPPORTED_EXTENSIONS:
        file_type, parser_func = SUPPORTED_EXTENSIONS[ext]
    elif mime_type and mime_type in MIME_TYPE_MAP:
        mapped_ext = MIME_TYPE_MAP[mime_type]
        if mapped_ext in SUPPORTED_EXTENSIONS:
            file_type, parser_func = SUPPORTED_EXTENSIONS[mapped_ext]

    if parser_func is None:
        raise ValueError(f"Unsupported file type: {ext} (mime: {mime_type})")

    # Use streaming mode for PDFs if requested
    if streaming and file_type == "pdf":
        return parse_pdf_streaming(file_path)

    return parser_func(file_path)


def get_supported_extensions() -> list[str]:
    """Get list of supported file extensions."""
    return list(SUPPORTED_EXTENSIONS.keys())


def get_supported_mime_types() -> list[str]:
    """Get list of supported MIME types."""
    return list(MIME_TYPE_MAP.keys())


def get_parser_status() -> dict[str, Any]:
    """
    Get status information about the parser system.
    
    Returns:
        Dict with hardware info, OCR engine status, and recommendations.
    """
    hardware = detect_hardware()
    ocr_engine = get_ocr_engine()
    pdf_parser = get_pdf_parser()
    
    return {
        "hardware": {
            "cpu_cores": hardware.cpu.total_cores,
            "cpu_name": hardware.cpu.name,
            "is_hybrid_cpu": hardware.cpu.is_hybrid,
            "ocr_threads": hardware.cpu.recommended_ocr_threads,
            "bg_threads": hardware.cpu.recommended_bg_threads,
        },
        "gpu": {
            "available": hardware.primary_gpu.is_available,
            "name": hardware.primary_gpu.name,
            "accelerator": hardware.primary_gpu.accelerator.value,
            "vram_gb": hardware.primary_gpu.vram_gb,
        },
        "ocr": {
            "engine": ocr_engine.engine_name,
            "gpu_accelerated": ocr_engine.engine_name in ("paddle_openvino", "paddle_cuda"),
        },
        "memory": {
            "is_low_memory": hardware.memory.is_low_memory,
            "streaming_enabled": hardware.recommendations.get("use_streaming_pipeline", False),
        },
        "display_string": hardware.display_string,
    }


# Export commonly used functions
__all__ = [
    "parser_factory",
    "get_file_type",
    "is_supported",
    "get_supported_extensions",
    "get_supported_mime_types",
    "get_parser_status",
    "parse_pdf",
    "parse_pdf_streaming",
    "parse_word",
    "parse_excel",
    "parse_image",
    "parse_pptx",
    "parse_text",
]
