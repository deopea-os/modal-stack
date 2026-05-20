# Modal LLM serving entrypoint.
#
# Select a model config via the MODEL_CONFIG env var (deploy) or
# the --config flag (run/test). Both resolve to configs/<name>.yaml.
#
# Deploy:
#   MODEL_CONFIG=gemma4_26b modal deploy main.py
#
# Test (spins up a fresh replica and runs a health check):
#   modal run main.py -- --config gemma4_26b

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve the config name at import time so both `modal deploy` and
# `modal run` work. Modal passes everything after `--` into sys.argv.
# ---------------------------------------------------------------------------
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--config", default=None, metavar="NAME")
_known, _ = _parser.parse_known_args()

_config_name: str | None = os.environ.get("MODEL_CONFIG") or _known.config

if _config_name is None:
    print(
        "No model config specified.\n"
        "  Deploy:  MODEL_CONFIG=gemma4_26b modal deploy main.py\n"
        "  Test:    modal run main.py -- --config gemma4_26b",
        file=sys.stderr,
    )
    sys.exit(1)

_configs_dir = Path(__file__).parent / "configs"
_config_path = _configs_dir / f"{_config_name}.yaml"

if not _config_path.exists():
    available = sorted(p.stem for p in _configs_dir.glob("*.yaml") if not p.stem.startswith("_"))
    print(
        f"Config '{_config_name}' not found at {_config_path}\n"
        f"Available configs: {', '.join(available) or '(none)'}",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Load config and wire up the Modal app.
# ---------------------------------------------------------------------------
import modal

from models.config import ModelConfig
from models.health import run_health_check
from models.server import prepare_app

config = ModelConfig.from_yaml(_config_path)
_r = prepare_app(config)

_root = Path(__file__).parent

# Bake the config file and the models package into the container image.
# Modal automounts main.py but not data files or local packages reliably.
_image = (
    _r.image
    .env({"MODEL_CONFIG": _config_name})
    .add_local_file(str(_config_path), f"/root/configs/{_config_name}.yaml")
    .add_local_dir(str(_root / "models"), "/root/models")
)

app = _r.app
_cmd = _r.cmd
_served_name = config.model.served_name
_timeout_s = _r.timeout


@app.function(
    image=_image,
    gpu=_r.gpu,
    scaledown_window=_r.scaledown,
    timeout=_r.timeout,
    volumes={
        "/root/.cache/huggingface": _r.hf_vol,
        "/root/.cache/vllm": _r.vllm_vol,
    },
)
@modal.concurrent(max_inputs=_r.max_inputs)
@modal.web_server(port=_r.port, startup_timeout=_r.timeout)
def serve():
    import subprocess
    subprocess.Popen(_cmd)


@app.local_entrypoint()
async def test():
    await run_health_check(serve, _served_name, _timeout_s)
