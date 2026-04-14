"""
State management for autoimprove experiments.

Each experiment keeps its state in:
  experiments/{name}/data/state.json    — best score, run counter, validation set
  experiments/{name}/data/results.jsonl — append-only run log
  experiments/{name}/data/prompt.txt    — current working prompt
  experiments/{name}/data/best_prompt.txt — best prompt found so far
"""

import json
from pathlib import Path


def load_state(data_dir: Path) -> dict:
    f = data_dir / "state.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"best_score": -1, "run_number": 0, "validation_set": []}


def save_state(data_dir: Path, state: dict):
    (data_dir / "state.json").write_text(json.dumps(state, indent=2))


def load_prompt(data_dir: Path) -> str:
    return (data_dir / "prompt.txt").read_text().strip()


def save_prompt(data_dir: Path, prompt: str):
    (data_dir / "prompt.txt").write_text(prompt)


def save_best_prompt(data_dir: Path, prompt: str):
    (data_dir / "best_prompt.txt").write_text(prompt)


def load_best_prompt(data_dir: Path) -> str | None:
    f = data_dir / "best_prompt.txt"
    return f.read_text().strip() if f.exists() else None


def append_result(data_dir: Path, entry: dict):
    with open(data_dir / "results.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_results(data_dir: Path) -> list[dict]:
    f = data_dir / "results.jsonl"
    if not f.exists():
        return []
    results = []
    for line in f.read_text().strip().split("\n"):
        if line.strip():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return results
