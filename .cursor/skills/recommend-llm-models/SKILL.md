---
name: recommend-llm-models
description: Researches and recommends open-weight LLMs and Modal GPU sizing for vLLM deployment from a user specification. Uses tiered evidence, multiple independent sources, and explicit conflict matrices before recommendations. Use when the user asks which model to deploy on Modal, GPU sizing, tiered stacks, benchmark-backed comparisons, or cost estimates for self-hosted inference — only when this skill is attached or named.
disable-model-invocation: true
---

# Recommend LLM Models (Modal / vLLM)

Produce **impartial, evidence-backed** model and GPU recommendations for **Modal + vLLM** in this repo. Do not treat prior conclusions, chat history, or repo docs as proof.

## Non-negotiable principles

1. **No prior winners** — Do not assume a model, vendor, or GPU is best until verified for *this* spec. Do not rank from memory alone.
2. **Evidence before recommendation** — Apply the [evidence tiers](reference.md#evidence-tiers). Mark single-source or stale claims **unverified**.
3. **Separate fact from judgment** — Facts need citations; trade-offs and picks are labeled **interpretation** and tied to stated user priorities.
4. **Conflicts → user decides** — When credible sources disagree, present a **conflict matrix** and ask the user to weight priorities before a final pick. Do not silently pick a side.
5. **Missing spec → conditional ranges** — If budget, workload, or context are unknown, give **scenario branches** (e.g. “if &lt;$30/mo credit-covered usage…”) instead of inventing defaults. Ask blocking questions before a single “best” answer.
6. **Open-weight first** — Recommend HF models deployable via this repo’s stack. Mention closed APIs only for **comparison** when the user asks or when benchmarks require a reference point — label as non-Modal.
7. **Repo artifacts are examples only** — `docs/modal-llm-deployment-recommendation.md`, `configs/*.yaml`, and ad-hoc markdown in the repo illustrate patterns; **re-validate** claims for the current request.

## Workflow

Copy and track:

```
- [ ] 1. Intake — complete requirements checklist (or document gaps)
- [ ] 2. Research — multi-source evidence per tier
- [ ] 3. Feasibility — VRAM, context, vLLM flags, Modal GPU enum
- [ ] 4. Compare — matrix + conflicts
- [ ] 5. User priority check — if conflicts remain
- [ ] 6. Recommend — conditional or final, with citations
- [ ] 7. Offer config — only if user wants YAML (see below)
```

### 1. Requirements intake

Before researching, fill the [requirements checklist](reference.md#requirements-checklist) from the user’s message. For any item **unknown**, record `not specified` — do not guess.

If the user supplies **usage CSVs or logs**, analyze them (medians, p90 context, burstiness, active days) and cite aggregates in the report. If not supplied, note that cost estimates are **usage-dependent**.

### 2. Research (multi-source)

Use **at least two independent source types** for performance and cost claims. Prefer:

| Source type | Examples |
|-------------|----------|
| Primary / vendor | Model cards, HF README, official blog, license |
| Infrastructure | [Modal GPU docs](https://modal.com/docs/guide/gpu), [Modal pricing](https://modal.com/pricing) |
| Engine | [vLLM docs](https://docs.vllm.ai/), release notes for parsers/MoE |
| Benchmarks | Task-matched leaderboards (see [benchmark selection](reference.md#benchmark-selection)) |
| Community | Recent issues/PRs only when primary docs are silent — label **secondary** |

Use **WebSearch** / **WebFetch** for current pricing, benchmarks, and fit claims. State **as-of date** for time-sensitive numbers.

Cross-check repo-local claims (VRAM tables, “fits on one B200”, SWE-bench scores) against primary sources.

### 3. Feasibility (Modal + vLLM)

For each candidate:

- **VRAM fit** — weights + KV at stated context and concurrency; note quantization (FP8/INT4) and tensor parallel if needed.
- **GPU** — Must match `schemas/model-config.schema.json` enum; use [create-model-config](../create-model-config/SKILL.md) sizing guide as a **starting hypothesis**, not a verdict.
- **vLLM** — tool parser, `trust-remote-code`, MoE flags, `max-model-len` vs “practical” context.
- **Modal ops** — scale-to-zero, `scaledown_window`, cold starts, `max_concurrent_inputs`.

Reject or downgrade candidates that **cannot** be served on Modal with stated constraints; say why with evidence.

### 4. Compare and surface conflicts

Build a comparison matrix (models × criteria relevant to the spec). When sources disagree, add a **conflict matrix**:

| Topic | Position A | Source | Position B | Source | Why they may differ |
|-------|------------|--------|------------|--------|---------------------|

Ask the user which dimension matters most (cost, peak quality, context, latency, tool calling, etc.) before a single final recommendation.

### 5. Deliver (flexible format)

Choose format based on the ask:

| User intent | Format |
|-------------|--------|
| Quick steer | Short answer + 2–3 cited bullets + caveats |
| Stack design | Tier table (role / model / GPU / context / $/hr / deploy name) |
| Major decision | Decision memo: spec → evidence → matrix → branches → caveats → sources |

**Cost:** Use Modal **$/sec or $/hr** from the pricing page; include Starter **$30/mo credit** when relevant. Quantify **$/month** only when the user gives GPU-hours or usage data; otherwise give **hours-to-$50** style bounds.

**Output location:** Reply in chat only. **Do not** write `docs/` unless the user asks.

### 6. Optional: client appendix

If the user mentions **Copilot BYOK**, **Cloudflare AI Gateway**, **Cursor**, or **Claude Code**, add a short appendix:

- API shape (OpenAI-compatible vs Anthropic `/v1/messages`)
- Model id (`served_name` / `llm`) and token limits derived from `max-model-len`
- What this repo does **not** guarantee (e.g. Composer backend, Insiders-only features)

Keep appendix factual; link to primary docs.

### 7. Offer config creation

After recommendations, **offer** (do not auto-run) creating `configs/<name>.yaml` via [create-model-config](../create-model-config/SKILL.md). Wait for explicit approval.

## Anti-patterns

- Recommending from a single blog post or uncited benchmark screenshot
- “Industry standard” or “obviously best” without sources
- Copying `docs/modal-llm-deployment-recommendation.md` tiers without re-checking the user’s spec
- Hardcoding model winners in the skill (this file must stay methodology-only)
- Creating or deploying configs without user confirmation

## Additional resources

- [reference.md](reference.md) — checklist, evidence tiers, benchmark rules, output templates
