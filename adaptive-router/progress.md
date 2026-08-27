# Adaptive Router — Progress

Last updated: Aug 27, 2026

This file tracks what's built, what's stubbed, and what still needs work.

---

## Build order (from spec)

| Step | Component | Status | Notes |
|------|-----------|--------|-------|
| 1 | Execution layer + dumb routing | **Done** | Local + cloud paths work end-to-end (mock mode by default) |
| 2 | Sensitivity gate (regex v1) | **Done** | Runs on every request; triggers logged in telemetry |
| 3 | Routing decision engine | **Done** | 2×2 policy + hard rules wired |
| 4 | Collect labeled data | **Not started** | CSV schema exists; only 4 placeholder rows |
| 5 | Complexity classifier | **Stub only** | Feature extraction exists; training + inference not wired |
| 6 | Telemetry + dashboard | **Done (v1)** | SQLite logger + CLI; no web UI yet |
| 7 | v2 upgrades | **Partial** | `policy.yaml` wired; NER + XGBoost not built |

---

## What's working today

### Execution layer (`packages/execution/`)

- **`local_runner.py`** — runs small or large local models via llama.cpp when GGUF paths are set; falls back to mock responses otherwise
- **`cloud_adapter.py`** — OpenAI-compatible cloud calls when `OPENAI_API_KEY` is set; mock mode otherwise
- Same response shape regardless of target

### Sensitivity gate (`packages/sensitivity_gate/`)

- **`rules.py`** — regex detection for email, US phone, SSN-shaped, credit-card-shaped patterns
- Output: `is_sensitive` boolean + which rules fired (included in routing reason + telemetry)
- **`ner_classifier.py`** — placeholder only (v2)

### Routing engine (`packages/routing_engine/decide.py`)

- Implements the 2×2 policy table from the spec
- Reads `config/policy.yaml` for thresholds, targets, and hard rules
- Hard rule: `never_cloud_for_high_sensitivity` blocks cloud even if complexity is high
- **Dumb routing still active** — uses prompt length (≥ 500 chars = "high complexity") instead of a real classifier

### SDK (`packages/sdk/`)

- **Python** — `Router.init().generate_text(...)` returns OpenAI-compatible response + routing metadata
- **TypeScript** — `Router.init().generateText(...)` calls Python via `scripts/ts_bridge.py` subprocess
- Types mirrored in `types.py` / `types.ts`

### Telemetry (`telemetry/`)

- Every request logged to SQLite (`telemetry/routing.db`)
- Fields: target, reason, complexity score, sensitivity flag, triggers, latency, tokens, estimated cost saved
- CLI viewer: `python -m telemetry.dashboard.cli --mode summary`

### Tests (`tests/`)

- 7 tests passing (`pytest`)
- Covers: sensitivity detection, dumb routing, hard rules, end-to-end mock pipeline

---

## What's stubbed or placeholder

| File | State | What's missing |
|------|-------|----------------|
| `data/labeled_requests.csv` | 4 example rows | Real data from running prompts through small + large models |
| `packages/complexity_classifier/features.py` | Feature extraction only | Not connected to routing engine |
| `packages/complexity_classifier/train.py` | Raises `NotImplementedError` | Actual training pipeline (logistic regression / XGBoost) |
| `packages/complexity_classifier/model.pkl` | Does not exist | Trained model artifact |
| `packages/sensitivity_gate/ner_classifier.py` | Returns `is_sensitive=False` always | spaCy or distilled transformer NER |
| `telemetry/dashboard/` | CLI only | Web dashboard (charts, tables) |
| `config/policy.yaml` → `dumb_routing.enabled` | `true` | Must be disabled once classifier is trained |

---

## Current routing behavior (important)

Because dumb routing is on and there is no trained classifier yet:

```
Short prompt (< 500 chars)  →  small_local
Long prompt (≥ 500 chars)   →  cloud  (unless sensitivity forces large_local)
```

Sensitivity is real (regex runs), but **complexity is faked by character count**, not ML.

Example outcomes:

