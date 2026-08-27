#!/usr/bin/env python3
"""Tests for model_router.py. Run: python3 scripts/test_model_router.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model_router import choose_model, HAIKU, SONNET, OPUS  # noqa: E402
from usage_tracker import MODEL_PRICING  # noqa: E402


def pass_(name: str) -> None:
    print(f"PASS: {name}")


def fail(name: str, msg: str = "") -> None:
    print(f"FAIL: {name} {msg}", file=sys.stderr)
    sys.exit(1)


# 1. cheap task types always route to Haiku, even at high complexity
for task_type in ("classify", "extract", "format"):
    model = choose_model(task_type, complexity_score=0.95)
    if model != HAIKU:
        fail(f"cheap task type '{task_type}' at high complexity", f"got {model}")
pass_("cheap task types route to Haiku regardless of complexity")

# 2. low complexity on an unlisted task type still routes to Haiku
model = choose_model("summarize", complexity_score=0.1)
if model != HAIKU:
    fail("low complexity unlisted task type", f"got {model}")
pass_("low complexity routes to Haiku")

# 3. mid complexity routes to Sonnet
model = choose_model("summarize", complexity_score=0.5)
if model != SONNET:
    fail("mid complexity", f"got {model}")
pass_("mid complexity routes to Sonnet")

# 4. high complexity routes to Opus
model = choose_model("summarize", complexity_score=0.9)
if model != OPUS:
    fail("high complexity", f"got {model}")
pass_("high complexity routes to Opus")

# 5. boundaries: 0.3 is the first Sonnet value, 0.7 is the first Opus value
if choose_model("summarize", 0.3) != SONNET:
    fail("boundary 0.3 should route to Sonnet")
if choose_model("summarize", 0.7) != OPUS:
    fail("boundary 0.7 should route to Opus")
pass_("complexity boundaries land on the documented side")

# 6. every returned model id is priced — no unknown/unpriced ids
for task_type in ("classify", "extract", "format", "summarize", "reason"):
    for score in (0.0, 0.1, 0.29, 0.3, 0.5, 0.69, 0.7, 0.99, 1.0):
        model = choose_model(task_type, score)
        if model not in MODEL_PRICING:
            fail("unpriced model returned", f"{task_type}/{score} -> {model}")
pass_("every route returns a model present in MODEL_PRICING")

# 7. no route ever returns a dated snapshot id (the original bug)
for task_type in ("classify", "extract", "format", "summarize", "reason"):
    for score in (0.0, 0.5, 1.0):
        model = choose_model(task_type, score)
        if len(model.rsplit("-", 1)[-1]) == 8 and model.rsplit("-", 1)[-1].isdigit():
            fail("route returned a dated snapshot id", model)
pass_("no route returns a dated snapshot id")

print("ALL MODEL ROUTER TESTS PASSED")
