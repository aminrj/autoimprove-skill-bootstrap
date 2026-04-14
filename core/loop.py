"""
Generic autoimprove loop engine.

The Karpathy autoresearch pattern, generalized:

  1. GENERATE  — produce a batch of artifacts using the current prompt
  2. EVALUATE  — score each artifact against binary yes/no criteria
  3. SCORE     — count passes per criterion → total out of max
  4. KEEP/DISCARD — save prompt if score beats the current best
  5. MUTATE    — ask Claude to improve the prompt based on failures
  6. REPEAT

Each experiment plugs in two functions:
  generate(prompt, topic) → artifact
  evaluate(artifact)      → {criterion_id: bool, ...}

Everything else (state, scoring, mutation, logging) is handled here.
"""

import json
import os
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from core import state as st

# Generic mutation template — works for any experiment
_MUTATION_TEMPLATE = """You are optimizing a prompt for the following task:
  {experiment_name}

The prompt is sent to an AI model. Its outputs are evaluated against {n_criteria} binary (yes/no) criteria.
Your goal: rewrite the prompt so outputs consistently pass ALL criteria.

CURRENT PROMPT:
---
{current_prompt}
---

LAST BATCH RESULTS ({score}/{max_score}):
{criteria_lines}

RECENT FAILURES:
{failures}

BEST SCORE SO FAR: {best_score}/{max_score}

INSTRUCTIONS:
- Keep the core intent of the prompt intact
- For any criterion below 80%, add explicit, specific language to address failures
- Be direct and imperative — AI models respond to clear commands, not vague hints
- Address the most common failure patterns first
- Keep the rewritten prompt under 500 words
- Return ONLY the new prompt text — no explanation, no markdown fences"""


def _load_topics(config: dict, data_dir: Path, state: dict) -> list[str]:
    """Return a list of topic strings based on the config source type."""
    source = config.get("source", {})
    source_type = source.get("type", "list")

    if source_type == "list":
        # Topics are defined in the experiment module — loaded by caller
        raise ValueError("topic list must be passed directly for source.type=list")

    if source_type == "local_files":
        path = Path(source["path"]).expanduser()
        pattern = source.get("pattern", "*.md")
        all_files = sorted(str(p) for p in path.glob(pattern))
        if not all_files:
            raise FileNotFoundError(f"No files found at {path}/{pattern}")

        validation_set = state.get("validation_set", [])
        # On first run, pick and lock the validation set
        if not validation_set:
            n_val = min(source.get("validation_set_size", 5), len(all_files))
            validation_set = random.sample(all_files, n_val)
            state["validation_set"] = validation_set
            print(f"  Fixed validation set ({len(validation_set)} posts):")
            for p in validation_set:
                print(f"    {Path(p).name}")

        # Sample rotating posts to fill up to batch_size
        batch_size = config.get("batch_size", 8)
        rotating_pool = [f for f in all_files if f not in validation_set]
        n_rotating = max(0, batch_size - len(validation_set))
        rotating = random.sample(rotating_pool, min(n_rotating, len(rotating_pool)))

        return validation_set + rotating

    raise ValueError(f"Unknown source type: {source_type}")


def _mutation_prompt(config: dict, current_prompt: str, scores_per_criterion: dict,
                     all_failures: list[str], best_score: int) -> str:
    """Build the mutation prompt from config criteria + run results."""
    criteria = config["criteria"]
    batch_size = config.get("batch_size", 10)
    max_score = len(criteria) * batch_size

    lines = []
    for c in criteria:
        cid = c["id"]
        score = scores_per_criterion.get(cid, 0)
        pct = int(score / batch_size * 100)
        lines.append(f"  - {c['description']}: {score}/{batch_size} ({pct}%)")

    unique_failures = list(dict.fromkeys(all_failures))[:20]
    failures_text = "\n".join(f"  - {f}" for f in unique_failures) if unique_failures else "  - None recorded"

    total = sum(scores_per_criterion.values())

    return _MUTATION_TEMPLATE.format(
        experiment_name=config["name"],
        n_criteria=len(criteria),
        current_prompt=current_prompt,
        score=total,
        max_score=max_score,
        criteria_lines="\n".join(lines),
        failures=failures_text,
        best_score=best_score,
    )


