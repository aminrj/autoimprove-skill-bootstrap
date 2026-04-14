"""
Diagram evaluation via Claude vision.

evaluate(artifact) → {criterion_id: bool, failures: list[str]}
  artifact: Path to a PNG image (returned by generate.py)
  returns:  dict with one bool per criterion + optional failures list

TOPICS is also defined here — used by run.py as the sampling pool.
"""

import base64
import json
import os
from pathlib import Path

_anthropic_client = None

# 30 diverse technical topics that produce varied diagram structures
TOPICS = [
    "CI/CD pipeline: code commit flows to build, then test, then deploy, then monitor",
    "Machine learning workflow: data collection to preprocessing to training to evaluation to deployment",
    "User authentication: login form to validation to JWT token to access granted",
    "Microservices: API gateway connecting to user service, payment service, and notification service",
    "ETL pipeline: extract from databases, transform with business rules, load into warehouse",
    "Email marketing funnel: capture lead to nurture sequence to segment to convert to retain",
    "Content creation pipeline: research to outline to draft to edit to publish",
    "Customer support flow: ticket submitted to triage to assign to resolve to follow up",
    "API request lifecycle: client request to load balancer to app server to database to response",
    "Git workflow: feature branch to pull request to code review to merge to deploy",
    "OAuth flow: user to app to authorization server to resource server",
    "Notification system: event trigger to queue to router splitting to email, push, and SMS channels",
    "Search engine pipeline: crawl pages to index to rank to serve results",
    "Video processing: upload to transcode to generate thumbnail to CDN to stream",
    "A/B testing: hypothesis to experiment design to traffic split to measure to analyze",
    "Payment processing: cart to checkout to payment gateway to bank to confirmation",
    "Recommendation engine: user activity to features to model to ranked results to display",
    "Monitoring stack: metrics collection to aggregation to alerting to dashboard",
    "Caching strategy: request to cache check then hit path or miss path to origin server",
    "Log aggregation: app logs to collector to parser to storage to visualization",
    "Message queue: producer to exchange to routing to queues to consumers",
    "Blue-green deploy: load balancer switching between blue and green environments",
    "SSO architecture: identity provider connecting to multiple service providers via tokens",
    "Data lake: raw ingestion to cataloging to processing to curated zone to analytics",
    "Serverless flow: API request to function trigger to compute to storage to response",
    "Container orchestration: registry to scheduler to node to pod to service mesh",
    "GraphQL architecture: client query to resolver to data sources to merged response",
    "Event sourcing: command to event store to projections to read models to query",
    "Feature flag system: config to evaluation engine to user targeting to rollout",
    "Rate limiting: request to counter check to allow or reject to update counter",
]

_EVAL_PROMPT = """You are evaluating a diagram image against 4 strict criteria. Examine the image carefully.

Criteria:
1. LEGIBLE_AND_GRAMMATICAL: ALL text in the diagram is clearly readable — no garbled, overlapping, blurry, or cut-off text. All words are real English words spelled correctly. Sentences/phrases are grammatically correct.

2. PASTEL_COLORS: The diagram uses ONLY soft pastel colors for fills (light purple, light blue, light green, light pink, light yellow, light teal, etc). No bright, saturated, neon, or dark-colored fills. White background counts as passing.

3. LINEAR_LAYOUT: The diagram flows in ONE clear linear direction — either strictly left-to-right OR strictly top-to-bottom. Not circular, radial, scattered, hub-and-spoke, or multi-directional.

4. NO_NUMBERS: The diagram contains ZERO numbers, step numbers, ordinals (1st, 2nd, 3rd), sequence indicators (Step 1, Phase 2), or any numerical ordering. Only text labels allowed.

Rate each criterion as PASS (true) or FAIL (false). Be strict.

Respond in this exact JSON format:
{"legible_and_grammatical": true, "pastel_colors": true, "linear_layout": true, "no_numbers": true, "failures": []}

If any criterion fails, set it to false and add a brief description to the failures array."""


def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def evaluate(artifact) -> dict:
    """
    Evaluate a diagram image against 4 binary criteria.

    Eval isolation: the evaluator sees ONLY the image and the criteria —
    never the prompt that generated it. This prevents charitable grading.
    """
    if artifact is None:
        return {"legible_and_grammatical": False, "pastel_colors": False,
                "linear_layout": False, "no_numbers": False, "failures": ["no_artifact"]}

    image_path = Path(artifact)
    if not image_path.exists():
        return {"legible_and_grammatical": False, "pastel_colors": False,
                "linear_layout": False, "no_numbers": False, "failures": ["file_not_found"]}

    client = _get_client()
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    eval_model = os.getenv("EVAL_MODEL", "claude-sonnet-4-6")

    try:
        response = client.messages.create(
            model=eval_model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": _EVAL_PROMPT},
                ],
            }],
        )
        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        print(f"    EVAL ERROR: {e}")
        return {"legible_and_grammatical": False, "pastel_colors": False,
                "linear_layout": False, "no_numbers": False, "failures": [f"eval_exception: {e}"]}
