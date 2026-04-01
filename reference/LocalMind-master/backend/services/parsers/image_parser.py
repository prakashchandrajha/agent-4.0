"""Image parser with OCR and optional LLM vision support."""

import base64
from pathlib import Path
from typing import Any

from PIL import Image

from backend.config import get_settings


def parse_image(file_path: Path) -> list[dict[str, Any]]:
    """
    Parse image files using OCR, with optional LLM vision fallback.

    Args:
        file_path: Path to the image file.

    Returns:
        List containing single chunk with extracted text.
    """
    settings = get_settings()

    try:
        img = Image.open(file_path)
        img.verify()  # Verify it's a valid image
        img = Image.open(file_path)  # Reopen after verify
    except Exception as e:
        raise ValueError(f"Failed to open image: {e}") from e

    # Try OCR first
    ocr_text = _run_ocr(file_path, settings.tesseract_cmd)
    word_count = len(ocr_text.split()) if ocr_text else 0

    text = ocr_text

    # If OCR result is poor, try LLM vision (if available)
    if word_count < 20:
        vision_text = _try_vision_description(file_path, settings)
        if vision_text:
            text = vision_text
        elif not text:
            text = f"Image: {file_path.name} - content not extractable"

    return [
        {
            "text": text,
            "metadata": {
                "source": file_path.name,
                "file_type": "image",
                "page_or_sheet_or_slide": 1,
                "extraction_method": "ocr" if word_count >= 20 else "vision",
            },
        }
    ]


def _run_ocr(file_path: Path, tesseract_cmd: str) -> str:
    """
    Run OCR on an image file.

    Args:
        file_path: Path to the image.
        tesseract_cmd: Path to tesseract executable.

    Returns:
        Extracted text.
    """
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        img = Image.open(file_path)

        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        text = pytesseract.image_to_string(img)
        return text.strip()

    except Exception:
        return ""


def _try_vision_description(file_path: Path, settings) -> str:
    """
    Try to get image description using LLM vision model.

    Args:
        file_path: Path to the image.
        settings: Application settings.

    Returns:
        Image description or empty string.
    """
    if settings.llm_backend != "ollama":
        return ""

    try:
        import httpx

        # Check if llava model is available
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        if response.status_code != 200:
            return ""

        models = response.json().get("models", [])
        vision_model = None

        for model in models:
            name = model.get("name", "").lower()
            if "llava" in name or "vision" in name:
                vision_model = model.get("name")
                break

        if not vision_model:
            return ""

        # Encode image to base64
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Call vision model
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": vision_model,
                "prompt": "Describe this image in detail. What text, objects, or information does it contain?",
                "images": [image_data],
                "stream": False,
            },
            timeout=60,
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()

    except Exception:
        pass

    return ""
