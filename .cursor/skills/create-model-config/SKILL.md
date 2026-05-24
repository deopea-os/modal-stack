---
name: create-model-config
description: Create a new Modal LLM model config YAML file with validated defaults. Use when the user wants to add a new model, create a model config, deploy a new LLM, or mentions adding a model to configs/.
---

# Create Model Config

Create a new YAML config in `configs/` for deploying an LLM on Modal via vLLM.

**Source of truth:** `schemas/model-config.schema.json` — field types, defaults, and validation. Pydantic models are generated in `models/_generated.py`; custom behavior (`from_yaml`, default `app_name`) lives in `models/config.py`.

Start from `configs/_example.yaml` when possible.

## Required Information

Only `model.name` (Hugging Face repo ID) is required. Gather from the user:

1. **Model repo** — e.g. `meta-llama/Llama-3.1-8B-Instruct`
2. **GPU preference** — if not specified, use the sizing guide below (Modal GPU type strings)
3. **Any special vLLM flags** — tool calling, reasoning, MoE, trust-remote-code, max-model-len, etc.
4. **Auth** — if the endpoint should require a Bearer token, ask for a Modal Secret name (not the token value)

## GPU Sizing Guide

Use when the user does not specify a GPU. Values must match the schema enum (see [Modal GPU docs](https://modal.com/docs/guide/gpu)).

| Model size | GPU type | Count | Notes |
|------------|----------|-------|-------|
| < 8B | `A10` or `A100` | 1 | `L4` / `L40S` also work for small inference workloads |
| 8B – 14B | `A100` | 1 | |
| 14B – 30B | `H100` | 1 | May be upgraded to `H200` at no extra cost |
| 30B – 70B | `H200` | 1–2 | Tensor parallelism for dense ~70B |
| 70B+ / large MoE | `H200` or `B200` | 2–8 | `B200+` opts into B200/B300 pool |

**Valid `gpu.type` strings:** `T4`, `L4`, `A10`, `L40S`, `A100`, `A100-40GB`, `A100-80GB`, `RTX-PRO-6000`, `H100`, `H100!`, `H200`, `B200`, `B200+`

- `H100!` — no automatic upgrade to H200 (benchmarking)
- `B200+` — may schedule on B200 or B300 (billed as B200; needs CUDA 13.0+ for B300)

**GPU fallbacks** — use an array instead of a single string; `gpu.count` is ignored (put `:N` on each entry):

```yaml
gpu:
  type:
    - "H100"
    - "A100-80GB:2"
```

## Config File Naming

Use a short, descriptive stem: `<model>_<variant>.yaml`

Examples: `gemma4_26b.yaml`, `qwen3_coder_next_h200.yaml`, `llama3_8b.yaml`

## Creation Steps

1. Copy `configs/_example.yaml` to `configs/<name>.yaml`
2. Set `model.name` (and optional `revision`, GPU, `vllm_args`, etc.)
3. Ensure the first line enables IDE autocomplete:
   ```yaml
   # yaml-language-server: $schema=../schemas/model-config.schema.json
   ```
4. Validate:
   ```bash
   agents run <name>   # optional: full Modal health check
   ```
   Or validate locally without Modal:
   ```bash
   python -c "
   from pathlib import Path
   from models.config import ModelConfig

   cfg = ModelConfig.from_yaml(Path('configs/<name>.yaml'))
   gpu = cfg.gpu.type
   gpu_s = gpu if isinstance(gpu, str) else ', '.join(gpu)
   print(f'Valid: {cfg.app_name} -> {cfg.model.name} on {gpu_s} (count={cfg.gpu.count})')
   "
   ```

## YAML Template

Minimal config (only required field):

```yaml
# yaml-language-server: $schema=../schemas/model-config.schema.json

model:
  name: "org/model-name"
```

Typical config with customization:

```yaml
# yaml-language-server: $schema=../schemas/model-config.schema.json

app_name: "model-shortname"

model:
  name: "org/Model-Name"
  revision: "abc123def456..."
  served_name: "llm"

gpu:
  type: "H100"
  count: 1

scaling:
  scaledown_window_minutes: 15
  timeout_minutes: 10
  max_concurrent_inputs: 100
  fast_boot: false

vllm_args:
  async_scheduling: true
  extra_args:
    - "--trust-remote-code"
```

## Authentication (optional)

Protect `/v1` API calls with a Bearer token. The token value lives in a [Modal Secret](https://modal.com/docs/guide/secrets). See [Modal token-based authentication](https://modal.com/docs/guide/webhooks#token-based-authentication).

1. Create the secret (once per workspace):

   ```bash
   modal secret create <token_name> AUTH_TOKEN=<your-token>
   ```

2. Pass the secret name at deploy/run:

   ```bash
   agents deploy <name> -t <token_name>
   agents run <name> -t <token_name>
   ```

   Or set `AUTH_TOKEN_NAME=<token_name>` in the environment when calling `modal deploy` directly.

3. Alternatively set it in YAML:

   ```yaml
   auth:
     token_name: "<token_name>"
   ```

   CLI/env (`-t` / `AUTH_TOKEN_NAME`) overrides YAML when both are set.

4. Clients send `Authorization: Bearer <your-token>` (OpenAI SDK: set `api_key` to the same value).

For local health checks with auth, also export the token value: `export AUTH_TOKEN=<your-token>`.

## Defaults Reference

Applied when a field is omitted (from schema / generated models):

| Field | Default |
|-------|---------|
| `app_name` | Slug from `model.name` (e.g. `llama-3.1-8b-instruct`) |
| `model.served_name` | `"llm"` |
| `engine.type` | `"vllm"` |
| `engine.version` | `"0.19.0"` |
| `engine.extra_pip` | `[]` |
| `gpu.type` | `"H200"` |
| `gpu.count` | `1` |
| `scaling.scaledown_window_minutes` | `15` |
| `scaling.timeout_minutes` | `10` |
| `scaling.max_concurrent_inputs` | `100` |
| `scaling.fast_boot` | `false` |
| `vllm_args.async_scheduling` | `true` |
| `vllm_args.extra_args` | `[]` |
| `image.base` | `"nvidia/cuda:12.9.0-devel-ubuntu22.04"` |
| `image.python` | `"3.12"` |
| `image.env` | `{}` |
| `volumes.hf_cache` | `"huggingface-cache"` (shared) |
| `volumes.vllm_cache` | `"vllm-cache"` (shared) |
| `auth` | omitted (no auth) |

## Common `extra_args` Patterns

**Reasoning / tool-calling** (Gemma 4, DeepSeek R1, Qwen Coder, etc.):

```yaml
extra_args:
  - "--enable-auto-tool-choice"
  - "--reasoning-parser"
  - "gemma4"
  - "--tool-call-parser"
  - "gemma4"
```

**MoE expert parallelism** (e.g. Qwen3-Coder-Next):

```yaml
extra_args:
  - "--enable-expert-parallel"
```

**Text-only** (disable multimodal):

```yaml
extra_args:
  - "--limit-mm-per-prompt"
  - '{"image": 0, "video": 0, "audio": 0}'
```

**Context window limit:**

```yaml
extra_args:
  - "--max-model-len"
  - "8192"
```

**Community / custom modeling code:**

```yaml
extra_args:
  - "--trust-remote-code"
```

**Blackwell MoE (B200 only)** — do not use on H100/H200:

```yaml
image:
  env:
    VLLM_USE_DEEP_GEMM: "1"
```

## After Creation

Deploy:

```bash
agents deploy <name>
```

Test (health check + sample completion):

```bash
agents run <name>
```

## Schema / Docs Maintenance

If you change the JSON schema, regenerate artifacts:

```bash
agents generate-config   # models/_generated.py
agents generate-docs     # README Config Reference
```

Pre-commit runs these automatically when `schemas/model-config.schema.json` is staged.
