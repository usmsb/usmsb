"""
GPU Monitor
"""

import subprocess
from typing import Dict, List, Optional


class GPUMonitor:
    """
    GPU information monitor
    """

    def __init__(self):
        self.has_nvidia_smi = self._check_nvidia_smi()

    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available"""
        try:
            subprocess.run(
                ["nvidia-smi", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_gpu_info(self) -> Dict:
        """
        Get GPU information

        Returns:
            {
                "gpu_count": int,
                "gpu_type": str,
                "total_vram_gb": int,
                "gpus": [{"id": 0, "vram_gb": 80, "utilization": 0.1}, ...]
            }
        """
        if not self.has_nvidia_smi:
            # No GPU, return mock data (for development testing)
            return {
                "gpu_count": 1,
                "gpu_type": "RTX 4090",
                "total_vram_gb": 24,
                "gpus": [{"id": 0, "vram_gb": 24, "utilization": 0.0, "used_vram_gb": 0}]
            }

        # Parse nvidia-smi
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,utilization.gpu,memory.used",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        gpus = []
        total_vram = 0

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue

            idx, name, mem_total, util, mem_used = parts[:5]
            vram = int(mem_total)
            total_vram += vram

            gpus.append({
                "id": int(idx),
                "name": name,
                "vram_gb": vram,
                "utilization": float(util) / 100.0,
                "used_vram_gb": int(mem_used)
            })

        gpu_type = gpus[0]["name"] if gpus else "Unknown"

        return {
            "gpu_count": len(gpus),
            "gpu_type": gpu_type,
            "total_vram_gb": total_vram,
            "gpus": gpus
        }

    def get_available_vram(self) -> int:
        """Get available VRAM (GB)"""
        info = self.get_gpu_info()
        total = info["total_vram_gb"]
        used = sum(g["used_vram_gb"] for g in info["gpus"])
        return total - used
