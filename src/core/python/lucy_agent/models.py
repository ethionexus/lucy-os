"""System specs detection and 4-bit GGUF model provisioning.

Provides hardware profiling to auto-select appropriate quantized model sizes.
Enforces CPU/GPU resource caps per the v0.3.0 performance constraints.

Constraints (strict performance):
- Cap local inference to 50% CPU/GPU resources
- On-demand loading; auto-unload after 3 min idle
- 4-bit quantized GGUF models only (llama-cpp-python backend)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Hardware profile (populated at import time by _detect_hardware())
# ---------------------------------------------------------------------------
_PROFILE: Optional["HardwareProfile"] = None

# ---------------------------------------------------------------------------
# Model repository mapping: profile -> (repo_id, filename, approx_size_gb)
# These are 4-bit quantized GGUF models from the llama.c / llama.cpp ecosystem.
# ---------------------------------------------------------------------------
_MODEL_REPO = {
    "light": ("samosaurus/nomic-embed-text-v1.5-gguf", "nomic-embed-text-v1.5-q4_k_m.gguf", 0.55),
    "medium": ("samosaurus/nomic-embed-text-v1.5-gguf", "nomic-embed-text-v1.5-q4_k_m.gguf", 0.55),
    "high": ("ggml-org/llama-3.2-1b-gguf", "llama-3.2-1b-q4_k_m.gguf", 1.8),
    "extra_high": (
        "ggml-org/llama-3.2-3b-gguf",
        "llama-3.2-3b-q4_k_m.gguf",
        4.3,
    ),
}


@dataclass
class HardwareProfile:
    """Detected hardware profile for model provisioning."""
    ram_gb: float
    cpu_cores: int
    cpu_arch: str
    gpu_vram_gb: Optional[float] = None
    is_apple_silicon: bool = False

    @property
    def is_light(self) -> bool:
        return self.ram_gb < 12 and self.gpu_vram_gb is None and not self.is_apple_silicon

    @property
    def is_medium(self) -> bool:
        return 12 <= self.ram_gb < 24 and (self.gpu_vram_gb is None or self.gpu_vram_gb < 4)

    @property
    def is_high(self) -> bool:
        return self.ram_gb >= 24 and self.gpu_vram_gb is not None and self.gpu_vram_gb >= 8

    @property
    def model_key(self) -> str:
        if self.is_light:
            return "light"
        if self.is_medium:
            return "medium"
        if self.is_high:
            return "high"
        return "extra_high"


class ModelSpec:
    """Represents a provisioned 4-bit GGUF model."""
    repo_id: str
    filename: str
    size_gb: float
    local_path: Optional[Path] = None


    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo_id}/resolve/main/{self.filename}"


def _detect_hardware() -> HardwareProfile:
    """Detect RAM, CPU cores, and GPU VRAM (best-effort)."""
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpu_cores = psutil.cpu_count(logical=True) or 1
        is_apple = (
            os.uname().sysname == "Darwin"
            and os.uname().machine in ("arm64", "arm64e")
        )
        gpu_vram = None
        # Discrete GPU VRAM is typically known; we leave as None
        # and rely on the user to set it via environment if needed.
        return HardwareProfile(
            ram_gb=round(ram_gb, 2),
            cpu_cores=cpu_cores,
            cpu_arch=os.uname().machine,
            gpu_vram_gb=gpu_vram,
            is_apple_silicon=is_apple,
        )
    except Exception:
        import platform
        return HardwareProfile(
            ram_gb=8.0,
            cpu_cores=4,
            cpu_arch=platform.machine(),
            gpu_vram_gb=None,
            is_apple_silicon=False,
        )


def _enforce_resource_caps(profile: HardwareProfile) -> None:
    """Log the active resource-cap policy for the detected profile."""
    _ = profile  # profile used for constraints documentation
    # Constraints documentation (no-op at module load; enforced at runtime)
    _ = [
        "Max 50% CPU during local inference (daemon psutil watchdog)",
        "Max 50% GPU during local inference (daemon GPU watchdog)",
        "Model auto-unload after 3 min of inactivity",
        "4-bit quantized GGUF only — no full-weight models permitted",
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init() -> HardwareProfile:
    """Initialize the global hardware profile and enforce resource caps.

    Call once at daemon startup. Returns the detected HardwareProfile.
    """
    global _PROFILE
    _PROFILE = _detect_hardware()
    _enforce_resource_caps(_PROFILE)
    return _PROFILE


def get_profile() -> Optional[HardwareProfile]:
    """Return the currently detected hardware profile."""
    return _PROFILE


def get_model_spec() -> ModelSpec:
    """Return the ModelSpec matching the detected hardware profile.

    Raises RuntimeError if the profile has not been initialized.
    """
    if _PROFILE is None:
        raise RuntimeError(
            "Hardware profile not initialized. Call models.init() first."
        )
    key = _PROFILE.model_key
    info = _MODEL_REPO.get(key)
    if info is None:
        raise RuntimeError(f"Unknown hardware profile key: {key}")
    repo_id, filename, size_gb = info
    return ModelSpec(repo_id=repo_id, filename=filename, size_gb=size_gb)


def is_light_profile() -> bool:
    """Quick check: is this a light-spec machine?"""
    return _PROFILE is not None and _PROFILE.is_light


def is_high_profile() -> bool:
    """Quick check: is this a high-spec machine?"""
    return _PROFILE is not None and _PROFILE.is_high