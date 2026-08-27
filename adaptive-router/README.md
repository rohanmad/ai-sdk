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

## Telemetry

Every request is logged to `telemetry/routing.db`:

```bash
python -m telemetry.dashboard.cli --mode summary
python -m telemetry.dashboard.cli --limit 10
```

## Project layout

```
adaptive-router/
├── packages/
│   ├── sdk/                  # Python + TypeScript public API
│   ├── sensitivity_gate/     # Regex PII rules (v1)
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
