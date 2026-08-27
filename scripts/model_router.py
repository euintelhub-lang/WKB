#!/usr/bin/env python3
"""model_router.py — picks the cheapest model tier likely to handle a task.

Companion to usage_tracker.py: `choose_model` decides which model to call;
`UsageTracker.record` then prices whatever model actually ran. Keeping the
router's output tied to `MODEL_PRICING` means a route can never point at a
model this tracker doesn't know how to price.

Two bugs fixed from the snippet this was built from:
  - `claude-haiku-4-5-20251001` is not a real model id. Anthropic model
    strings are undated aliases (`claude-haiku-4-5`) — appending a date
    suffix like a training-data-era snapshot name gets a 404 from the API,
    not a specific dated model.
  - it mixed model generations (Haiku *4.5* alongside Sonnet/Opus *4.6*).
    Routes now stay within the current generation (Haiku 4.5, Sonnet 5,
    Opus 5) for a consistent quality-per-tier ladder.
"""

from usage_tracker import MODEL_PRICING

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-5"
OPUS = "claude-opus-5"

# Task types simple/structured enough to trust to the cheapest tier
# regardless of the complexity score.
CHEAP_TASK_TYPES = frozenset({"classify", "extract", "format"})

for _model in (HAIKU, SONNET, OPUS):
    assert _model in MODEL_PRICING, f"{_model} has no entry in usage_tracker.MODEL_PRICING"


def choose_model(task_type: str, complexity_score: float) -> str:
    """Route to the cheapest model tier likely to handle this task.

    `task_type` in CHEAP_TASK_TYPES always routes to Haiku, independent of
    `complexity_score` — a classification/extraction/formatting task is
    assumed cheap by its structure, not by a caller-supplied score.
    """
    if task_type in CHEAP_TASK_TYPES or complexity_score < 0.3:
        return HAIKU
    if complexity_score < 0.7:
        return SONNET
    return OPUS
