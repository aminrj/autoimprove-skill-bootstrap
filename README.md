# autoimprove-skills-bootstrap

A multi-experiment framework for the **Karpathy autoresearch pattern** — applied to anything with a measurable output.

The idea: let an AI agent run experiments on its own, measure the results, keep what works, throw away what doesn't, and repeat until it's good.

---

## The pattern

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   GENERATE  │───▶│  EVALUATE   │───▶│  KEEP/DISC  │───▶│   MUTATE    │
│             │    │             │    │             │    │             │
│ prompt +    │    │ binary      │    │ score >     │    │ Claude      │
│ topic →     │    │ yes/no      │    │ best?       │    │ rewrites    │
│ artifact    │    │ criteria    │    │ save/revert │    │ prompt      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
        ▲                                                        │
        └────────────────────────────────────────────────────────┘
                              repeat every N minutes
```

**Three ingredients** for any autoimprove experiment:

| Ingredient | What it is | Example |
|---|---|---|
| Something to optimize | `data/prompt.txt` | Gemini image prompt, Claude writing prompt |
| Something to measure | Binary yes/no criteria | Is the diagram linear? Is the title ≤60 chars? |
| Something that produces it | `generate.py` + `evaluate.py` | Gemini image gen, Claude text gen |

---

## Experiments

### [diagrams](experiments/diagrams/) — Whiteboard diagram generation
Optimizes a prompt for generating whiteboard-style technical diagrams via Gemini.
- **Baseline**: 32/40 → **Best**: 40/40 perfect score in 12 minutes
- Generator: Gemini image generation | Evaluator: Claude vision

### [blog-seo](experiments/blog-seo/) — Blog SEO front matter
Optimizes a prompt that generates SEO-compliant front matter for [aminrj.com](https://aminrj.com) (Chirpy/Jekyll).
- Generator: Claude | Evaluator: rule-based (no LLM cost for eval)
- 5 criteria: title length, description length, H1 count, alt text, internal links

---

## Quick start

```bash
# Install dependencies
pip install anthropic google-genai python-dotenv pyyaml

# Set API keys
cp .env.example .env  # then fill in your keys

# List experiments
python run.py --list

# Run a single cycle
python run.py diagrams --once
python run.py blog-seo --once

# Run continuous loops
python run.py diagrams          # 2-minute cycles
python run.py blog-seo          # 90-second cycles

# Dashboard (all experiments)
python core/dashboard.py        # open http://localhost:8501
```

---

## Repo structure

```
autoimprove-skills-bootstrap/
├── run.py                    ← entry point: python run.py <experiment>
├── core/
│   ├── loop.py               ← generic generate→evaluate→keep/discard→mutate loop
│   ├── state.py              ← state.json + results.jsonl management
│   └── dashboard.py          ← multi-experiment live dashboard
└── experiments/
    ├── _template/            ← starter kit for new experiments
    ├── diagrams/             ← whiteboard diagram generation (Gemini)
    └── blog-seo/             ← blog SEO front matter (Claude → Chirpy)
```

Each experiment contains:
```
experiments/your-name/
├── README.md         ← what it optimizes and how to run it
├── config.yaml       ← criteria, model choices, timing, batch size
├── generate.py       ← generate(prompt, topic) → artifact
├── evaluate.py       ← evaluate(artifact) → {criterion_id: bool}
└── data/
    ├── prompt.txt        ← current prompt being tested
    ├── best_prompt.txt   ← best prompt found so far
    ├── state.json        ← run counter + best score
    └── results.jsonl     ← full history of every cycle
```

---

## Add a new experiment

1. Copy the template: `cp -r experiments/_template experiments/my-experiment`
2. Edit `config.yaml` — name, description, 3-6 binary criteria
3. Implement `generate.py` — call any model/API, return an artifact
4. Implement `evaluate.py` — check criteria, return bools
5. Write a starting prompt in `data/prompt.txt`
6. Run: `python run.py my-experiment --once`

The loop handles everything else: state, scoring, mutation, dashboard.

---

## Local LLMs (RTX 3090)

Any experiment can use a local Ollama model. In `config.yaml`:

```yaml
generator:
  provider: ollama
  model: llava:13b          # or any model you have locally
  endpoint: http://localhost:11434
```

Then update `generate.py` to call the Ollama endpoint. The evaluator can stay on Claude,
or you can swap it too if you have a local vision model.

---

## Dashboard

```bash
python core/dashboard.py
# open http://localhost:8501
```

Auto-discovers all experiments and shows a tab per experiment:
score over time, criterion breakdowns, run history, best prompt.

---

## Inspiration

- [Andrej Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — the original pattern (March 2026)
- [Nick Saraev's YouTube video](https://youtube.com) — applied to diagram generation (March 2026)
- [Blog post](inspiration-blog-post.local.md) — how this framework was built
