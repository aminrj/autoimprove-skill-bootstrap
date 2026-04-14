"""
Evaluation function for your experiment.

evaluate(artifact) → {criterion_id: bool, failures: list[str]}
  artifact: what generate() returned
  returns:  a dict with one bool per criterion (matching config.yaml criterion IDs)
            plus an optional "failures" list for mutation hints

IMPORTANT — Eval isolation:
  This function should NOT have access to the optimization prompt.
  It judges the artifact purely on its own merits.
  If the evaluator knows the intent, it grades charitably — corrupting the signal.

Two evaluation approaches:
  1. Rule-based: parse the artifact and check properties directly (fast, cheap, deterministic)
  2. LLM-judge:  ask Claude to evaluate — use a separate API call with no prompt context

Rule-based is always preferred when possible. Use LLM-judge only for qualities
that require understanding (e.g., "is this alt text descriptive?").
"""


def evaluate(artifact) -> dict:
    """
    Score one artifact against the criteria defined in config.yaml.

    Args:
        artifact: the return value of generate() — image path, dict, string, etc.

    Returns:
        dict with:
          - one key per criterion_id (bool: True = pass, False = fail)
          - "failures": list of strings describing what failed (used for mutation hints)

    Example return:
        {
            "criterion_one": True,
            "criterion_two": False,
            "criterion_three": True,
            "failures": ["criterion_two failed because X"],
        }

    TODO: implement this function
    """
    failures = []

    if artifact is None:
        return {
            "criterion_one": False,
            "criterion_two": False,
            "criterion_three": False,
            "failures": ["no artifact produced"],
        }

    # TODO: check criterion_one
    criterion_one = False  # replace with actual check
    if not criterion_one:
        failures.append("TODO: describe why criterion_one failed")

    # TODO: check criterion_two
    criterion_two = False  # replace with actual check
    if not criterion_two:
        failures.append("TODO: describe why criterion_two failed")

    # TODO: check criterion_three
    criterion_three = False  # replace with actual check
    if not criterion_three:
        failures.append("TODO: describe why criterion_three failed")

    return {
        "criterion_one": criterion_one,
        "criterion_two": criterion_two,
        "criterion_three": criterion_three,
        "failures": failures,
    }
