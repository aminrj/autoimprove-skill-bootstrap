# Experiment: Whiteboard Diagram Generation

Optimizes a prompt for generating whiteboard-style technical diagrams via Gemini image generation.

## What it optimizes

`data/prompt.txt` — the prompt sent to Gemini's image generation model.

## How it works

Each cycle:
1. **Generate** 10 diagrams from 10 randomly sampled technical topics
2. **Evaluate** each diagram via Claude vision against 4 binary criteria
3. **Score** — count passes: 10 diagrams × 4 criteria = 40 points max
4. **Keep** the prompt if score beats the current best
5. **Mutate** — Claude rewrites the prompt to fix the most common failures

## Evaluation criteria (4 binary)

| Criterion | Description |
|---|---|
| `legible_and_grammatical` | All text readable, correctly spelled, grammatically correct |
| `pastel_colors` | Only soft pastel fills; no bright/saturated/dark colors |
| `linear_layout` | Strictly left-to-right OR top-to-bottom — no branching/radial |
| `no_numbers` | Zero digits, ordinals, or sequence numbers anywhere |

## Results so far

- **Baseline** (Run 1): 32/40
- **Best** (Run 6): 40/40 — perfect score in ~12 minutes

## Setup

```bash
# Required API keys in .env
NANO_BANANA_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
```

## Run

```bash
# From repo root:
python run.py diagrams --once       # single cycle
python run.py diagrams --cycles 5   # 5 cycles
python run.py diagrams              # infinite loop (2 min intervals)
```

## Local LLM (RTX 3090)

Change `config.yaml`:
```yaml
generator:
  provider: ollama
  model: llava:13b           # or any image-gen model you have
  endpoint: http://localhost:11434
```

Then update `generate.py` to use the Ollama endpoint instead of Gemini.
