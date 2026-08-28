# Adaptive Inference Router SDK

Routes each AI inference request to the right execution target — a small local model, a large local model, or a cloud API — based on **complexity** (how hard is the request) and **sensitivity** (whether data is allowed to leave the device).

Same OpenAI-compatible interface regardless of where inference actually runs. Every routing decision is logged with a human-readable reason.

## Routing policy (2×2)

|                  | LOW sensitivity        | HIGH sensitivity              |
|------------------|------------------------|-------------------------------|
| LOW complexity   | small local model      | small local model (forced)    |
| HIGH complexity  | cloud (best model)     | large local (privacy wins)    |

## Build status

| Step | Component | Status |
|------|-----------|--------|
| 1 | Execution layer + dumb routing | **Done** |
| 2 | Sensitivity gate (regex v1) | **Done** |
| 3 | Routing decision engine | **Done** |
| 4 | Collect labeled data | Scaffolded (`data/labeled_requests.csv`) |
| 5 | Complexity classifier | Scaffolded (`features.py`, `train.py`) |
| 6 | Telemetry + dashboard | **Done** (SQLite + CLI) |
| 7 | v2 upgrades (NER, XGBoost, policy) | Partial (policy.yaml wired) |

## Quick start

### Python

```bash
cd adaptive-router
pip install -e ".[dev]"
pytest
python scripts/demo.py "What is 2+2?"
python scripts/demo.py "$(python -c 'print("x"*600)')"
```

### TypeScript

```bash
cd adaptive-router/packages/sdk
npm install
npm run demo
```

Requires `python3` on PATH (or set `ADAPTIVE_ROUTER_PYTHON`).

### Data collection (new machine)

Collection scripts need Python 3.10+, local GGUF models, and ML deps. **Use a virtual environment** — system Python on many Linux/macOS installs blocks `pip install` with `externally-managed-environment`.

```bash
cd adaptive-router

# One-time setup
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[local,ml,dev]"

# Ensure models exist at paths in config/policy.yaml (see models/small/, models/large/)
# Then run batch 2 collection (resumes automatically):
./scripts/collect_batch2.sh 30
```

If `python` is not on your PATH (common on macOS), the scripts use `python3` automatically. To pin a specific interpreter:

```bash
PYTHON=/path/to/python3 ./scripts/collect_batch2.sh 30
```

Each prompt runs small + large models sequentially (~1–2 min/prompt). The RAM tip at startup is normal, not an error.

### Download local GGUF models (~5.5 GB total)

Models are **not** installed by pip. Download from Hugging Face (requires `huggingface_hub`, included in `[local]`):

```bash
cd adaptive-router
mkdir -p models/small models/large

# Small model (~1 GB)
hf download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --local-dir models/small

# Large model (~4.5 GB, 2 shards — llama.cpp loads both automatically)
hf download Qwen/Qwen2.5-7B-Instruct-GGUF \
  --include "qwen2.5-7b-instruct-q4_k_m-*" \
  --local-dir models/large
```

Paths must match `config/policy.yaml` (first shard for the 7B model). If `hf` is not found: `pip install huggingface_hub` or use `huggingface-cli download` instead.

## Architecture

```
Request (text + metadata)
        |
        v
+-------------------+     +------------------------+
| Sensitivity Gate   |     | Complexity Classifier   |
| (regex PII rules)  |     | (placeholder / dumb)    |
+---------+----------+     +-----------+--------------+
          |                            |
          +-------------+--------------+
                         v
                Routing Decision Engine
                         |
        +----------------+-----------------+
        v                v                 v
  Small local       Large local        Cloud API
     model             model
        |                |                 |
        +----------------+-----------------+
                         v
                  Telemetry (SQLite)
```

## Step 1: dumb routing

While the complexity classifier is not trained, `config/policy.yaml` enables **dumb routing**:

- Prompts **&lt; 500 chars** → `small_local`
- Prompts **≥ 500 chars** → `cloud` (unless sensitivity forces `large_local`)

This proves both local and cloud execution paths work behind one API call.

## Configuration

Edit `config/policy.yaml` for hard rules, thresholds, and model paths:

```yaml
hard_rules:
  never_cloud_for_high_sensitivity: true

models:
  small_local:
    path: "/path/to/small.gguf"
  large_local:
    path: "/path/to/large.gguf"
```

Set `OPENAI_API_KEY` for real cloud inference. Without API keys or GGUF paths, the router runs in **mock mode** (useful for tests and CI).

## API

### Python

```python
from packages.sdk.router import Router, RouterConfig
from packages.sdk.types import GenerateTextRequest

router = Router.init()
response = router.generate_text(GenerateTextRequest(prompt="Hello!"))
print(response.routing.target, response.routing.reason)
print(response.choices[0].text)
```

### TypeScript

```typescript
import { Router } from "@adaptive-router/sdk";

const router = Router.init();
const response = await router.generateText({ prompt: "Hello!" });
console.log(response.routing.target, response.routing.reason);
```

## Sensitivity gate

Regex patterns (email, phone, SSN, credit-card) plus optional spaCy NER for names, locations, and organizations.

```bash
pip install -e ".[ner]"
python -m spacy download en_core_web_sm
```

NER runs additively in `check_sensitivity()` — a prompt is sensitive if regex **or** NER flags it.

## Telemetry

Every request is logged to `telemetry/routing.db`:

```bash
python -m telemetry.dashboard.cli --mode summary
python -m telemetry.dashboard.cli --limit 10
python -m telemetry.dashboard.web.app   # telemetry at /, chat at /chat
```

## Project layout

```
adaptive-router/
├── packages/
│   ├── sdk/                  # Python + TypeScript public API
│   ├── sensitivity_gate/     # Regex PII + spaCy NER
│   ├── complexity_classifier/# Feature extraction + training (step 5)
│   ├── routing_engine/       # 2×2 policy logic
│   └── execution/            # local_runner + cloud_adapter
├── telemetry/                # SQLite logger + CLI dashboard
├── config/policy.yaml
├── data/labeled_requests.csv
└── tests/
```

## Next steps

1. Disable `dumb_routing` in policy.yaml once labeled data exists
2. Run requests through small + large local models to expand `labeled_requests.csv`
3. Train complexity classifier: `python packages/complexity_classifier/train.py`
4. Optional: `pip install llama-cpp-python openai` for real inference