| Prompt | Sensitivity | Routed to |
|--------|-------------|-----------|
| "What is 2+2?" | LOW | `small_local` |
| 600-char string of x's | LOW | `cloud` |
| 600-char string + email/SSN | HIGH | `large_local` |

---

## Known gaps / things to fix

### Must-do before this is "real"

1. **Collect labeled data (step 4)** — run real prompts through small + large local models, record which was sufficient
2. **Train complexity classifier (step 5)** — implement `train.py`, save `model.pkl`, wire score into `decide.py`
3. **Disable dumb routing** — set `dumb_routing.enabled: false` in `policy.yaml` once classifier is live
4. **Configure real models** — set GGUF paths in `policy.yaml` or `RouterConfig`; install `llama-cpp-python`
5. **Configure cloud** — set `OPENAI_API_KEY`; install `openai`

### Nice-to-have / v2

- NER-based sensitivity detection (`ner_classifier.py`)
- Gradient-boosted classifier (XGBoost) alongside logistic regression baseline
- Web telemetry dashboard (currently CLI only)
- HTTP server mode for TypeScript SDK (instead of subprocess bridge)
- Anthropic adapter (spec mentions OpenAI/Anthropic; only OpenAI adapter exists)
- Accuracy metrics and failure-mode reporting for the classifier

### Minor / polish

- `pyproject.toml` entry point references `scripts.demo:main` but `scripts/` is not a proper package — CLI install may not work; use `python scripts/demo.py` directly for now
- TypeScript SDK requires `python3` on PATH (`ADAPTIVE_ROUTER_PYTHON` env var to override)
- Package dirs use underscores (`routing_engine`) instead of hyphens from original spec (`routing-engine`) — Python import requirement

---

## File map (what exists)

```
adaptive-router/
├── config/policy.yaml          ✅ routing policy + dumb routing config
├── data/labeled_requests.csv   ⚠️  schema only (4 placeholder rows)
├── packages/
│   ├── sdk/
│   │   ├── router.py           ✅ Python SDK entry point
│   │   ├── types.py            ✅ request/response types
│   │   ├── router.ts           ✅ TypeScript client
│   │   └── types.ts            ✅ TS types
│   ├── execution/
│   │   ├── local_runner.py     ✅ local inference (mock + llama.cpp)
│   │   └── cloud_adapter.py    ✅ cloud inference (mock + OpenAI)
│   ├── sensitivity_gate/
│   │   ├── rules.py            ✅ regex PII gate
│   │   └── ner_classifier.py   ⬜ v2 stub
│   ├── complexity_classifier/
│   │   ├── features.py         ⚠️  features only, not wired
│   │   └── train.py            ⬜ not implemented
│   └── routing_engine/
│       └── decide.py           ✅ policy logic + dumb routing
├── telemetry/
│   ├── logger.py               ✅ SQLite logger
│   └── dashboard/cli.py        ✅ CLI viewer
├── scripts/
│   ├── demo.py                 ✅ quick Python demo
│   └── ts_bridge.py            ✅ TS ↔ Python bridge
└── tests/
    ├── test_router.py          ✅ 6 tests
    └── test_hard_rules.py      ✅ 1 test
```

Legend: ✅ done · ⚠️ partial · ⬜ stub / not started

---

## How to verify current state

```bash
cd adaptive-router
pip install -e ".[dev]"
pytest -q                                    # should pass 7 tests
python scripts/demo.py "What is 2+2?"        # → small_local
python scripts/demo.py "$(python -c 'print("x"*600)')"  # → cloud
python -m telemetry.dashboard.cli --mode summary
```

---

## Suggested next steps (in order)

1. **Set up real local models** — download small (1–3B) and larger GGUF quantizations, add paths to `policy.yaml`
2. **Build data collection script** — batch-run prompts through both models, append rows to `labeled_requests.csv`
3. **Implement `train.py`** — logistic regression first, report accuracy on held-out set
4. **Wire classifier into router** — replace dumb routing complexity score with model prediction
5. **Expand test set** — measure routing accuracy and cost savings vs always-cloud baseline
