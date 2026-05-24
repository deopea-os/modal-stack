# Modal LLM Serving

Config-driven infrastructure for deploying OpenAI-compatible LLM inference endpoints on [Modal](https://modal.com/) using [vLLM](https://docs.vllm.ai/).

Each model is described by a single YAML file. Adding a new model is as simple as creating a new config and running `agents deploy`.

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Modal](https://modal.com/) account with the CLI installed and authenticated

```bash
pip install modal
modal setup
```

### Install dependencies

```bash
# Using uv (recommended — matches the project's .venv setup)
uv pip install -e .

# Using pip
pip install -r requirements.txt
```

> The `agents` command is installed into the virtual environment. Activate it first (`source .venv/bin/activate`) or prefix commands with `.venv/bin/agents` if you prefer not to activate.

### Deploy a model

```bash
agents deploy gemma4_26b

# With API auth:
agents deploy gemma4_26b -t my-llm-auth
```

### Test a deployed model

```bash
agents run gemma4_26b
```

This spins up a fresh container, runs a `/health` check, then sends a single streaming chat completion request.

### Deployment planning (GPU / model tiers)

For Modal GPU and model tier recommendations (three-tier stack, cost estimates, benchmarks), see:

- [docs/modal-llm-deployment-recommendation.md](docs/modal-llm-deployment-recommendation.md) — full write-up
- [canvases/final-recommendation.canvas.tsx](canvases/final-recommendation.canvas.tsx) — interactive charts and comparison (open in Cursor)

---

## Project Structure

```
agents/
├── cli.py                # `agents` console script (deploy / run subcommands)
├── main.py               # Modal entrypoint — loads config, wires up Modal app
├── pyproject.toml        # Project metadata and dependencies
├── requirements.txt      # Pinned requirements (derived from pyproject.toml)
│
├── configs/
│   ├── gemma4_26b.yaml                  # Gemma 4 26B deployment config
│   ├── qwen2_5_coder_7b.yaml            # Tier 1 — Qwen2.5-Coder-7B on L4
│   ├── qwen3_coder_next_rtx_pro_6000.yaml # Tier 2 — Qwen3-Coder-Next on RTX PRO 6000
│   ├── qwen3_coder_next_h200.yaml         # Tier 3 — Qwen3-Coder-Next on H200 (256K)
│   └── _example.yaml                      # Annotated template for new models
│
├── docs/
│   └── modal-llm-deployment-recommendation.md
│
├── canvases/
│   └── final-recommendation.canvas.tsx
│
└── models/
    ├── config.py         # Pydantic schema — validates YAML at load time
    ├── image.py          # Modal container Image factory
    ├── server.py         # Modal App factory + vLLM command builder
    └── health.py         # Health check local_entrypoint
```

---

## How It Works

```
agents deploy <name>
         │
         ▼  (sets MODEL_CONFIG=<name>, calls modal deploy main.py)
    main.py resolves configs/<name>.yaml
         │
         ▼
    ModelConfig.from_yaml() validates via Pydantic
         │
         ▼
    create_app(config) in models/server.py
         │
         ├─ build_image(config)     → Modal container Image (vLLM installed)
         ├─ modal.Volume.from_name  → shared HF + vLLM caches
         └─ @app.function           → GPU-backed web server running vllm serve
```

The deployed function is a `@modal.web_server` that exposes an OpenAI-compatible API at a public Modal URL.

---

## Adding a New Model

1. Copy the template:

   ```bash
   cp configs/_example.yaml configs/my_model.yaml
   ```

2. Edit `configs/my_model.yaml` — only `model.name` is required:

   ```yaml
   model:
     name: "meta-llama/Llama-3.1-8B-Instruct"
   ```

3. Deploy:

   ```bash
   agents deploy my_model
   ```

That's it. GPU, scaling, image, and volume settings all have sensible defaults.

### Test without deploying

```bash
agents run my_model
```

---

<!-- BEGIN GENERATED CONFIG REFERENCE -->
## Config Reference

All fields except `model.name` are optional. Defaults are shown below.

### Top-level

| Field | Required | Default | Description |
| ----- | -------- | ------- | ----------- |
| `app_name` | No | Slug from `model.name` | Modal app name used to identify this deployment. |
| `model` | Yes | — | Model identity and serving name configuration |
| `engine` | No | See below | LLM serving engine configuration |
| `gpu` | No | See below | GPU hardware configuration for the Modal deployment |
| `scaling` | No | See below | Autoscaling, timeout, and concurrency settings for the Modal deployment |
| `vllm_args` | No | See below | Arguments passed to the 'vllm serve' command |
| `image` | No | See below | Container image settings |
| `volumes` | No | See below | Modal Volume names for persistent caching |
| `auth` | No | See below | Optional Bearer token authentication for the OpenAI-compatible API |

### `model`

| Field | Required | Default | Description |
| ----- | -------- | ------- | ----------- |
| `name` | **Yes** | — | Hugging Face repository ID for the model weights. |
| `revision` | No | `null` | Git commit hash to pin model weights to a specific version. |
| `served_name` | No | `"llm"` | The model name that clients send in the OpenAI API 'model' field when making requests. |

### `engine`

| Field | Default | Description |
| ----- | ------- | ----------- |
| `type` | `"vllm"` | Serving engine type. |
| `version` | `"0.19.0"` | Version of the serving engine (vLLM) to install via pip in the container image. |
| `extra_pip` | `[]` | Additional pip packages installed alongside the serving engine. |

### `gpu`

| Field | Default | Description |
| ----- | ------- | ----------- |
| `type` | `"H200"` | Modal GPU type or fallback list. |
| `count` | `1` | Number of GPUs per replica. |

**Available GPU types:**

| GPU | Memory | Architecture | Max Count | Notes |
| --- | ------ | ------------ | --------- | ----- |
| `T4` | 16 GB | Turing | 8 | Budget option for small models and experimentation. |
| `L4` | 24 GB | Ada Lovelace | 8 | Good cost/performance for inference workloads up to ~7B parameters. |
| `A10` | 24 GB | Ampere | 4 | Similar to L4 but on Ampere architecture. Max 4 GPUs (96 GB total). |
| `L40S` | 48 GB | Ada Lovelace | 8 | Excellent cost/performance trade-off. Recommended starting point for inference. |
| `A100` | 40 GB | Ampere | 8 | 40GB variant. May be auto-upgraded to 80GB A100 at no extra cost. |
| `A100-40GB` | 40 GB | Ampere | 8 | Explicitly requests 40GB A100. No automatic upgrade. |
| `A100-80GB` | 80 GB | Ampere | 8 | Explicitly requests 80GB A100. Use for models requiring >40GB VRAM. |
| `RTX-PRO-6000` | 96 GB | Blackwell | 8 | Professional workstation GPU with 96GB VRAM. |
| `H100` | 80 GB | Hopper | 8 | SXM variant. May be auto-upgraded to H200 at no extra cost. Strong software ecosystem support. |
| `H100!` | 80 GB | Hopper | 8 | Explicitly requests H100 with NO automatic upgrade to H200. Use for benchmarking or when strict memory assumptions are needed. |
| `H200` | 141 GB | Hopper | 8 | 141GB HBM3e at 4.8TB/s bandwidth. 1.75x capacity and 1.4x bandwidth vs H100. |
| `B200` | 192 GB | Blackwell | 8 | NVIDIA's flagship data center chip. Highest performance for large models. |
| `B200+` | 192 GB | Blackwell | 8 | Opt-in upgrade: allows Modal to schedule on B200 or B300 GPUs. Billed as B200. B300 requires CUDA 13.0+. |

**Sizing guide:**

| Model size | Recommended GPU | Count |
| ---------- | --------------- | ----- |
| < 8B | A10 or A100 | 1 |
| 8B – 14B | A100 | 1 |
| 14B – 30B | H100 | 1 |
| 30B – 70B | H200 | 1–2 |
| 70B+ / large MoE | H200 or B200 | 2–8 |

### `scaling`

| Field | Default | Description |
| ----- | ------- | ----------- |
| `scaledown_window_minutes` | `15` | Minutes a replica stays alive with no incoming requests before scaling to zero. |
| `timeout_minutes` | `10` | Container startup timeout in minutes. |
| `max_concurrent_inputs` | `100` | Maximum number of simultaneous requests a single replica will accept. |
| `fast_boot` | `false` | When true, skips torch compilation during startup for faster cold starts at the cost of lower throughput. |

### `vllm_args`

| Field | Default | Description |
| ----- | ------- | ----------- |
| `async_scheduling` | `true` | Enable vLLM's async scheduling for better throughput under concurrent load. |
| `extra_args` | `[]` | Arbitrary CLI flags appended verbatim to the 'vllm serve' command. |

Common `extra_args` patterns:

```yaml
# Reasoning / tool-calling models
# Enable function calling and chain-of-thought parsing (e.g. Gemma 4, DeepSeek R1).
extra_args:
  - "--enable-auto-tool-choice"
  - "--reasoning-parser"
  - "gemma4"
  - "--tool-call-parser"
  - "gemma4"

# Context window limit
# Limit the maximum context length to reduce VRAM usage.
extra_args:
  - "--max-model-len"
  - "8192"

# Community models with custom code
# Required for models that use custom modeling code not in transformers.
extra_args:
  - "--trust-remote-code"

# Disable multimodal inputs
# Restrict to text-only to save memory on multimodal-capable models.
extra_args:
  - "--limit-mm-per-prompt"
  - '{"image": 0, "video": 0, "audio": 0}'

# MoE expert parallelism
# Enable expert parallelism for Mixture-of-Experts models (e.g. Qwen3-Coder, Mixtral).
extra_args:
  - "--enable-expert-parallel"

# Prefix caching
# Cache KV blocks for common prefixes to speed up repeated prompts.
extra_args:
  - "--enable-prefix-caching"

# GPU memory utilization
# Fraction of GPU VRAM vLLM is allowed to use (default 0.9).
extra_args:
  - "--gpu-memory-utilization"
  - "0.95"
```

### `image`

| Field | Default | Description |
| ----- | ------- | ----------- |
| `base` | `"nvidia/cuda:12.9.0-devel-ubuntu22.04"` | Base Docker image for the container. |
| `python` | `"3.12"` | Python version installed in the container by Modal. |
| `env` | `{}` | Environment variables baked into the container image at build time. |

Common environment variables:

| Variable | Value | Description |
| -------- | ----- | ----------- |
| `HF_XET_HIGH_PERFORMANCE` | `"1"` | Enable faster Hugging Face Hub downloads via Xet transport. |
| `VLLM_USE_DEEP_GEMM` | `"1"` | Enable DeepGEMM FP8 kernels for MoE models. Only supported on Blackwell GPUs (B200/B300), NOT Hopper (H100/H200). |

### `volumes`

| Field | Default | Description |
| ----- | ------- | ----------- |
| `hf_cache` | `"huggingface-cache"` | Modal Volume name for the Hugging Face model weight cache. |
| `vllm_cache` | `"vllm-cache"` | Modal Volume name for vLLM's JIT compilation cache. |

Modal Volume names for persistent caching. By default all deployments share the same volumes, so weights downloaded for one model are available to all. Use unique names to isolate a model's cache.

### `auth`

| Field | Required | Default | Description |
| ----- | -------- | ------- | ----------- |
| `token_name` | **Yes** | — | Name of the Modal Secret that holds the API token. |

Optional Bearer token authentication for the OpenAI-compatible API. The token value is stored in a Modal Secret, not in this config file.

Create the secret with `modal secret create <token_name> AUTH_TOKEN=<your-token>`. The secret must define an `AUTH_TOKEN` key. vLLM enforces Bearer auth on `/v1` endpoints when auth is enabled. Pass the secret name at deploy or run time: `agents deploy <config> -t <token_name>` (or set `AUTH_TOKEN_NAME` in the environment).
<!-- END GENERATED CONFIG REFERENCE -->

---

## Using the API

Once deployed, Modal prints a URL like:

```
https://<workspace>--<app-name>-serve.modal.run
```

This is a standard OpenAI-compatible endpoint. Use it with any OpenAI client.

If the config includes `auth.token_name`, create the Modal Secret first (`modal secret create <token_name> AUTH_TOKEN=<your-token>`) and pass the same token as the API key:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<workspace>--<app-name>-serve.modal.run/v1",
    api_key="your-token",  # must match AUTH_TOKEN in the Modal Secret when auth is enabled
)

response = client.chat.completions.create(
    model="llm",  # matches model.served_name in your config
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

The `/docs` route on the URL serves interactive Swagger UI for exploring the API.

---

## Editing the Infrastructure

| What to change                                    | Where                                                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Add a config field or change a default            | `schemas/model-config.schema.json`, then `agents generate-config` + `agents generate-docs` |
| Change how the container image is built           | `models/image.py`                                                                          |
| Change GPU, volumes, or vLLM command construction | `models/server.py`                                                                         |
| Change the health check / test request            | `models/health.py`                                                                         |
| Add SGLang engine support                         | `models/image.py` + `models/server.py` + extend `engine.type` in the JSON schema          |

**Never hardcode model-specific values in Python.** All model configuration belongs in `configs/*.yaml`.

---

## Dependencies

| Package    | Purpose                             |
| ---------- | ----------------------------------- |
| `modal`    | Cloud infrastructure SDK            |
| `pydantic` | Config validation                   |
| `pyyaml`   | YAML parsing                        |
| `aiohttp`  | Async HTTP client for health checks |

Managed in `pyproject.toml`. Install with:

```bash
uv pip install -e .
```
