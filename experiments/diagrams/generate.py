"""
Diagram generation via Gemini image generation.

generate(prompt, topic) → Path | None
  prompt: the optimization prompt (whiteboard style instructions)
  topic:  a string describing the technical process to diagram
  returns: Path to the generated PNG, or None on failure
"""

import os
from pathlib import Path

_gemini_client = None
_run_dir = None  # set by run.py before each cycle via set_run_dir()


def set_run_dir(path: Path):
    """Called by the runner before each cycle to set the output directory."""
    global _run_dir
    _run_dir = path
    _run_dir.mkdir(parents=True, exist_ok=True)


def _get_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        key = os.getenv("NANO_BANANA_API_KEY")
        if not key:
            raise EnvironmentError("NANO_BANANA_API_KEY not set")
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


def generate(prompt: str, topic: str) -> Path | None:
    """Generate one diagram image for the given topic using the current prompt."""
    from google.genai import types

    client = _get_client()
    full_prompt = f"{prompt}\n\nDiagram to create: {topic}"

    # Derive output path from topic index (topic may be "CI/CD pipeline: ...")
    # We use a hash of the topic for a stable filename within the run dir
    import hashlib
    slug = hashlib.md5(topic.encode()).hexdigest()[:8]
    out_path = (_run_dir or Path("/tmp")) / f"diagram_{slug}.png"

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image"),
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(part.inline_data.data)
                return out_path
        return None
    except Exception as e:
        print(f"    GEN ERROR ({topic[:40]}): {e}")
        return None