def _call_mutation(config: dict, current_prompt: str, scores_per_criterion: dict,
                   all_failures: list[str], best_score: int) -> str:
    """Ask Claude to rewrite the prompt based on failure analysis."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    mutate_model = config.get("mutator", {}).get("model", "claude-sonnet-4-6")
    prompt = _mutation_prompt(config, current_prompt, scores_per_criterion, all_failures, best_score)

    response = client.messages.create(
        model=mutate_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def run_cycle(experiment_dir: Path, config: dict,
              generate_fn, evaluate_fn,
              topics: list[str], state: dict) -> dict:
    """
    Run one autoresearch optimization cycle.

    Args:
        experiment_dir: path to experiments/{name}/
        config:         loaded config.yaml
        generate_fn:    generate(prompt, topic) → artifact
        evaluate_fn:    evaluate(artifact) → {criterion_id: bool}
        topics:         list of topic strings for this cycle
        state:          current state dict (mutated in place)

    Returns:
        updated state dict
    """
    data_dir = experiment_dir / "data"
    criteria = config["criteria"]
    batch_size = config.get("batch_size", len(topics))
    max_workers_gen = config.get("max_workers_generate", 3)
    max_workers_eval = config.get("max_workers_evaluate", 5)
    max_score = len(criteria) * batch_size

    run_num = state["run_number"] + 1
    state["run_number"] = run_num
    prompt = st.load_prompt(data_dir)
    batch = topics[:batch_size]

    print(f"\n{'='*60}")
    print(f"RUN {run_num} | {datetime.now().strftime('%H:%M:%S')} | Best: {state['best_score']}/{max_score}")
    print(f"{'='*60}")

    # ── 1. GENERATE ───────────────────────────────────────────────
    print(f"\n  Generating {len(batch)} artifacts...")
    artifacts: list[tuple[int, str, object]] = []

    with ThreadPoolExecutor(max_workers=max_workers_gen) as pool:
        futures = {pool.submit(generate_fn, prompt, topic): (i, topic)
                   for i, topic in enumerate(batch)}
        for future in as_completed(futures):
            i, topic = futures[future]
            try:
                artifact = future.result()
            except Exception as e:
                artifact = None
                print(f"    [{i+1}/{len(batch)}] GEN ERROR: {e}")
            if artifact is not None:
                artifacts.append((i, topic, artifact))
                label = Path(topic).name if os.path.exists(topic) else topic[:50]
                print(f"    [{i+1}/{len(batch)}] ok: {label}")
            else:
                print(f"    [{i+1}/{len(batch)}] FAILED")

    if not artifacts:
        print("  ERROR: nothing generated — skipping cycle")
        st.save_state(data_dir, state)
        return state

    # ── 2. EVALUATE ───────────────────────────────────────────────
    print(f"\n  Evaluating {len(artifacts)} artifacts...")
    eval_results: list[dict] = []
    all_failures: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers_eval) as pool:
        futures = {pool.submit(evaluate_fn, artifact): (i, topic)
                   for i, topic, artifact in artifacts}
        for future in as_completed(futures):
            i, topic = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = None
                print(f"    [{i+1}] EVAL ERROR: {e}")

            if result:
                eval_results.append(result)
                passes = sum(result.get(c["id"], False) for c in criteria)
                fails = result.get("failures", [])
                all_failures.extend(fails)
                label = Path(topic).name if os.path.exists(topic) else topic[:40]
                print(f"    [{i+1}] {passes}/{len(criteria)} — {label}"
                      + (f" | {'; '.join(fails[:2])}" if fails else ""))
            else:
                # Count as all-fail so it doesn't skew scores
                fallback = {c["id"]: False for c in criteria}
                fallback["failures"] = ["eval_error"]
                eval_results.append(fallback)
                print(f"    [{i+1}] 0/{len(criteria)} — eval failed")

    # ── 3. SCORE ──────────────────────────────────────────────────
    scores_per_criterion = {
        c["id"]: sum(1 for r in eval_results if r.get(c["id"]))
        for c in criteria
    }
    total_score = sum(scores_per_criterion.values())

    print(f"\n  SCORE: {total_score}/{max_score}")
    for c in criteria:
        cid = c["id"]
        s = scores_per_criterion[cid]
        label = c.get("label", cid.replace("_", " ").title())
        bar = "█" * s + "░" * (batch_size - s)
        print(f"    {label:<22} {s:>2}/{batch_size} {bar}")

    # ── 4. LOG ────────────────────────────────────────────────────
    st.append_result(data_dir, {
        "run": run_num,
        "timestamp": datetime.now().isoformat(),
        "score": total_score,
        "max": max_score,
        "criteria": scores_per_criterion,
        "prompt_len": len(prompt),
        "generated": len(artifacts),
    })

    # ── 5. KEEP OR DISCARD ────────────────────────────────────────
    prev_best = state["best_score"]
    if total_score > prev_best:
        state["best_score"] = total_score
        st.save_best_prompt(data_dir, prompt)
        print(f"\n  NEW BEST! {total_score}/{max_score} (was {prev_best})")
    else:
        print(f"\n  No improvement ({total_score} vs best {prev_best})")

    # ── 6. MUTATE ─────────────────────────────────────────────────
    if total_score < max_score:
        print("\n  Mutating prompt...")
        base = st.load_best_prompt(data_dir) or prompt
        new_prompt = _call_mutation(config, base, scores_per_criterion, all_failures, state["best_score"])
        st.save_prompt(data_dir, new_prompt)
        print(f"  New prompt ({len(new_prompt)} chars): {new_prompt[:120].replace(chr(10), ' ')}...")
    else:
        print(f"\n  PERFECT {max_score}/{max_score}! Prompt fully optimized.")

    st.save_state(data_dir, state)
    return state


def run_loop(experiment_dir: Path, config: dict, generate_fn, evaluate_fn,
             topics_list: list[str] | None = None,
             once: bool = False, max_cycles: int = 0):
    """
    Entry point for running an experiment.

    Args:
        experiment_dir:  path to experiments/{name}/
        config:          loaded config.yaml
        generate_fn:     generate(prompt, topic) → artifact
        evaluate_fn:     evaluate(artifact) → {criterion_id: bool}
        topics_list:     static topic list (for source.type=list experiments)
        once:            run exactly one cycle then exit
        max_cycles:      run N cycles (0 = infinite)
    """
    data_dir = experiment_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    state = st.load_state(data_dir)
    cycle_seconds = config.get("interval_seconds", 120)
    n_criteria = len(config["criteria"])
    batch_size = config.get("batch_size", 10)

    print(f"\n{config['name']}")
    print(f"  Criteria:   {n_criteria} × {batch_size} = {n_criteria * batch_size} max")
    print(f"  Interval:   {cycle_seconds}s")
    print(f"  State:      run {state['run_number']}, best {state['best_score']}/{n_criteria * batch_size}")

    limit = 1 if once else (max_cycles or float("inf"))
    i = 0
    while i < limit:
        start = time.time()
        try:
            # Resolve topics for this cycle
            source = config.get("source", {})
            if source.get("type", "list") == "local_files":
                topics = _load_topics(config, data_dir, state)
            else:
                if topics_list is None:
                    raise ValueError("topics_list required for source.type=list")
                topics = random.sample(topics_list, min(batch_size, len(topics_list)))

            state = run_cycle(experiment_dir, config, generate_fn, evaluate_fn, topics, state)

        except Exception as e:
            print(f"\n  CYCLE ERROR: {e}")
            traceback.print_exc()

        elapsed = time.time() - start
        i += 1

        if i < limit:
            wait = max(0, cycle_seconds - elapsed)
            if wait > 0:
                print(f"\n  Waiting {wait:.0f}s until next cycle...")
                time.sleep(wait)
            else:
                print(f"\n  Cycle took {elapsed:.0f}s (>{cycle_seconds}s budget)")

    best = state["best_score"]
    max_s = n_criteria * batch_size
    print(f"\nDone. Best score: {best}/{max_s}")
    best_p = st.load_best_prompt(data_dir)
    if best_p:
        print(f"Best prompt saved to: {data_dir}/best_prompt.txt")
