"""
PDF file parser with Producer-Consumer pattern and GPU acceleration.

Features:
- Producer-Consumer pattern for parallel processing
- Automatic GPU acceleration (Intel OpenVINO / NVIDIA CUDA)
- Memory-adaptive streaming pipeline
- Hybrid CPU core awareness for Intel 12th gen+
"""

import gc
import io
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

import fitz  # PyMuPDF
from PIL import Image

from backend.config import get_settings
from backend.utils.hardware import (
    AcceleratorType,
    CoreType,
    detect_hardware,
    set_thread_affinity,
)
from backend.services.parsers.utils import is_readable_text

logger = logging.getLogger(__name__)


@dataclass
class PageTask:
    """Task for processing a single PDF page."""
    page_num: int
    page_data: bytes  # Serialized page data
    file_name: str


@dataclass
class PageResult:
    """Result from processing a single PDF page."""
    page_num: int
    text: str
    metadata: dict[str, Any]
    success: bool
    error: str | None = None


class OCREngine:
    """
    Unified OCR engine with automatic acceleration.
    
    Priority:
    1. Intel OpenVINO (iGPU) - If available via PaddleOCR
    2. NVIDIA CUDA - Via Tesseract with GPU preprocessing
    3. CPU Multi-threaded - Tesseract fallback
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.settings = get_settings()
        self.hardware = detect_hardware()
        self._engine_type = None
        self._paddle_ocr = None
        self._tesseract_available = False
        
        self._init_engine()
        self._initialized = True
    
    def _init_engine(self) -> None:
        """Initialize the best available OCR engine."""
        # Try Intel OpenVINO via PaddleOCR
        if self._try_init_paddle_openvino():
            self._engine_type = "paddle_openvino"
            logger.info("OCR using PaddleOCR with Intel OpenVINO acceleration")
            return
        
        # Try PaddleOCR with CUDA
        if self._try_init_paddle_cuda():
            self._engine_type = "paddle_cuda"
            logger.info("OCR using PaddleOCR with NVIDIA CUDA acceleration")
            return
        
        # Fallback to Tesseract
        if self._try_init_tesseract():
            self._engine_type = "tesseract"
            logger.info(f"OCR using Tesseract with {self.hardware.cpu.recommended_ocr_threads} threads")
            return
        
        self._engine_type = "none"
        logger.warning("No OCR engine available - scanned PDFs will have limited extraction")
    
    def _try_init_paddle_openvino(self) -> bool:
        """Try to initialize PaddleOCR with OpenVINO."""
        try:
            # Check if OpenVINO GPU is available
            from openvino import Core
            core = Core()
            if "GPU" not in core.available_devices:
                return False
            
            from paddleocr import PaddleOCR
            
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=True,
                enable_mkldnn=True,
                use_openvino=True,
            )
            return True
        except Exception:
            return False
    
    def _try_init_paddle_cuda(self) -> bool:
        """Try to initialize PaddleOCR with CUDA."""
        if self.hardware.primary_gpu.accelerator != AcceleratorType.NVIDIA_CUDA:
            return False
        
        try:
            from paddleocr import PaddleOCR
            
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=True,
            )
            return True
        except Exception:
            return False
    
    def _try_init_tesseract(self) -> bool:
        """Try to initialize Tesseract OCR."""
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd
            # Test if tesseract is available
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
            return True
        except Exception:
            return False
    
    def ocr_image(self, image: Image.Image) -> str:
        """
        Perform OCR on an image using the best available engine.
        
        Args:
            image: PIL Image to process.
            
        Returns:
            Extracted text.
        """
        if self._engine_type == "none":
            return ""
        
        if self._engine_type in ("paddle_openvino", "paddle_cuda"):
            return self._ocr_paddle(image)
        
        return self._ocr_tesseract(image)
    
    def _ocr_paddle(self, image: Image.Image) -> str:
        """OCR using PaddleOCR."""
        try:
            import numpy as np
            
            # Convert PIL to numpy
            img_array = np.array(image)
            
            result = self._paddle_ocr.ocr(img_array, cls=True)
            
            if not result or not result[0]:
                return ""
            
            # Extract text from result
            lines = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0] if isinstance(line[1], tuple) else line[1]
                    lines.append(text)
            
            return "\n".join(lines)
        except Exception as e:
            logger.debug(f"PaddleOCR failed: {e}")
            return ""
    
    def _ocr_tesseract(self, image: Image.Image) -> str:
        """OCR using Tesseract."""
        try:
            import pytesseract
            
            # Set thread affinity to P-cores for OCR (compute intensive)
            set_thread_affinity(CoreType.P_CORE)
            
            # Use optimal thread count
            config = f"--oem 3 --psm 3 -c tessedit_parallelize={self.hardware.cpu.recommended_ocr_threads}"
            
            text = pytesseract.image_to_string(image, config=config)
            return text.strip()
        except Exception as e:
            logger.debug(f"Tesseract OCR failed: {e}")
            return ""
    
    @property
    def engine_name(self) -> str:
        """Get the name of the active OCR engine."""
        return self._engine_type or "none"


def get_ocr_engine() -> OCREngine:
    """Get singleton OCR engine instance."""
    return OCREngine()


class PDFParser:
    """
    Memory-adaptive PDF parser with Producer-Consumer pattern.
    
    Processes PDFs page-by-page to minimize memory usage:
    Read 1 page -> OCR -> Yield result -> Clear RAM
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.hardware = detect_hardware()
        self.ocr_engine = get_ocr_engine()
        
        # Determine worker count
        self._num_workers = self.hardware.cpu.recommended_ocr_threads
        
        # Adaptive settings based on memory
        self._use_streaming = self.hardware.recommendations.get("use_streaming_pipeline", False)
    
    def parse(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Parse PDF file with automatic optimization.
        
        For low-memory systems, uses streaming pipeline.
        For high-memory systems, uses parallel processing.
        
        Args:
            file_path: Path to the PDF file.
            
        Returns:
            List of chunks with text and metadata per page.
        """
        t_start = time.perf_counter()

        if self._use_streaming:
            # Streaming mode for low memory - process one page at a time
            result = list(self.parse_streaming(file_path))
        else:
            # Parallel mode for high memory - use Producer-Consumer
            result = self._parse_parallel(file_path)

        elapsed = time.perf_counter() - t_start
        mode = "streaming" if self._use_streaming else "parallel"
        logger.info(
            "PDF parsed %s in %.2fs (%s mode, %d workers, OCR engine: %s)",
            file_path.name,
            elapsed,
            mode,
            self._num_workers,
            self.ocr_engine.engine_name,
        )
        return result
    
    def parse_streaming(self, file_path: Path) -> Generator[dict[str, Any], None, None]:
        """
        Generator-based streaming parser for memory efficiency.
        
        Processes one page at a time:
        Read -> OCR -> Yield -> Clear RAM
        
        Args:
            file_path: Path to the PDF file.
            
        Yields:
            Chunks with text and metadata per page.
        """
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e}") from e
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text("text").strip()
                word_count = len(text.split()) if text else 0
                
                # OCR if needed
                if word_count < 50:
                    ocr_text = self._ocr_page(page)
                    if ocr_text and len(ocr_text.split()) > word_count:
                        text = ocr_text
                
                if text:
                    if not is_readable_text(text):
                        logger.debug(f"[PDF] Skipping low-quality page {page_num}")
                        text = ""
                
                if text:
                    yield {
                        "text": text,
                        "metadata": {
                            "source": file_path.name,
                            "file_type": "pdf",
                            "page_or_sheet_or_slide": page_num + 1,
                        },
                    }
                
                # Clear page from memory
                page = None
                gc.collect()
                
        finally:
            doc.close()
    
    def _parse_parallel(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Producer-Consumer parallel parser for high-memory systems.
        
        Producer: Reads pages into queue
        Consumers: OCR workers process pages in parallel
        """
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF: {e}") from e
        
        total_pages = len(doc)
        results: dict[int, PageResult] = {}
        
        # Use thread pool for parallel OCR
        with ThreadPoolExecutor(max_workers=self._num_workers) as executor:
            futures = {}
            
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Submit OCR task
                future = executor.submit(
                    self._process_page,
                    page_num,
                    page,
                    file_path.name,
                )
                futures[future] = page_num
            
            # Collect results
            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    result = future.result()
                    results[page_num] = result
                except Exception as e:
                    logger.error(f"Failed to process page {page_num}: {e}")
                    results[page_num] = PageResult(
                        page_num=page_num,
                        text="",
                        metadata={},
                        success=False,
                        error=str(e),
                    )
        
        doc.close()
        
        # Build output in page order
        chunks = []
        for page_num in sorted(results.keys()):
            result = results[page_num]
            if result.success and result.text:
                chunks.append({
                    "text": result.text,
                    "metadata": result.metadata,
                })
        
        return chunks
    
    def _process_page(
        self,
        page_num: int,
        page: fitz.Page,
        file_name: str,
    ) -> PageResult:
        """
        Process a single PDF page.
        
        Args:
            page_num: Page number (0-indexed).
            page: PyMuPDF page object.
            file_name: Source file name.
            
        Returns:
            PageResult with extracted text.
        """
        try:
            # Extract text
            text = page.get_text("text").strip()
            word_count = len(text.split()) if text else 0
            
            # OCR if needed
            if word_count < 50:
                ocr_text = self._ocr_page(page)
                if ocr_text and len(ocr_text.split()) > word_count:
                    text = ocr_text
            
            if text and not is_readable_text(text):
                logger.debug(f"[PDF] Skipping low-quality page {page_num}")
                text = ""

            return PageResult(
                page_num=page_num,
                text=text,
                metadata={
                    "source": file_name,
                    "file_type": "pdf",
                    "page_or_sheet_or_slide": page_num + 1,
                },
                success=True,
            )
        except Exception as e:
            return PageResult(
                page_num=page_num,
                text="",
                metadata={},
                success=False,
                error=str(e),
            )
    
    def _ocr_page(self, page: fitz.Page) -> str:
        """
        Perform OCR on a PDF page using the unified OCR engine.
        
        Args:
            page: PyMuPDF page object.
            
        Returns:
            Extracted text from OCR.
        """
        try:
            # Render page to image at 300 DPI for better OCR
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Run OCR using unified engine
            text = self.ocr_engine.ocr_image(img)
            
            # Clean up
            del pix
            del img_data
            img.close()
            
            return text
        except Exception as e:
            logger.debug(f"OCR failed for page: {e}")
            return ""


# Module-level singleton
_parser: PDFParser | None = None


def get_pdf_parser() -> PDFParser:
    """Get singleton PDF parser instance."""
    global _parser
    if _parser is None:
        _parser = PDFParser()
    return _parser


def parse_pdf(file_path: Path) -> list[dict[str, Any]]:
    """
    Parse PDF files using automatic optimization.
    
    Convenience function that uses the singleton parser.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        List of chunks with text and metadata per page.
    """
    return get_pdf_parser().parse(file_path)


def parse_pdf_streaming(file_path: Path) -> Generator[dict[str, Any], None, None]:
    """
    Parse PDF files using streaming mode.
    
    Memory-efficient generator that processes one page at a time.
    
    Args:
        file_path: Path to the PDF file.
        
    Yields:
        Chunks with text and metadata per page.
    """
    yield from get_pdf_parser().parse_streaming(file_path)
