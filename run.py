#!/usr/bin/env python3
"""
Autoimprove — run any experiment by name.

Usage:
    python run.py <experiment>                   # continuous loop
    python run.py <experiment> --once            # single cycle
    python run.py <experiment> --cycles N        # run N cycles
    python run.py --list                         # list available experiments

Examples:
    python run.py diagrams --once
    python run.py blog-seo --cycles 5
    python run.py diagrams
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

REPO_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = REPO_DIR / "experiments"

# Make core/ and experiments/ importable
sys.path.insert(0, str(REPO_DIR))


def list_experiments():
    exps = []
    for d in sorted(EXPERIMENTS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        cfg_file = d / "config.yaml"
        name = d.name
        desc = ""
        if cfg_file.exists():
            try:
                cfg = yaml.safe_load(cfg_file.read_text())
                name = cfg.get("name", d.name)
                desc = cfg.get("description", "")
            except Exception:
                pass
        exps.append((d.name, name, desc))
    return exps


def load_experiment(exp_id: str):
    """Load generate and evaluate modules from experiments/{exp_id}/."""
    exp_dir = EXPERIMENTS_DIR / exp_id
    if not exp_dir.exists():
        print(f"ERROR: experiment '{exp_id}' not found at {exp_dir}")
        sys.exit(1)

    def load_module(filename):
        spec = importlib.util.spec_from_file_location(filename, exp_dir / filename)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    gen_mod = load_module("generate.py")
    eval_mod = load_module("evaluate.py")
    return gen_mod, eval_mod


def main():
    parser = argparse.ArgumentParser(
        description="Run an autoimprove experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("experiment", nargs="?", help="Experiment name (folder under experiments/)")
    parser.add_argument("--once", action="store_true", help="Run a single cycle then exit")
    parser.add_argument("--cycles", type=int, default=0, help="Run N cycles (0 = infinite)")
    parser.add_argument("--list", action="store_true", help="List available experiments")
    args = parser.parse_args()

    if args.list or not args.experiment:
        exps = list_experiments()
        if not exps:
            print("No experiments found under experiments/")
        else:
            print("Available experiments:")
            for exp_id, name, desc in exps:
                print(f"  {exp_id:<20} {name}")
                if desc:
                    print(f"  {'':20} {desc}")
        sys.exit(0)

    exp_id = args.experiment
    exp_dir = EXPERIMENTS_DIR / exp_id
    cfg_file = exp_dir / "config.yaml"

    if not cfg_file.exists():
        print(f"ERROR: config.yaml not found at {cfg_file}")
        sys.exit(1)

    config = yaml.safe_load(cfg_file.read_text())

    # Load experiment modules
    gen_mod, eval_mod = load_experiment(exp_id)

    # Diagrams experiment: set per-cycle run_dir on generate module
    # and wire up TOPICS from evaluate module
    from core.loop import run_loop

    source_type = config.get("source", {}).get("type", "list")
    topics_list = None

    if source_type == "list":
        if not hasattr(eval_mod, "TOPICS"):
            print("ERROR: source.type=list but evaluate.py has no TOPICS list")
            sys.exit(1)
        topics_list = eval_mod.TOPICS

    # Diagrams: hook up per-cycle run_dir for image output
    generate_fn = gen_mod.generate
    if hasattr(gen_mod, "set_run_dir"):
        # Wrap generate_fn to update run_dir each time the loop changes runs
        # We use a closure that reads state from core/loop via a side channel
        # Simpler: inject a wrapper that sets the run_dir based on data_dir
        original_generate = generate_fn

        _data_dir = exp_dir / "data"
        _state_path = _data_dir / "state.json"

        def generate_with_run_dir(prompt, topic):
            import json
            try:
                s = json.loads(_state_path.read_text()) if _state_path.exists() else {}
                run_num = s.get("run_number", 0) + 1  # +1 because it hasn't incremented yet
            except Exception:
                run_num = 1
            run_dir = _data_dir / "diagrams" / f"run_{run_num:03d}"
            gen_mod.set_run_dir(run_dir)
            return original_generate(prompt, topic)

        generate_fn = generate_with_run_dir

    run_loop(
        experiment_dir=exp_dir,
        config=config,
        generate_fn=generate_fn,
        evaluate_fn=eval_mod.evaluate,
        topics_list=topics_list,
        once=args.once,
        max_cycles=args.cycles,
    )


if __name__ == "__main__":
    main()
