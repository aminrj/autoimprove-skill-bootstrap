# Experiment: Blog SEO Front Matter

Optimizes a prompt that generates SEO-compliant front matter suggestions for [aminrj.com](https://aminrj.com) — a technical blog built with Jekyll + Chirpy theme.

## What it optimizes

`data/prompt.txt` — the prompt Claude uses to analyze a blog post and suggest SEO improvements (title, description, H1 structure, alt text, internal links).

## How it works

Each cycle:
1. **Sample** 8 posts from `~/git/aminrj.com/_posts/` (5 fixed validation posts + 3 rotating)
2. **Generate** — Claude reads each post + applies the optimization prompt → returns structured SEO suggestions as JSON
3. **Evaluate** — rule-based checks on the suggestions (no LLM needed for eval)
4. **Score** — 8 posts × 5 criteria = 40 points max
5. **Keep** the prompt if score beats the current best
6. **Mutate** — Claude rewrites the prompt to fix the most common failures

## Evaluation criteria (5 binary)

| Criterion | Check | Description |
|---|---|---|
| `title_under_60` | rule | title ≤ 60 characters |
| `description_120_160` | rule | description is 120-160 characters |
| `single_h1` | rule | h1_count == 1 (Chirpy renders front matter title as H1) |
| `images_have_alt` | rule | all alt texts are descriptive (not empty/generic) |
| `internal_links` | rule | ≥ 2 internal `/posts/` links suggested |

All checks are rule-based — fast, cheap, deterministic.

## Eval isolation

The evaluator (`evaluate.py`) never sees the optimization prompt. It only receives the structured JSON output and judges it by the numbers. This prevents the model from grading its own suggestions charitably.

## Setup

```bash
# The blog repo must be cloned at ~/git/aminrj.com/
# (or change the path in config.yaml)

ANTHROPIC_API_KEY=your_key  # in .env at repo root
```

## Run

```bash
# From repo root:
python run.py blog-seo --once       # single cycle
python run.py blog-seo --cycles 5   # 5 cycles
python run.py blog-seo              # infinite loop (90s intervals)
```

## End result

`data/best_prompt.txt` is a battle-tested prompt for generating SEO-compliant front matter. Apply it to any post:

```python
from experiments.blog_seo.generate import generate
from pathlib import Path

prompt = Path("experiments/blog-seo/data/best_prompt.txt").read_text()
suggestion = generate(prompt, "~/git/aminrj.com/_posts/2024-01-15-my-post.md")
print(suggestion)
# {"title": "...", "description": "...", "h1_count": 1, "alt_texts": [...], "internal_links": [...]}
```

## Adapting for other blogs

Change `config.yaml`:
```yaml
source:
  path: "~/path/to/your/_posts"
```

For non-Chirpy themes, update the initial `data/prompt.txt` to match your front matter field names.
