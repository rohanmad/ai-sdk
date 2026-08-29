# Adaptive Router — Progress

Last updated: Aug 28, 2026

---

## Build order (from spec)

| Step | Component | Status | Notes |
|------|-----------|--------|-------|
| 1 | Execution layer + dumb routing | **Done** | Qwen 1.5B + 7B GGUF via llama.cpp; mock fallback |
| 2 | Sensitivity gate | **Done** | Regex PII + spaCy NER (`en_core_web_sm`) |
| 3 | Routing decision engine | **Done** | 2×2 policy + hard rules |
| 4 | Collect labeled data | **Done** | 300 rows in `labeled_requests.csv` |
| 5 | Complexity classifier | **Done** | Logistic regression trained; `model.pkl` saved |
| 6 | Telemetry + dashboard | **Done** | SQLite logger + CLI viewer + web dashboard |
| 7 | v2 upgrades | **Partial** | XGBoost not built |

---

## Classifier metrics (stratified 5-fold CV, `class_weight='balanced'`)

**Primary estimate:** 5-fold stratified cross-validation. Production `model.pkl` uses **6 legacy hand-crafted features** @ threshold **0.50** (12-feature pattern model reverted Aug 28).

### Dataset (300 rows, Aug 28)

| | Batch 1 | Batch 2 | Total |
|--|---------|---------|-------|
| Prompts | 150 | 150 | **300** |
| `True` | 127 | 129 | **256 (85.3%)** |
| `False` | 23 | 21 | **44 (14.7%)** |

Batch 2 collected with labeling v2 (`factual_substring_match` + substring fixes). V2 relabel applied to 4 disputed batch-1 factual rows.

### 5-fold CV — hand-crafted only (n=300)

| Metric | n=150 (relabeled) | n=300 | Δ |
|--------|-------------------|-------|---|
| **Accuracy** | 0.640 ± 0.118 | **0.673 ± 0.076** | +0.033 |
| **False precision** | 0.298 ± 0.087 | 0.287 ± 0.064 | −0.011 |
| **False recall** | 0.680 ± 0.194 | **0.772 ± 0.071** | +0.092 |
| **False F1** | **0.412 ± 0.118** | **0.416 ± 0.075** | +0.004 |
| **True precision** | 0.890 ± 0.080 | **0.943 ± 0.019** | +0.053 |
| **True recall** | 0.633 ± 0.117 | 0.656 ± 0.084 | +0.023 |
| **True F1** | 0.737 ± 0.107 | **0.771 ± 0.065** | +0.034 |

**Read:** Doubling data improved accuracy and True-class metrics, but **False precision stayed ~0.29** — still the weak point. False F1 barely moved (+0.004). More clean data alone did not get minority precision to a usable level; the model still over-predicts `False` (88 easy prompts misclassified as hard in aggregated CV).

#### Aggregated confusion matrix — n=300, hand-crafted only

```
                      pred=False  pred=True
  actual=False (hard):          34          10
  actual=True  (easy):          88         168
```

Hand-crafted max separation (char_length): **0.841**

### Threshold sweep + pattern features (Aug 28, n=300)

**12 features** (6 legacy + 6 new): `open_ended_starter`, `imperative_multi_step`, `factual_pattern`, `length_bucket_short/medium/long`.

Run on other machine:
```bash
python packages/complexity_classifier/train.py --handcrafted-only --skip-inspection
```

#### Threshold sweep (6 legacy features, out-of-fold)

| threshold | accuracy | False prec | False rec | False F1 |
|-----------|----------|------------|-----------|----------|
| 0.30 | 0.787 | **0.321** | 0.409 | 0.360 |
| 0.35 | 0.747 | 0.284 | 0.477 | 0.356 |
| 0.40 | 0.700 | 0.255 | 0.545 | 0.348 |
| 0.45 | 0.683 | 0.274 | 0.705 | 0.395 |
| 0.50 | 0.673 | 0.279 | 0.773 | 0.410 |
| 0.55 | 0.663 | 0.279 | 0.818 | 0.416 |
| 0.60 | 0.620 | 0.257 | 0.841 | 0.394 |
| 0.65 | 0.590 | 0.242 | 0.841 | 0.376 |
| 0.70 | 0.547 | 0.226 | 0.864 | 0.358 |

**Recommended (recall ≥ 0.50, precision nearest 0.45):** threshold **0.50–0.55** — False precision stays **~0.28**, no usable tradeoff vs pre-relabel sweep.

