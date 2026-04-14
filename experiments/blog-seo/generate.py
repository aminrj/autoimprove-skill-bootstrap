"""
Blog SEO generation — Claude suggests SEO improvements for a Chirpy post.

generate(prompt, topic) → dict | None
  prompt: the optimization prompt being improved by the loop
  topic:  path to a .md blog post file
  returns: structured dict with suggested SEO improvements, or None on failure

The generate step asks Claude to analyze a post and produce:
- A suggested title (under 60 chars)
- A meta description (120-160 chars)
- H1 heading count recommendation
- Alt text suggestions for images
- Internal link suggestions

The optimization prompt tells Claude HOW to write good SEO suggestions.
The loop improves that prompt over cycles.
"""

import json
import os
import re
from pathlib import Path

_anthropic_client = None


def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def _read_post(post_path: str) -> str:
    """Read a blog post file, trimmed to avoid huge context usage."""
    content = Path(post_path).read_text(encoding="utf-8", errors="replace")
    # Trim very long posts — front matter + first 3000 chars of body is enough
    if len(content) > 4000:
        content = content[:4000] + "\n\n[... post truncated for analysis ...]"
    return content


_OUTPUT_SCHEMA = """Respond with ONLY a JSON object matching this schema — no markdown fences, no explanation:
{
  "title": "<suggested title, max 60 chars>",
  "description": "<meta description, 120-160 chars>",
  "h1_count": <integer: how many H1 headings the post body should have>,
  "alt_texts": ["<descriptive alt for image 1>", ...],
  "internal_links": ["/posts/slug-1", "/posts/slug-2"]
}

If the post has no images, use an empty array for alt_texts.
If you cannot suggest 2 internal links, use whatever you can find."""


def generate(prompt: str, topic: str) -> dict | None:
    """
    Use the optimization prompt to generate SEO suggestions for a blog post.

    The prompt is what the loop is trying to improve.
    This function applies that prompt to a real post and returns structured output.
    """
    post_content = _read_post(topic)
    model = os.getenv("GEN_MODEL", "claude-sonnet-4-6")

    user_message = f"""{prompt}

---
POST FILE: {Path(topic).name}

{post_content}

---
{_OUTPUT_SCHEMA}"""

    try:
        response = _get_client().messages.create(
            model=model,
            max_tokens=512,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if "```" in text:
            text = re.sub(r"```[a-z]*\n?", "", text).replace("```", "").strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e} | raw: {text[:120]}")
        return None
    except Exception as e:
        print(f"    GEN ERROR ({Path(topic).name}): {e}")
        return None
