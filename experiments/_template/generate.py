"""
Generation function for your experiment.

generate(prompt, topic) → artifact | None
  prompt: the optimization prompt (this is what the loop improves)
  topic:  one item from your topic list or file path
  returns: the artifact to evaluate (image path, dict, string, etc.)

This file is the ONLY place that changes based on WHAT you're generating.
The loop engine (core/loop.py) calls this function — you don't need to touch it.

Examples:
  - Diagram experiment: calls Gemini image gen → returns Path to PNG
  - Blog SEO experiment: calls Claude with a post → returns dict of suggestions
  - Your experiment: call whatever model/API makes sense → return anything
    (as long as evaluate.py can handle it)
"""

import os


# ── If using a hardcoded topic list, define it here ──────────────────────────
# This is used when config.yaml has source.type = list
TOPICS = [
    "TODO: topic 1",
    "TODO: topic 2",
    "TODO: topic 3",
    # Add more topics here. 20-30 is a good range for variety.
]


def generate(prompt: str, topic: str):
    """
    Produce one artifact from the current prompt + topic.

    Args:
        prompt: the optimization prompt being improved by the loop
        topic:  a string from TOPICS, or a file path (for source.type=local_files)

    Returns:
        The artifact to be evaluated — can be any type, as long as evaluate()
        knows how to score it. Return None if generation fails.

    TODO: implement this function
    """
    # Example: call an LLM and return the text response
    # import anthropic
    # client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    # response = client.messages.create(
    #     model="claude-sonnet-4-6",
    #     max_tokens=512,
    #     messages=[{"role": "user", "content": f"{prompt}\n\nTopic: {topic}"}],
    # )
    # return response.content[0].text

    raise NotImplementedError("implement generate() in generate.py")