**Best precision in sweep:** **0.355 @ 0.30** (recall 0.41, below 0.50 floor). **No threshold reaches 0.40+ precision with recall ≥ 0.50.**

#### Pattern features @ threshold 0.50 (vs 6 legacy baseline)

| Metric | 6 legacy @ 0.50 | 12 feat @ 0.50 | Δ |
|--------|-----------------|----------------|---|
| False precision | 0.287 | 0.259 | −0.028 |
| False recall | 0.772 | 0.750 | −0.022 |
| False F1 | 0.416 | 0.383 | −0.033 |

**Verdict: PRECISION PLATEAU.** Threshold tuning and prompt-pattern features did not meaningfully improve False precision above ~0.29. Pattern features slightly **hurt** metrics.

#### Production model revert (Aug 28)

**Reverted `model.pkl` to 6 legacy features @ threshold 0.50** (`git checkout` from commit `9930748`). Pattern-feature code remains in `features.py` / `vectorize.py` but is **not used** in production (`predict.py` slices to `model.coef_.shape[1]` features).

| Model | False prec | False rec | False F1 |
|-------|------------|-----------|----------|
| 6 legacy @ 0.50 (production) | **0.287** | 0.772 | **0.416** |
| 12 pattern @ 0.55 (reverted) | 0.250 | 0.794 | 0.379 |

### Cost & Routing Analysis (Aug 28, n=300 eval set)

Full pipeline on `labeled_requests.csv`: sensitivity gate → 6-feature classifier (0.50) → `decide.py` 2×2 policy. Script: `scripts/analyze_routing_cost.py` → `data/routing_cost_analysis.csv`. Run `python scripts/analyze_routing_cost.py --compare-ner` for regex-only vs regex+NER table.

#### Routing distribution — regex+NER (current production gate)

| Target | Count | % |
|--------|------:|--:|
| `small_local` | 185 | 61.7% |
| `cloud` | 88 | 29.3% |
| `large_local` | 27 | 9.0% |

**66 / 300** prompts flagged sensitive (NER; regex alone flagged **0** on this eval set). NER shifts **27** previously-cloud hard prompts → `large_local` (e.g. `ner:ORG` on “GitHub”, “SQL”, “NoSQL”; `ner:GPE` on “Fahrenheit”).

#### Before / after NER on same 300-prompt eval

| Metric | Regex only (pre-NER baseline) | Regex + NER (current) |
|--------|------------------------------:|----------------------:|
| `small_local` | 61.7% | 61.7% |
| `cloud` | 38.3% | **29.3%** |
| `large_local` | 0.0% | **9.0%** |
| **Cost savings** | 60.8% | **70.0%** |
| **Misroute rate** (hard → `small_local`) | 4.3% | 4.3% |
| Sensitive flagged | 0 | 66 |
| Savings per 1k req | $0.019 | $0.022 |

Misroute rate unchanged because NER moves hard prompts from `cloud` → `large_local`, not to `small_local`. Cost savings **increase** because fewer requests hit cloud API.

#### Cost assumptions

