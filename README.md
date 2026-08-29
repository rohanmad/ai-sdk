# Adaptive Router

Send a prompt, get an answer. Behind the scenes, the router picks where inference runs: a small local model, a large local one, or a cloud API. It looks at how hard the request is and whether the text looks sensitive (emails, names, orgs, and similar).

One API call. Every decision is logged with a plain-English reason.

## How routing works

| | Not sensitive | Sensitive |
|---|---|---|
| **Easy prompt** | `small_local` | `small_local` |
| **Hard prompt** | `cloud` | `large_local` |

Sensitive data never goes to cloud when `never_cloud_for_high_sensitivity` is on in `config/policy.yaml`.

## Quick start

```bash
pip install -e ".[dev,web]"
pytest -q --ignore=tests/test_local_runner.py
python scripts/demo.py "What is 2+2?"
```

Open the dashboard and chat UI:

```bash
python -m telemetry.dashboard.web.app
```

Telemetry: http://127.0.0.1:8765  
Chat: http://127.0.0.1:8765/chat

## Python API

```python
from packages.sdk.router import Router
from packages.sdk.types import GenerateTextRequest

router = Router.init()
response = router.generate_text(GenerateTextRequest(prompt="Hello!"))
print(response.routing.target, response.routing.reason)
print(response.choices[0].text)
```

TypeScript bindings live in `packages/sdk` (`npm install && npm run demo`).

## Local models (optional)

GGUF models are not installed by pip. Download Qwen instruct weights into `models/small` and `models/large`, then point `config/policy.yaml` at them. Without model paths or `OPENAI_API_KEY`, the router runs in mock mode (fine for tests).

```bash
pip install -e ".[local]"
mkdir -p models/small models/large
hf download Qwen/Qwen2.5-1.5B-Instruct-GGUF qwen2.5-1.5b-instruct-q4_k_m.gguf --local-dir models/small
hf download Qwen/Qwen2.5-7B-Instruct-GGUF --include "qwen2.5-7b-instruct-q4_k_m-*" --local-dir models/large
```

## Sensitivity gate (optional NER)

Regex catches emails, phones, SSNs, and card-like patterns. Add spaCy NER for names, places, and organizations:

```bash
pip install -e ".[ner]"
python -m spacy download en_core_web_sm
```

## Project layout

```
packages/          SDK, routing engine, classifier, execution, sensitivity gate
config/            policy.yaml
telemetry/         SQLite logger + web dashboard
data/              labeled prompts and eval outputs
scripts/           demo, cost analysis, data collection
tests/
```

More detail on training, eval numbers, and known limitations: see `progress.md`.
