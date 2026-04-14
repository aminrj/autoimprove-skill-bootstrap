"""
Blog SEO evaluation — checks 5 binary criteria on Claude's suggestions.

evaluate(artifact) → {criterion_id: bool, failures: list[str]}
  artifact: dict returned by generate.py
  returns:  dict with one bool per criterion + failures list

EVAL ISOLATION: This function never sees the optimization prompt.
It only sees the structured suggestion and judges it on its own merits.
This prevents Claude from grading its own outputs charitably.

Criteria:
  1. title_under_60       — rule-based (string length)
  2. description_120_160  — rule-based (string length)
  3. single_h1            — rule-based (h1_count == 1)
  4. images_have_alt      — rule-based (checks for generic/empty alt text)
  5. internal_links       — rule-based (counts links starting with /posts/)
"""

_GENERIC_ALT_TEXTS = {
    "", "image", "photo", "picture", "screenshot", "figure", "diagram",
    "img", "pic", "thumbnail", "banner", "header", "background",
}


def _is_descriptive_alt(alt: str) -> bool:
    """Return True if the alt text is descriptive (not empty or generic)."""
    if not alt or not alt.strip():
        return False
    normalized = alt.strip().lower().rstrip(".")
    return normalized not in _GENERIC_ALT_TEXTS and len(alt.strip()) > 10


def evaluate(artifact) -> dict:
    """
    Evaluate SEO suggestions against 5 binary criteria.

    Entirely rule-based — no LLM call needed. Fast, deterministic, cheap.
    """
    failures = []

    if artifact is None:
        return {
            "title_under_60": False,
            "description_120_160": False,
            "single_h1": False,
            "images_have_alt": False,
            "internal_links": False,
            "failures": ["no_artifact"],
        }

    # ── 1. Title under 60 chars ───────────────────────────────────
    title = artifact.get("title", "")
    title_ok = bool(title and title.strip()) and len(title.strip()) <= 60
    if not title_ok:
        if not title or not title.strip():
            failures.append("title is missing or empty")
        else:
            failures.append(f"title is {len(title.strip())} chars (limit: 60): '{title.strip()[:70]}'")

    # ── 2. Description 120-160 chars ─────────────────────────────
    desc = artifact.get("description", "")
    desc_len = len(desc.strip()) if desc else 0
    desc_ok = 120 <= desc_len <= 160
    if not desc_ok:
        if desc_len == 0:
            failures.append("description is missing or empty")
        elif desc_len < 120:
            failures.append(f"description too short: {desc_len} chars (need 120-160)")
        else:
            failures.append(f"description too long: {desc_len} chars (need 120-160)")

    # ── 3. Single H1 ──────────────────────────────────────────────
    h1_count = artifact.get("h1_count", None)
    if h1_count is None:
        h1_ok = False
        failures.append("h1_count not provided in suggestion")
    else:
        h1_ok = int(h1_count) == 1
        if not h1_ok:
            failures.append(f"h1_count should be 1, got {h1_count}")

    # ── 4. Images have descriptive alt text ───────────────────────
    alt_texts = artifact.get("alt_texts", [])
    if not alt_texts:
        # No images — treat as pass (not applicable)
        images_ok = True
    else:
        bad_alts = [a for a in alt_texts if not _is_descriptive_alt(a)]
        images_ok = len(bad_alts) == 0
        if not images_ok:
            for a in bad_alts[:3]:
                failures.append(f"non-descriptive alt text: '{a or '(empty)'}'")

    # ── 5. At least 2 internal links ─────────────────────────────
    links = artifact.get("internal_links", [])
    # Accept links that start with /posts/ or /categories/ or relative paths
    internal = [l for l in links if l and (l.startswith("/") or "aminrj.com" in l)]
    links_ok = len(internal) >= 2
    if not links_ok:
        failures.append(f"only {len(internal)} internal link(s) suggested (need ≥2)")

    return {
        "title_under_60": title_ok,
        "description_120_160": desc_ok,
        "single_h1": h1_ok,
        "images_have_alt": images_ok,
        "internal_links": links_ok,
        "failures": failures,
    }
