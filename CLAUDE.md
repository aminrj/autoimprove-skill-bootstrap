# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY (and GEMINI_API_KEY for diagrams)

# Run experiments
python run.py --list                     # list available experiments
python run.py <experiment> --once        # single cycle
python run.py <experiment> --cycles N   # N cycles
python run.py <experiment>              # continuous loop

# Dashboard
python core/dashboard.py   # Streamlit dashboard at http://localhost:8501
```

No test suite or linter config exists in the repo. `ruff` is available (`.ruff_cache` present) but not configured.

## Architecture

The framework implements the **Karpathy autoresearch loop**: generate → evaluate → keep/discard → mutate → repeat.

### Core engine (`core/`)

- **`core/loop.py`** — the generic loop engine. `run_loop()` is the top-level entry; `run_cycle()` runs one iteration: parallel generation via `ThreadPoolExecutor`, parallel evaluation, scoring, best-prompt bookkeeping, and Claude-driven mutation. The mutator (`_call_mutation`) rewrites `prompt.txt` based on per-criterion failure rates.
- **`core/state.py`** — thin wrappers for reading/writing `state.json`, `results.jsonl`, `prompt.txt`, and `best_prompt.txt` under each experiment's `data/` directory.
- **`core/dashboard.py`** — Streamlit multi-tab dashboard; auto-discovers all experiments by scanning `experiments/*/data/results.jsonl`.

### Experiment plug-in contract

Each experiment under `experiments/<name>/` provides:

| File | Contract |
|------|----------|
| `config.yaml` | `name`, `criteria` (list of `{id, label, description}`), `batch_size`, `interval_seconds`, `source`, `generator`, `evaluator`, `mutator` |
| `generate.py` | `generate(prompt: str, topic: str) → artifact \| None`; optionally `TOPICS = [...]` when `source.type: list` |
| `evaluate.py` | `evaluate(artifact) → {criterion_id: bool, ..., "failures": [str]}`; **must not** see the optimization prompt (eval isolation) |

`run.py` dynamically imports these modules via `importlib` and passes the functions to `run_loop`.

### Source types

- `source.type: list` — topics come from `TOPICS` in `evaluate.py`; a random `batch_size` subset is sampled each cycle.
- `source.type: local_files` — scans a directory for files matching `pattern`; on first run locks a fixed validation set in `state.json["validation_set"]` for apples-to-apples comparison across cycles.

### Provider support

`generator`, `evaluator`, and `mutator` blocks in `config.yaml` accept `provider: anthropic | ollama`. Ollama calls go to `http://localhost:11434` (RTX 3090 local inference). The mutator always uses Anthropic by default unless `provider: ollama` is set explicitly.

### Adding a new experiment

1. `cp -r experiments/_template experiments/my-experiment`
2. Fill in `config.yaml` (name, 3–6 binary criteria, source, models)
3. Implement `generate.py` → return any artifact type
4. Implement `evaluate.py` → return `{criterion_id: bool, failures: [str]}`
5. Write a starting prompt in `data/prompt.txt`
6. Run: `python run.py my-experiment --once`

### State files (per experiment, under `experiments/<name>/data/`)

| File | Purpose |
|------|---------|
| `state.json` | `run_number`, `best_score`, `validation_set` |
| `results.jsonl` | Append-only run history (score, criteria breakdown, timestamp) |
| `prompt.txt` | Current working prompt (mutated each cycle) |
| `best_prompt.txt` | Best-scoring prompt found so far |
| `artifacts/run-N/` | Persisted artifacts from each cycle for inspection |
