"""Hardware detection and resource management for LocalMind Chameleon."""

import os
import platform
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any


class AcceleratorType(Enum):
    """Available accelerator types."""
    NVIDIA_CUDA = "nvidia_cuda"
    INTEL_OPENVINO = "intel_openvino"
    AMD_ROCM = "amd_rocm"
    CPU = "cpu"


class CoreType(Enum):
    """Intel hybrid core types."""
    P_CORE = "performance"
    E_CORE = "efficiency"
    STANDARD = "standard"


@dataclass
class CPUInfo:
    """CPU information."""
    name: str = ""
    total_cores: int = 1
    physical_cores: int = 1
    is_hybrid: bool = False
    p_cores: int = 0
    e_cores: int = 0
    recommended_ocr_threads: int = 1
    recommended_bg_threads: int = 1


@dataclass
class GPUInfo:
    """GPU information."""
    name: str = ""
    accelerator: AcceleratorType = AcceleratorType.CPU
    vram_gb: float = 0.0
    is_available: bool = False
    device_id: int = 0
    supports_fp16: bool = False


@dataclass
class MemoryInfo:
    """System memory information."""
    total_gb: float = 0.0
    available_gb: float = 0.0
    is_low_memory: bool = False  # < 8GB


@dataclass
class HardwareReport:
    """Complete hardware report."""
    cpu: CPUInfo = field(default_factory=CPUInfo)
    primary_gpu: GPUInfo = field(default_factory=GPUInfo)
    secondary_gpu: GPUInfo | None = None
    memory: MemoryInfo = field(default_factory=MemoryInfo)
    accelerator_priority: list[AcceleratorType] = field(default_factory=list)
    display_string: str = ""
    recommendations: dict[str, Any] = field(default_factory=dict)


