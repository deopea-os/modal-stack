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
```

### Test a deployed model

```bash
agents run gemma4_26b
```

This spins up a fresh container, runs a `/health` check, then sends a single streaming chat completion request.

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
│   ├── gemma4_26b.yaml   # Gemma 4 26B deployment config
│   └── _example.yaml     # Annotated template for new models
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

## Config Reference

All fields except `model.name` are optional. Defaults are shown below.

### Top-level

| Field       | Required | Default                | Description                                   |
| ----------- | -------- | ---------------------- | --------------------------------------------- |
| `model`     | Yes      | —                      | Model identity section                        |
| `app_name`  | No       | Slug from `model.name` | Modal app name (e.g. `llama-3.1-8b-instruct`) |
| `engine`    | No       | See below              | Serving engine settings                       |
| `gpu`       | No       | See below              | GPU type and count                            |
| `scaling`   | No       | See below              | Timeout and concurrency                       |
| `vllm_args` | No       | See below              | vLLM CLI flags                                |
| `image`     | No       | See below              | Container image settings                      |
| `volumes`   | No       | See below              | Modal Volume names                            |

### `model`

| Field         | Required | Default | Description                                            |
| ------------- | -------- | ------- | ------------------------------------------------------ |
| `name`        | **Yes**  | —       | Hugging Face repo ID, e.g. `google/gemma-4-26B-A4B-it` |
| `revision`    | No       | `null`  | Commit hash to pin. Omit to always use latest          |
| `served_name` | No       | `"llm"` | Name clients use in the OpenAI `model` field           |

### `engine`

| Field       | Default    | Description                                                          |
| ----------- | ---------- | -------------------------------------------------------------------- |
| `type`      | `"vllm"`   | Serving engine. Only `"vllm"` is supported today                     |
| `version`   | `"0.19.0"` | vLLM pip version installed in the container                          |
| `extra_pip` | `[]`       | Extra packages installed alongside vLLM (e.g. `transformers==5.5.0`) |

### `gpu`

| Field   | Default  | Description                                                       |
| ------- | -------- | ----------------------------------------------------------------- |
| `type`  | `"H200"` | Modal GPU type: `A10G`, `A100`, `H100`, `H200`, `B200`            |
| `count` | `1`      | GPUs per replica. Use `>1` for tensor parallelism on large models |

**Sizing guide:**

| Model size       | Recommended GPU | Count |
| ---------------- | --------------- | ----- |
| < 8B             | A10G or A100    | 1     |
| 8B – 14B         | A100            | 1     |
| 14B – 30B        | H100            | 1     |
| 30B – 70B        | H200            | 1–2   |
| 70B+ / large MoE | H200 or B200    | 2–8   |

### `scaling`

| Field                      | Default | Description                                                           |
| -------------------------- | ------- | --------------------------------------------------------------------- |
| `scaledown_window_minutes` | `15`    | Minutes a replica stays alive with no requests before scaling to zero |
| `timeout_minutes`          | `10`    | Container startup timeout. Increase for very large models             |
| `max_concurrent_inputs`    | `100`   | Max simultaneous requests per replica                                 |
| `fast_boot`                | `false` | Skip torch compilation for faster cold starts (lower throughput)      |

### `vllm_args`

| Field              | Default | Description                                                            |
| ------------------ | ------- | ---------------------------------------------------------------------- |
| `async_scheduling` | `true`  | Enable async scheduling for better throughput under load               |
| `extra_args`       | `[]`    | Arbitrary `vllm serve` CLI flags (each token is a separate list entry) |

Common `extra_args` patterns:

```yaml
# Reasoning / tool-calling models (e.g. Gemma 4, DeepSeek R1)
extra_args:
  - "--enable-auto-tool-choice"
  - "--reasoning-parser"
  - "gemma4"
  - "--tool-call-parser"
  - "gemma4"

# Limit context window to reduce VRAM usage
extra_args:
  - "--max-model-len"
  - "8192"

# Community models that use custom code
extra_args:
  - "--trust-remote-code"

# Disable multimodal inputs (text-only, saves memory)
extra_args:
  - "--limit-mm-per-prompt"
  - '{"image": 0, "video": 0, "audio": 0}'
```

### `image`

| Field    | Default                                  | Description                                              |
| -------- | ---------------------------------------- | -------------------------------------------------------- |
| `base`   | `"nvidia/cuda:12.9.0-devel-ubuntu22.04"` | Base Docker image                                        |
| `python` | `"3.12"`                                 | Python version added to the base image                   |
| `env`    | `{}`                                     | Environment variables baked into the image at build time |

### `volumes`

| Field        | Default               | Description                                 |
| ------------ | --------------------- | ------------------------------------------- |
| `hf_cache`   | `"huggingface-cache"` | Modal Volume for Hugging Face weight cache  |
| `vllm_cache` | `"vllm-cache"`        | Modal Volume for vLLM JIT compilation cache |

By default all deployments share the same volumes, so weights downloaded for one model are available to all. Use unique names to isolate a model's cache.

---

## Using the API

Once deployed, Modal prints a URL like:

```
https://<workspace>--<app-name>-serve.modal.run
```

This is a standard OpenAI-compatible endpoint. Use it with any OpenAI client:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<workspace>--<app-name>-serve.modal.run/v1",
    api_key="unused",  # Modal handles auth via the URL
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
| Add a config field or change a default            | `models/config.py`                                                                         |
| Change how the container image is built           | `models/image.py`                                                                          |
| Change GPU, volumes, or vLLM command construction | `models/server.py`                                                                         |
| Change the health check / test request            | `models/health.py`                                                                         |
| Add SGLang engine support                         | `models/image.py` + `models/server.py` + add `"sglang"` to `Literal` in `models/config.py` |

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
