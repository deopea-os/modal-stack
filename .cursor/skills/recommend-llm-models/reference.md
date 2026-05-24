# Recommend LLM Models — Reference

## Requirements checklist

Complete before research. Use `not specified` for unknowns; do not invent values.

### Workload and quality

| Field | Notes |
|-------|--------|
| Primary workload | e.g. agentic coding, chat, RAG, vision, batch inference |
| Quality bar | e.g. “near Opus on SWE tasks”, “good enough for autocomplete” |
| Tool / function calling | Required? Which client (Copilot, custom agent, etc.)? |
| Vision / multimodal | Required, nice-to-have, or out of scope |
| Reasoning / long chains | Heavy reasoning vs fast turns |

### Scale and performance

| Field | Notes |
|-------|--------|
| Expected usage pattern | Bursty vs steady; hours/month if known |
| Concurrent requests | e.g. 1, 2–4, batch |
| Latency sensitivity | Cold start OK? max wait? |
| Context needs | Min/max tokens; per-tier if stacking |
| Output length | Typical max completion tokens |

### Economics and ops

| Field | Notes |
|-------|--------|
| Budget | $/month target; soft vs hard cap |
| Scale-to-zero | Required? idle window tolerance |
| Modal plan | Starter credit, team limits if known |
| Uptime | Acceptable downtime / redeploy frequency |

### Technical constraints

| Field | Notes |
|-------|--------|
| License | Apache, MIT, custom, commercial use |
| Model class | Dense vs MoE; min parameter count if any |
| Quantization | FP16/BF16/FP8/INT4 preferences or bans |
| vLLM version | Pin or “latest supported by repo” |
| Auth | Bearer secret on endpoint? |
| Existing configs | Reuse volume/app patterns? |

### Integration (optional appendix)

| Field | Notes |
|-------|--------|
| Client | VS Code Copilot BYOK, Cursor BYOK, Claude Code, other |
| Gateway | Cloudflare AI Gateway, direct Modal URL |
| API compatibility | OpenAI chat vs Anthropic messages |

---

## Evidence tiers

| Tier | Claim type | Minimum evidence |
|------|------------|------------------|
| **A — Hard constraint** | Won’t fit on GPU; license forbids use; API incompatibility | **1 authoritative** source (model card, Modal docs, schema enum) |
| **B — Performance** | Benchmark ranks, “beats X on task Y” | **2+ independent** sources; task-matched benchmark; note eval version/date |
| **C — Cost / ops** | $/hr, $/month, credit math | Modal pricing page + stated usage assumptions; show arithmetic |
| **D — Soft preference** | UX, “feels faster”, community sentiment | Label **opinion**; never sole basis for tier-1 pick |

If tier B cannot be met, present **candidates with uncertainty** and what evidence would resolve it.

---

## Benchmark selection

- **Match benchmark to workload** — no fixed global hierarchy.
- Coding / agentic: SWE-bench Verified, SWE-bench, LiveCodeBench, etc., as appropriate to the task named in the spec.
- General chat: MMLU, MT-Bench only when relevant.
- Vision: document-specific VLM benchmarks when vision is required.
- **Never rank on a single number alone** when comparing flagship models — cite **≥2** metrics or explain why one metric is sufficient for this narrow ask.
- Always note: **benchmark ≠ production fit** (tools, context, latency, cost).

When comparing to closed models (user-requested), cite **primary** leaderboard or vendor report and label **non-deployable on Modal**.

---

## Source independence

Counts as **independent** when methodology or publisher differs, e.g.:

- Vendor model card + third-party leaderboard
- Modal pricing + vLLM memory docs
- HF model page + separate eval repo

Does **not** count as independent:

- Same press release repeated across blogs
- This repo’s prior recommendation doc without re-fetching primary sources
- Assistant prior turn without fresh citation

---

## Conflict matrix (template)

```markdown
## Conflicts requiring your input

| Dimension | Option A | Evidence | Option B | Evidence |
|-----------|----------|----------|----------|----------|
| GPU for 80B MoE | H200 1× | … | RTX PRO 6000 1× | … |

**What matters more for you?** (pick or rank: cost / peak quality / context / cold start / tool calling)
```

Do not issue a single “winner” until the user responds **or** explicitly says “optimize for X”.

---

## Output templates

### Tier table (stack design)

```markdown
## Recommended tiers (conditional on …)

| Tier | Role | Model | GPU | Practical context | ~$/hr | Caveats |
|------|------|-------|-----|-------------------|-------|---------|
| 1 | … | `org/model` | L4 | … | … | … |

**Evidence:** [links]
**Not recommended:** … (with tier-A reason)
```

### Decision memo (major decision)

```markdown
# [Title] — LLM recommendation

**As-of:** YYYY-MM-DD
**Spec summary:** …
**Unknowns:** …

## Requirements (from checklist)
…

## Candidates considered
…

## Comparison matrix
…

## Conflicts (if any)
…

## Recommendations
### If you prioritize …
…

## Caveats
- Benchmark ≠ production
- …

## Sources
1. …
```

### Quick answer

- **Answer:** one paragraph
- **Evidence:** 2–4 bullets with links
- **Caveats:** 1–2 bullets
- **Open question:** only if blocking

---

## Cost arithmetic (Modal)

Use published **$/second** × seconds per month:

```
gross_monthly = gpu_hours_per_month × 3600 × rate_per_sec
out_of_pocket = max(0, gross_monthly - 30)   # Starter credit, when applicable
```

Show GPU-hours assumption explicitly. With usage CSVs, derive hours from session patterns or state that only **qualitative** tiers are possible.

---

## Repo cross-links (implementation, not evidence)

| Artifact | Use |
|----------|-----|
| `schemas/model-config.schema.json` | Valid GPU types and fields |
| `configs/_example.yaml` | Config shape |
| [create-model-config](../create-model-config/SKILL.md) | After user approves YAML |
| `models/vendor/*` | Known tool-parser vendoring — verify still required for chosen model |
