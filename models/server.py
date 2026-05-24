from __future__ import annotations

from dataclasses import dataclass

import modal

from .config import ModelConfig
from .image import build_image

VLLM_PORT = 8000
MINUTES = 60


@dataclass
class AppResources:
    app: modal.App
    image: modal.Image
    hf_vol: modal.Volume
    vllm_vol: modal.Volume
    cmd: list[str]
    gpu: str | list[str]
    scaledown: int
    timeout: int
    max_inputs: int
    auth_secret_name: str | None = None
    port: int = VLLM_PORT


def _modal_gpu(config: ModelConfig) -> str | list[str]:
    """Build Modal gpu= argument from config (string or fallback list)."""
    gpu_type = config.gpu.type
    if isinstance(gpu_type, list):
        return gpu_type
    return f"{gpu_type}:{config.gpu.count}"


def build_vllm_cmd(config: ModelConfig) -> list[str]:
    """Build the vllm serve command from config."""
    m = config.model
    v = config.vllm_args

    cmd = [
        "vllm",
        "serve",
        m.name,
        "--served-model-name",
        m.served_name,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--uvicorn-log-level=info",
        "--tensor-parallel-size",
        str(config.gpu.count),
    ]

    if m.revision:
        cmd += ["--revision", m.revision]

    if v.async_scheduling:
        cmd.append("--async-scheduling")

    cmd.append("--enforce-eager" if config.scaling.fast_boot else "--no-enforce-eager")

    cmd.extend(v.extra_args)

    return cmd


def prepare_app(config: ModelConfig) -> AppResources:
    """
    Build and return all Modal resources needed to define the serve function.

    The serve() function itself must be defined at module level in main.py so
    that Modal can import it by name — a function defined inside another
    function is a local/closure and cannot be imported without serialization,
    which requires matching Python versions between local and remote.
    """
    return AppResources(
        app=modal.App(config.app_name),
        image=build_image(config),
        hf_vol=modal.Volume.from_name(config.volumes.hf_cache, create_if_missing=True),
        vllm_vol=modal.Volume.from_name(
            config.volumes.vllm_cache, create_if_missing=True
        ),
        cmd=build_vllm_cmd(config),
        gpu=_modal_gpu(config),
        scaledown=config.scaling.scaledown_window_minutes * MINUTES,
        timeout=config.scaling.timeout_minutes * MINUTES,
        max_inputs=config.scaling.max_concurrent_inputs,
        auth_secret_name=config.auth.token_name if config.auth else None,
    )
