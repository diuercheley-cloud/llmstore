import logging
import os
import platform
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareSpecs:
    cpu_count: int
    memory_total_gb: float
    gpu_count: int
    gpu_type: str
    vram_total_gb: float
    cuda_available: bool
    platform: str


def detect_hardware() -> HardwareSpecs:
    try:
        cpu_count = os.cpu_count() or 0
        memory_total_gb = _get_total_memory_gb()
        gpu_info = _get_gpu_info()

        return HardwareSpecs(
            cpu_count=cpu_count,
            memory_total_gb=memory_total_gb,
            gpu_count=gpu_info.get("count", 0),
            gpu_type=gpu_info.get("type", "unknown"),
            vram_total_gb=gpu_info.get("vram_gb", 0.0),
            cuda_available=gpu_info.get("cuda", False),
            platform=platform.system(),
        )
    except Exception as e:
        logger.error(f"Hardware detection failed: {e}")
        return HardwareSpecs(
            cpu_count=0,
            memory_total_gb=0.0,
            gpu_count=0,
            gpu_type="unknown",
            vram_total_gb=0.0,
            cuda_available=False,
            platform=platform.system(),
        )


def _get_total_memory_gb() -> float:
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        return kb / (1024 * 1024)
        # Fallback/Other platforms
        return 0.0
    except Exception:
        return 0.0


def _get_gpu_info() -> dict:
    info = {"count": 0, "type": "unknown", "vram_gb": 0.0, "cuda": False}
    try:
        # Try nvidia-smi
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            lines = res.stdout.strip().split("\n")
            info["count"] = len(lines)
            info["cuda"] = True
            if lines:
                parts = lines[0].split(",")
                info["type"] = parts[0].strip()
                total_vram_mb = sum(float(l.split(",")[1]) for l in lines)
                info["vram_gb"] = total_vram_mb / 1024.0
    except Exception:
        pass

    return info
