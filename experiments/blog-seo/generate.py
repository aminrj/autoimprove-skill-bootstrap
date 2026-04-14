"""
Blog SEO generation — works with Claude or Ollama to suggest SEO improvements for a Chirpy post.

generate(prompt, topic) → dict | None
  prompt: the optimization prompt being improved by the loop
  topic:  path to a .md blog post file
  returns: structured dict with suggested SEO improvements, or None on failure

The generate step asks Claude/Ollama to analyze a post and produce:
- A suggested title (under 60 chars)
- A meta description (120-160 chars)
- H1 heading count recommendation
- Alt text suggestions for images
- Internal link suggestions

The optimization prompt tells Claude/Ollama HOW to write good SEO suggestions.
The loop improves that prompt over cycles.
"""

import json
import os
import re
from pathlib import Path

# Cache for clients
_client_cache = {}


def _get_client(provider: str, model: str, endpoint: str = None):
    """Get or create an LLM client for the specified provider."""
    global _client_cache

    # Create a cache key
    cache_key = f"{provider}:{model}:{endpoint}"

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        _client_cache[cache_key] = client
        return client

    elif provider == "ollama":
        # For Ollama, we use the OpenAI client to interface with it
        from openai import OpenAI

        client = OpenAI(
            base_url=endpoint or "http://localhost:11434",
            api_key="ollama",  # Ollama doesn't require an API key
        )
        _client_cache[cache_key] = client
        return client

    else:
        raise ValueError(f"Unsupported provider: {provider}")


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
    # Load config to determine provider settings
    experiment_dir = Path(__file__).parent
    config_file = experiment_dir / "config.yaml"

    if not config_file.exists():
        # Fallback to hardcoded defaults for backward compatibility
        provider = "ollama"
        model = "qwen3-coder:30b"
        endpoint = "http://localhost:11434"
    else:
        import yaml

        config = yaml.safe_load(config_file.read_text())
        generator_config = config.get("generator", {})
        provider = generator_config.get("provider", "ollama")
        model = generator_config.get("model", "qwen3-coder:30b")
        endpoint = generator_config.get("endpoint", "http://localhost:11434")

    post_content = _read_post(topic)

    user_message = f"""{prompt}

---
POST FILE: {Path(topic).name}

{post_content}

---
{_OUTPUT_SCHEMA}"""

    try:
        client = _get_client(provider, model, endpoint)

        # Determine model name to use for the call
        model_name = model

        # Call the LLM
        if provider == "anthropic":
            response = client.messages.create(
                model=model_name,
                max_tokens=512,
                messages=[{"role": "user", "content": user_message}],
            )
            text = response.content[0].text.strip()
        else:  # ollama
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if "`" in text:
            text = re.sub(r"```[a-z]*\n?", "", text).replace("`", "").strip()

        # Try to parse the JSON response
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e} | raw: {text[:120]}")
        return None
    except Exception as e:
        print(f"    GEN ERROR ({Path(topic).name}): {e}")
        return None