def detect_cpu() -> CPUInfo:
    """Detect CPU capabilities including hybrid architecture."""
    info = CPUInfo()
    
    # Get basic info
    info.total_cores = os.cpu_count() or 1
    info.name = platform.processor() or "Unknown CPU"
    
    # Try to get physical core count
    try:
        import psutil
        info.physical_cores = psutil.cpu_count(logical=False) or info.total_cores
    except ImportError:
        # Estimate: assume hyperthreading
        info.physical_cores = max(1, info.total_cores // 2)
    
    # Detect Intel hybrid architecture (12th gen+)
    processor_lower = info.name.lower()
    
    # Check for Intel 12th gen+ (Alder Lake, Raptor Lake, etc.)
    intel_hybrid_patterns = [
        r"12\d{2,3}",  # 12th gen (12100, 12900, etc.)
        r"13\d{2,3}",  # 13th gen
        r"14\d{2,3}",  # 14th gen
        r"core.*(ultra|i[3579].*1[234]\d{2})",  # Core Ultra or i-series 12xx+
    ]
    
    is_intel = "intel" in processor_lower
    is_hybrid_gen = any(re.search(p, info.name, re.IGNORECASE) for p in intel_hybrid_patterns)
    
    if is_intel and is_hybrid_gen:
        info.is_hybrid = True
        # Estimate P/E core split (typical ratios)
        # 12th gen i7: 8P + 8E, i5: 6P + 8E, i3: 4P + 4E
        if info.physical_cores >= 16:
            info.p_cores = 8
            info.e_cores = info.physical_cores - 8
        elif info.physical_cores >= 10:
            info.p_cores = 6
            info.e_cores = info.physical_cores - 6
        else:
            info.p_cores = info.physical_cores // 2
            info.e_cores = info.physical_cores - info.p_cores
        
        # P-cores for OCR (compute intensive)
        info.recommended_ocr_threads = info.p_cores * 2  # With HT
        # E-cores for background tasks
        info.recommended_bg_threads = info.e_cores
    else:
        # Standard CPU - use all cores
        info.recommended_ocr_threads = max(1, info.total_cores - 1)
        info.recommended_bg_threads = max(1, info.total_cores // 4)
    
    return info


def detect_nvidia_gpu() -> GPUInfo | None:
    """Detect NVIDIA GPU via PyTorch CUDA."""
    try:
        import torch
        
        if not torch.cuda.is_available():
            return None
        
        device_id = 0
        props = torch.cuda.get_device_properties(device_id)
        
        return GPUInfo(
            name=props.name,
            accelerator=AcceleratorType.NVIDIA_CUDA,
            vram_gb=props.total_memory / (1024**3),
            is_available=True,
            device_id=device_id,
            supports_fp16=props.major >= 7,  # Volta+
        )
    except Exception:
        return None


def detect_intel_gpu() -> GPUInfo | None:
    """Detect Intel iGPU via OpenVINO."""
    try:
        from openvino import Core
        
        core = Core()
        devices = core.available_devices
        
        if "GPU" not in devices:
            return None
        
        # Get GPU info
        gpu_name = core.get_property("GPU", "FULL_DEVICE_NAME")
        
        return GPUInfo(
            name=gpu_name,
            accelerator=AcceleratorType.INTEL_OPENVINO,
            vram_gb=0,  # Shared memory, not easily queryable
            is_available=True,
            device_id=0,
            supports_fp16=True,  # Intel Xe supports FP16
        )
    except Exception:
        return None


def detect_amd_gpu() -> GPUInfo | None:
    """Detect AMD GPU via ROCm."""
    try:
        import torch
        
        if not hasattr(torch, 'hip') or not torch.cuda.is_available():
            return None
        
        # ROCm uses CUDA-like API
        if "AMD" not in torch.cuda.get_device_name(0).upper():
            return None
        
        props = torch.cuda.get_device_properties(0)
        
        return GPUInfo(
            name=props.name,
            accelerator=AcceleratorType.AMD_ROCM,
            vram_gb=props.total_memory / (1024**3),
            is_available=True,
            device_id=0,
            supports_fp16=True,
        )
    except Exception:
        return None


def detect_memory() -> MemoryInfo:
    """Detect system memory."""
    info = MemoryInfo()
    
    try:
        import psutil
        
        mem = psutil.virtual_memory()
        info.total_gb = mem.total / (1024**3)
        info.available_gb = mem.available / (1024**3)
        info.is_low_memory = info.total_gb < 8
    except ImportError:
        # Fallback: assume reasonable defaults
        info.total_gb = 8.0
        info.available_gb = 4.0
        info.is_low_memory = False
    
    return info


@lru_cache(maxsize=1)
def detect_hardware() -> HardwareReport:
    """
    Comprehensive hardware detection with priority fallback logic.
    
    Priority order for GPU acceleration:
    1. NVIDIA dGPU (CUDA) - Best for embeddings and ML
    2. Intel iGPU (OpenVINO) - Good for OCR and inference
    3. AMD GPU (ROCm) - If available
    4. CPU multi-threading - Universal fallback
    
    Returns:
        HardwareReport with all detected capabilities.
    """
    report = HardwareReport()
    
    # Detect CPU
    report.cpu = detect_cpu()
    
    # Detect GPUs in priority order
    nvidia = detect_nvidia_gpu()
    intel = detect_intel_gpu()
    amd = detect_amd_gpu()
    
    # Build accelerator priority list
    accelerators = []
    
    if nvidia:
        report.primary_gpu = nvidia
        accelerators.append(AcceleratorType.NVIDIA_CUDA)
        
        # Intel iGPU can be secondary for OCR
        if intel:
            report.secondary_gpu = intel
            accelerators.append(AcceleratorType.INTEL_OPENVINO)
    elif intel:
        report.primary_gpu = intel
        accelerators.append(AcceleratorType.INTEL_OPENVINO)
    elif amd:
        report.primary_gpu = amd
        accelerators.append(AcceleratorType.AMD_ROCM)
    
    # CPU is always available as fallback
    accelerators.append(AcceleratorType.CPU)
    report.accelerator_priority = accelerators
    
    # Detect memory
    report.memory = detect_memory()
    
    # Build display string
    parts = []
    parts.append(f"{report.cpu.total_cores} Threads")
    
    if report.primary_gpu.is_available:
        if report.primary_gpu.accelerator == AcceleratorType.NVIDIA_CUDA:
            parts.append(f"NVIDIA {report.primary_gpu.name} ({report.primary_gpu.vram_gb:.1f}GB)")
        elif report.primary_gpu.accelerator == AcceleratorType.INTEL_OPENVINO:
            parts.append(f"Intel {report.primary_gpu.name} (OpenVINO)")
        elif report.primary_gpu.accelerator == AcceleratorType.AMD_ROCM:
            parts.append(f"AMD {report.primary_gpu.name}")
    else:
        parts.append("CPU Fallback (Limited Speed)")
    
    report.display_string = " + ".join(parts)
    
    # Build recommendations
    report.recommendations = {
        "ocr_threads": report.cpu.recommended_ocr_threads,
        "bg_threads": report.cpu.recommended_bg_threads,
        "use_gpu_ocr": report.primary_gpu.accelerator in (
            AcceleratorType.INTEL_OPENVINO,
            AcceleratorType.NVIDIA_CUDA,
        ),
        "use_gpu_embeddings": report.primary_gpu.accelerator == AcceleratorType.NVIDIA_CUDA,
        "use_streaming_pipeline": report.memory.is_low_memory,
        "chunk_batch_size": 1 if report.memory.is_low_memory else 10,
        "embedding_device": (
            "cuda" if report.primary_gpu.accelerator == AcceleratorType.NVIDIA_CUDA
            else "cpu"
        ),
    }
    
    return report


def get_hardware_report_dict() -> dict[str, Any]:
    """Get hardware report as JSON-serializable dict."""
    report = detect_hardware()
    
    return {
        "cpu": {
            "name": report.cpu.name,
            "total_cores": report.cpu.total_cores,
            "physical_cores": report.cpu.physical_cores,
            "is_hybrid": report.cpu.is_hybrid,
            "p_cores": report.cpu.p_cores,
            "e_cores": report.cpu.e_cores,
        },
        "primary_gpu": {
            "name": report.primary_gpu.name,
            "accelerator": report.primary_gpu.accelerator.value,
            "vram_gb": report.primary_gpu.vram_gb,
            "is_available": report.primary_gpu.is_available,
            "supports_fp16": report.primary_gpu.supports_fp16,
        },
        "secondary_gpu": {
            "name": report.secondary_gpu.name,
            "accelerator": report.secondary_gpu.accelerator.value,
            "is_available": report.secondary_gpu.is_available,
        } if report.secondary_gpu else None,
        "memory": {
            "total_gb": round(report.memory.total_gb, 2),
            "available_gb": round(report.memory.available_gb, 2),
            "is_low_memory": report.memory.is_low_memory,
        },
        "accelerator_priority": [a.value for a in report.accelerator_priority],
        "display_string": report.display_string,
        "recommendations": report.recommendations,
    }


# Thread-local storage for worker affinity
_thread_local = threading.local()


def set_thread_affinity(core_type: CoreType) -> None:
    """
    Set thread affinity for hybrid CPUs.
    
    On Intel 12th gen+, this attempts to pin the current thread
    to either P-cores or E-cores based on workload type.
    """
    report = detect_hardware()
    
    if not report.cpu.is_hybrid:
        return
    
    try:
        import psutil
        
        process = psutil.Process()
        
        if core_type == CoreType.P_CORE:
            # P-cores are typically the first N cores
            p_core_mask = list(range(report.cpu.p_cores * 2))  # With HT
            process.cpu_affinity(p_core_mask)
        elif core_type == CoreType.E_CORE:
            # E-cores come after P-cores
            start = report.cpu.p_cores * 2
            e_core_mask = list(range(start, start + report.cpu.e_cores))
            process.cpu_affinity(e_core_mask)
    except Exception:
        pass  # Affinity setting is best-effort