| Assumption | Value |
|------------|-------|
| Cloud model | `gpt-4o-mini` (`config/policy.yaml`) |
| Input price | **$0.15 / 1M tokens** |
| Output price | **$0.60 / 1M tokens** |
| Source | [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [gpt-4o-mini](https://developers.openai.com/api/docs/models/gpt-4o-mini) |
| Local inference | **$0 API cost** (hardware/electricity out of scope) |
| Avg input tokens/prompt | **11.9** (estimated: `len(prompt)/4`) |
| Avg output tokens/response | **50** (assumed; collection capped at 64) |

**Per cloud request cost:**
```
(11.9 / 1e6) × $0.15  +  (50 / 1e6) × $0.60  =  $0.0000318
```

**300-request totals (regex+NER):**
```
Always cloud:  300 × $0.0000318  =  $0.0095
Router (88 cloud):               $0.0029
Savings:                         $0.0066  (70.0%)
```

**Per 1,000 requests (resume-scale, regex+NER):**
```
Always cloud:  $0.032
Router:        $0.010
Savings:       $0.022  (~70% API cost reduction)
```

*Note: Dollar amounts are small because eval prompts are short (~12 input tokens). The **70% reduction** (with NER) is the current headline — was **61%** under regex-only on this same eval set.*

#### Honest error-cost tradeoff (regex+NER)

| Metric | Value |
|--------|------:|
| Ground-truth hard prompts | 44 / 300 (14.7%) |
| Hard prompts routed to `small_local` (false negatives) | **13** (29.5% of hard, **4.3%** of all prompts) |
| Hard prompts routed to `cloud` | 31 (70.5% of hard) |

**Read:** Router saves ~61% API cost by serving 62% of requests locally, at the cost of ~4% of all prompts being genuinely hard but sent to the small model anyway.

### Labeling fix (Aug 28, batch 1)

**Bug:** Old labels used raw cosine similarity of full model outputs (`≥ 0.85` → `small_sufficient=True`) with no length normalization or answer extraction. Short correct answers (`"12"`) scored poorly against discursive correct answers (`"The answer is 12, since…"`), mislabeling simple factual prompts as hard. 24/34 old `False` rows had cosine in the 0.72–0.85 band (threshold noise).

**Fix:** `packages/complexity_classifier/labeling.py` — for terse outputs (≤15 words on small or large model), substring/number agreement overrides low cosine; longer open-ended outputs still use cosine ≥ 0.85. Relabeled existing 150 prompts via `relabel.py` (re-ran models only for old `False` rows).

| | Before fix | After fix |
|--|------------|-----------|
| `True` (easy) | 116 (77.3%) | **123 (82.0%)** |
| `False` (hard) | 34 (22.7%) | **27 (18.0%)** |
| Labels changed | — | **7** (`False` → `True`, all factual short-answer) |

### Class distribution (relabeled)

| Split | `True` (easy) | `False` (hard) |
|-------|---------------|----------------|
| Full (150) | 123 (82.0%) | 27 (18.0%) |

### 5-fold CV — hand-crafted only (relabeled data)

| Metric | Old labels | Relabeled | Δ |
|--------|------------|-----------|---|
| **Accuracy** | 0.520 ± 0.034 | **0.640 ± 0.118** | +0.120 |
| **False precision** | 0.213 ± 0.077 | 0.298 ± 0.087 | +0.085 |
| **False recall** | 0.476 ± 0.257 | **0.680 ± 0.194** | +0.204 |
| **False F1** | **0.291 ± 0.124** | **0.412 ± 0.118** | **+0.121** |
| **True precision** | 0.789 ± 0.084 | 0.890 ± 0.080 | +0.101 |
| **True recall** | 0.535 ± 0.061 | 0.633 ± 0.117 | +0.098 |
| **True F1** | 0.632 ± 0.028 | **0.737 ± 0.107** | +0.105 |

**False-class F1 improved meaningfully** (+0.12) after fixing labels — noisy labels were likely the main bottleneck, not feature engineering.

#### Aggregated confusion matrix — hand-crafted only (relabeled)

```
                      pred=False  pred=True
  actual=False (hard):          18           9
  actual=True  (easy):          45          78
```

### Historical: hand-crafted vs embeddings on OLD labels (superseded)

Embeddings did not improve minority-class F1 on old labels (False F1 0.291 → 0.225). Do not use embedding features until labels are further validated.

<details>
<summary>Old-label CV table (pre-relabel)</summary>

| Metric | 6 hand-crafted | 6 + embedding (384-dim) | Δ |
|--------|----------------|-------------------------|---|
| **Accuracy** | 0.520 ± 0.034 | 0.580 ± 0.058 | +0.060 |
| **False F1** | **0.291 ± 0.124** | 0.225 ± 0.103 | −0.066 |
| **True F1** | 0.632 ± 0.028 | 0.706 ± 0.058 | +0.074 |

</details>

---

## Current routing behavior

Production policy (`config/policy.yaml`): **`dumb_routing.enabled: false`** — classifier drives complexity.

```
Prompt → sensitivity gate (regex + NER) + complexity classifier (model.pkl)
       → 2×2 policy table → small_local | large_local | cloud
       → telemetry logged with reason
```

Fallback / test policy (`config/policy.dumb.yaml`): character-count routing for comparison tests.

| Prompt type | Sensitivity | Typical route |
|-------------|-------------|---------------|
| Easy factual | LOW | `small_local` |
| Hard reasoning | LOW | `cloud` (when classifier predicts high complexity) |
| Any + PII | HIGH | `small_local` or `large_local` (never cloud) |

---

## What's working

- **Local inference** — `models/small/` (1.5B) and `models/large/` (7B Q4_K_M shards)
- **Data collection** — `collect_data.py` with memory-safe unload + `collect_batches.sh`
- **Training** — `train.py` → `model.pkl`
- **Classifier routing** — wired in `decide.py` when dumb routing is off
- **Telemetry** — `python -m telemetry.dashboard.cli --mode summary` (CLI) or web dashboard (below)
- **Sensitivity gate** — regex PII + spaCy NER (additive; see below)
- **Tests** — **43 passing** (`pytest -q --ignore=tests/test_local_runner.py`)

---

## Test layout

| Test file | What it covers |
|-----------|----------------|
| `test_router.py` | Sensitivity, dumb routing (via `policy.dumb.yaml`), mock e2e |
| `test_hard_rules.py` | `never_cloud_for_high_sensitivity` |
| `test_classifier_routing.py` | Classifier path when dumb routing is off |
| `test_features.py` | Hand-crafted + pattern feature extraction |
| `test_ner_sensitivity.py` | spaCy NER entity detection + combined gate |
| `test_chat_api.py` | `POST /api/chat` response shape + telemetry logging |
| `test_dashboard_api.py` | Web dashboard `/api/summary` and `/api/decisions` |
| `test_local_runner.py` | Model unload / memory (skipped if no GGUF) |

---

## Known gaps / next improvements

### Classifier tuning (next)
- **Labels improved but not perfect** — 7 factual mislabels fixed; remaining 27 `False` rows are mostly open-ended design/debug/analyze prompts (look correct on inspection) plus some factual rows where models genuinely disagree
- Hand-crafted feature separation jumped to **0.85** (char_length) on relabeled data — features now align better with labels
- Consider collecting more data once a few more borderline factual labels are manually reviewed

### Labeling v2 (Aug 28 — framework ready, data runs pending)

**Inspection (Step 1):** 10 disputed factual `False` rows surfaced via `inspect_false_labels.py`; 17 open-ended rows look correct. Of the 10: ~4 are substring-matching gaps (#1 purple, #3 100cm, #4 Rowling, #5 heart), ~2 are genuine small-model failures (#2 incomplete hours, #9 wrong eclipse duration), ~4 are medium explanatory (#6–#8, #10) — left as `False` by design.

**Approved fix (items 1–3, implemented in `labeling.py`):**
1. Safer key-phrase splitting (`you get X`, `written by X`; abbrev-aware period handling)
2. `answer_number_match` on short factual prompts (largest large-model number must appear in small output)
3. `answer_token_overlap` for distinctive answer tokens (skipped for `how many` prompts to avoid #2 false positives)

**Not implemented:** number-word normalization (item 4) — deferred.

**Scripts ready (not run yet):**
```bash
# Step 3: relabel only the 4 approved rows (~5 min)
python packages/complexity_classifier/relabel_prompts.py \
  "What color do you get by mixing red and blue?" \
  "How many centimeters are in one meter?" \
  "Who wrote the Harry Potter series?" \
  "What organ pumps blood through the body?"
# → backs up to data/labeled_requests_v2_backup.csv

# Step 4: collect 150 new prompts, append to CSV (~2-3 hrs)
./scripts/collect_batch2.sh 30

# Step 5: retrain + CV
python packages/complexity_classifier/train.py --handcrafted-only
```

**Batch 2 scripts:** `data/sample_prompts_batch2.txt`, `scripts/collect_batch2.sh` — **collected** (300 total rows).

### Labeling
- `packages/complexity_classifier/labeling.py` — cosine + substring + factual matchers
- `packages/complexity_classifier/relabel.py` — bulk re-label
- `packages/complexity_classifier/relabel_prompts.py` — targeted row relabel
- `packages/complexity_classifier/inspect_false_labels.py` — manual review helper
- Backups: `labeled_requests_v1_backup.csv` (pre-v1 fix), `labeled_requests_v2_backup.csv` (pre-v2 fix, created but v2 relabel not applied)

### Cloud path
- Set `OPENAI_API_KEY` to exercise real cloud routing (currently mock without key)

### v2 (optional)
- Anthropic adapter

---

## Sensitivity gate — NER (Aug 28)

**Status:** Done. `packages/sensitivity_gate/ner_classifier.py` runs **alongside** regex rules in `check_sensitivity()` — sensitive if **either** path flags the prompt. Regex logic unchanged.

**Install:**
```bash
pip install -e ".[ner]"
python -m spacy download en_core_web_sm
```

**Entity types flagged:** `PERSON`, `GPE` (location), `LOC`, `ORG`, `NORP` (nationality/group).  
**Not flagged:** `DATE`, `TIME`, `CARDINAL`, `MONEY`, `QUANTITY`, `PERCENT`, etc.

**Telemetry shape:** `matched_rules` includes regex names (`email`, …) and NER entries (`ner:PERSON`, `ner:GPE`, …). `triggers` lists human-readable reasons from both paths.

### Latency (measured, en_core_web_sm, 10 prompts × 200 iterations)

| Path | Mean | p50 | p95 |
|------|------|-----|-----|
| Regex only | 0.003 ms | 0.003 ms | 0.004 ms |
| NER only | 2.7 ms | 2.6 ms | 3.0 ms |
| Regex + NER | 2.8 ms | 2.8 ms | 3.6 ms |

**NER overhead:** ~**2.8 ms/request** (model loaded once at module init, not per request).

### Before / after (regex-only → regex + NER)

| Prompt | Before | After |
|--------|--------|-------|
| Please send the report to **Sarah Johnson** by end of day. | not sensitive | `ner:PERSON` |
| Ship the package to **Boston, Massachusetts** tomorrow. | not sensitive | `ner:GPE` |
| I work at **Acme Corporation** on a confidential project. | not sensitive | `ner:ORG` |
| Meet with **Dr. Emily Carter** at the downtown clinic. | not sensitive | `ner:PERSON` |
| Our team is relocating to **Austin, Texas** next quarter. | not sensitive | `ner:GPE` |
| Explain how photosynthesis converts light into chemical energy. | not sensitive | not sensitive |

**Note:** NER can false-positive on ambiguous tokens (e.g. “Will” as a name) — see `test_ner_sensitivity.py`. Junk entities (repeated single-char strings) are filtered out.

### NER false-positive probe (Aug 28, informal)

**28 ordinary prompts** with capitalized words / tech terms (not intended as PII): **8 flagged (28.6%)** by NER.

| Prompt | NER trigger |
|--------|-------------|
| "The Chase account was updated." | `ner:ORG` → Chase |
| "Jordan scored 30 points last night." | `ner:GPE` → Jordan |
| "Victor won the chess tournament." | `ner:PERSON` → Victor |
| "Write a function to sort a list in Python." | `ner:GPE` → Python |
| "Compare SQL and NoSQL for analytics workloads." | `ner:ORG`/`ner:GPE` |

**Did not flag:** "Will this work?", "May I ask a question?", "Grant me access to the file.", "Mark the checkbox…", "Hope you are doing well."

**Read:** High false-positive rate on tech/product names and ambiguous capitalized words; acceptable for privacy-biased routing but inflates `large_local` share on technical eval prompts (see cost table above). Not fixed — documented limitation.

### `large_local` path verification (Aug 28)

Exercised **high complexity + high sensitivity** (classifier + NER/regex) on production `policy.yaml`:

| Prompt (abbrev.) | Sensitive rules | Target | Complexity |
|------------------|-----------------|--------|------------|
| Design pipeline for SSN 123-45-6789… | `ssn`, `ner:ORG` | **large_local** | 0.97 (HIGH) |
| Analyze Memorial Hospital security; email alice@… | `email`, `ner:ORG` | **large_local** | 0.99 (HIGH) |
| Build GDPR system for Sarah Johnson's team… | `ner:PERSON`, `ner:ORG` | **large_local** | 0.99 (HIGH) |

Reason pattern: `classifier:… complexity=HIGH; sensitivity=HIGH -> large_local`. Test: `test_high_complexity_and_sensitive_routes_to_large_local` in `test_classifier_routing.py`.

---

## Web telemetry dashboard

Observability UI over `telemetry/routing.db` — routing history and aggregate stats (not a chat interface).

**Stack:** FastAPI JSON API + plain HTML/CSS/JS (`telemetry/dashboard/web/`). CLI viewer unchanged (`telemetry/dashboard/cli.py`).

**Install (one-time):**
```bash
pip install -e ".[web]"
```

**Run:**
```bash
# Seed data first if DB is empty (router logs every generate_text call):
python scripts/demo.py "What is the capital of France?"

# Start dashboard (default http://127.0.0.1:8765)
python -m telemetry.dashboard.web.app
```

**What it shows:**
- Summary cards: total requests, % per target (`small_local` / `large_local` / `cloud`), avg latency per target, estimated API cost savings vs always-cloud (gpt-4o-mini pricing from `telemetry/cost.py`)
- Bar chart of target distribution
- Paginated, filterable table of recent decisions (timestamp, prompt preview, target, reason, complexity score, sensitivity, latency)

**API (read-only):**
- `GET /api/summary` — aggregates + cost comparison
- `GET /api/decisions?limit=50&offset=0&target=cloud` — paginated decision log

---

## Web chat UI (Aug 28)

Interactive demo surface on the **same server** as the telemetry dashboard — type a message, get a real routed response, see target/reason inline.

**URLs:**
- Telemetry: http://127.0.0.1:8765/
- Chat: http://127.0.0.1:8765/chat

**Run** (same command as dashboard):
```bash
pip install -e ".[web,local,cloud,ner]"
python -m telemetry.dashboard.web.app
```

**What it does:**
- `POST /api/chat` runs the full router pipeline via `Router.generate_text()` (sensitivity gate + classifier + policy + execution)
- Returns response text, target, reason, complexity score, sensitivity flag/triggers, latency
- Every chat message is logged to `telemetry/routing.db` (shows up on the telemetry page)
- UI: chat-style history, loading state, inline errors (e.g. missing `OPENAI_API_KEY`), expandable routing details per reply

**Execution:** Uses the **real execution layer** when configured — local GGUF models from `config/policy.yaml` paths, cloud via `OPENAI_API_KEY`. Falls back to mock responses only when models/API key are unavailable (noted in routing details).

**Nav:** Links between `/` (telemetry) and `/chat` in the header.

---

## How to verify

```bash
pip install -e ".[dev,local,ml,ner]"

pytest -q

# Threshold sweep + 12-feature CV (long-running):
python packages/complexity_classifier/train.py --handcrafted-only --skip-inspection
python -m telemetry.dashboard.cli --mode summary
python -m telemetry.dashboard.web.app   # telemetry: /  chat: /chat
```

### Data collection (if re-running)

```bash
python packages/complexity_classifier/collect_data.py --limit 3 --max-tokens 32  # smoke test
./scripts/collect_batches.sh 30                                                  # full run
```

---

## File map

```
├── config/
│   ├── policy.yaml           ✅ production (classifier on, dumb off)
│   └── policy.dumb.yaml      ✅ test / fallback (dumb routing on)
├── data/
│   ├── sample_prompts.txt         ✅ 150 prompts (batch 1)
│   ├── sample_prompts_batch2.txt  ✅ 150 prompts (batch 2, not collected yet)
│   ├── labeled_requests.csv       ✅ 150 labeled rows (v1 relabel applied)
│   ├── labeled_requests_v1_backup.csv
│   └── labeled_requests_v2_backup.csv  (snapshot before v2 relabel — not applied)
├── packages/
│   ├── complexity_classifier/
│   │   ├── labeling.py            ✅ v2 matchers (items 1-3)
│   │   ├── relabel_prompts.py     ✅ targeted relabel
│   │   ├── inspect_false_labels.py ✅ disputed-row inspection
│   │   ├── relabel.py
│   │   ├── collect_data.py
│   │   ├── train.py               ✅ --handcrafted-only
│   │   ├── predict.py        ✅ inference
│   │   ├── vectorize.py      ✅ feature → numpy
│   │   └── model.pkl         ✅ trained artifact
│   ├── routing_engine/decide.py  ✅ classifier + dumb paths
│   └── execution/local_runner.py ✅ unload() for memory
├── scripts/
│   ├── analyze_routing_cost.py  ✅ routing distribution + cost analysis
│   ├── collect_batches.sh    ✅ batch 1 collection
│   └── collect_batch2.sh     ✅ batch 2 collection (ready, not run)
├── telemetry/
│   ├── logger.py             ✅ SQLite routing log
│   ├── cost.py               ✅ shared cloud cost math
│   └── dashboard/
│       ├── cli.py            ✅ CLI summary / recent
│       └── web/              ✅ FastAPI + static dashboard
└── tests/                    ✅ 29 tests (incl. dashboard API)
```

---

## Resume bullets (fill in for applications)

> Architected an adaptive inference-routing SDK that dynamically selects between local and cloud LLM execution based on real-time complexity and data-sensitivity classification, enforcing hard privacy constraints on sensitive requests.

> Trained a complexity classifier (logistic regression, **76.7% accuracy**, **100% recall** on held-out set) to predict task difficulty pre-inference, labeling 150 prompts via embedding similarity between small and large local model outputs.
