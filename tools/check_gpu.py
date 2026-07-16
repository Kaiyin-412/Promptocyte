"""Print the PyTorch CUDA configuration used by PromptSentinel training."""
from __future__ import annotations

import shutil
import subprocess

import torch


def nvidia_smi() -> str:
    command = shutil.which("nvidia-smi")
    if not command:
        return "nvidia-smi unavailable"
    try:
        output = subprocess.check_output(
            [command, "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.STDOUT,
        )
        return output.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        return f"nvidia-smi query failed: {error}"


def main() -> None:
    available = torch.cuda.is_available()
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {available}")
    print(f"CUDA version (PyTorch build): {torch.version.cuda or 'None (CPU-only build)'}")
    print(f"Current device: {torch.cuda.current_device() if available else 'CPU'}")
    if available:
        index = torch.cuda.current_device()
        print(f"GPU name: {torch.cuda.get_device_name(index)}")
        print(f"Compute capability: {torch.cuda.get_device_capability(index)}")
        print(f"GPU memory allocated: {torch.cuda.memory_allocated(index) / 1024**2:.1f} MiB")
        print(f"GPU memory reserved: {torch.cuda.memory_reserved(index) / 1024**2:.1f} MiB")
        print(f"BF16 supported: {torch.cuda.is_bf16_supported()}")
    print(f"nvidia-smi: {nvidia_smi()}")


if __name__ == "__main__":
    main()
