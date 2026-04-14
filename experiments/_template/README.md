# Experiment: [Your Experiment Name]

One-line description of what this experiment optimizes.

## What it optimizes

`data/prompt.txt` — [describe the prompt: what it's sent to, what it produces]

## How it works

Each cycle:
1. **Generate** — [describe what generate.py produces]
2. **Evaluate** — [describe how evaluate.py scores the output]
3. **Score** — N items × M criteria = max score
4. **Keep** the prompt if score improves
5. **Mutate** — Claude rewrites the prompt to fix failures

## Evaluation criteria

| Criterion | Check | Description |
|---|---|---|
| `criterion_one` | rule/llm | What passes |
| `criterion_two` | rule/llm | What passes |
| `criterion_three` | rule/llm | What passes |

## Setup

```bash
# API keys in .env at repo root
ANTHROPIC_API_KEY=your_key
# Add other keys as needed
```

## Run

```bash
python run.py your-experiment-name --once
python run.py your-experiment-name --cycles 10
python run.py your-experiment-name
```

## Steps to create a new experiment from this template

1. Copy `experiments/_template/` to `experiments/your-name/`
2. Edit `config.yaml` — set name, description, criteria
3. Implement `generate.py` — call your model/API, return an artifact
4. Implement `evaluate.py` — check your criteria, return bools
5. Write an initial prompt in `data/prompt.txt`
6. Run: `python run.py your-name --once`
