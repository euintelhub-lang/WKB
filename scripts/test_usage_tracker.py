#!/usr/bin/env python3
"""Tests for usage_tracker.py. Run: python3 scripts/test_usage_tracker.py"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
from usage_tracker import UsageTracker, UsageTrackerError, MODEL_PRICING  # noqa: E402


def pass_(name: str) -> None:
    print(f"PASS: {name}")


def fail(name: str, msg: str = "") -> None:
    print(f"FAIL: {name} {msg}", file=sys.stderr)
    sys.exit(1)


# 1. basic input/output cost, no cache tokens
tracker = UsageTracker()
usage = SimpleNamespace(input_tokens=1000, output_tokens=500)
cost = tracker.record(usage, route="chat", model="claude-sonnet-5")
input_rate, output_rate = MODEL_PRICING["claude-sonnet-5"]
expected = 1000 * input_rate / 1_000_000 + 500 * output_rate / 1_000_000
if abs(cost - expected) > 1e-9:
    fail("basic cost calc", f"got {cost}, expected {expected}")
if tracker.input_tokens != 1000 or tracker.output_tokens != 500:
    fail("token accumulation")
if tracker.request_count != 1:
    fail("request count")
pass_("basic input/output cost + accumulation")

# 2. cache tokens are tracked AND billed (the fixed bug)
usage_cache = SimpleNamespace(
    input_tokens=100,
    output_tokens=50,
    cache_read_input_tokens=2000,
    cache_creation_input_tokens=300,
)
cost_cache = tracker.record(usage_cache, route="chat", model="claude-sonnet-5")
expected_cache = (
    100 * input_rate / 1_000_000
    + 50 * output_rate / 1_000_000
    + 300 * (input_rate * 1.25) / 1_000_000
    + 2000 * (input_rate * 0.1) / 1_000_000
)
if abs(cost_cache - expected_cache) > 1e-9:
    fail("cache cost calc", f"got {cost_cache}, expected {expected_cache}")
if tracker.cache_read_tokens != 2000 or tracker.cache_creation_tokens != 300:
    fail("cache token accumulation")
pass_("cache read/creation tokens billed")

# 3. per-route cost separation
usage_other = SimpleNamespace(input_tokens=10, output_tokens=10)
tracker.record(usage_other, route="summarize", model="claude-sonnet-5")
if set(tracker.costs_by_route) != {"chat", "summarize"}:
    fail("route separation", str(dict(tracker.costs_by_route)))
pass_("per-route cost separation")

# 4. total_cost aggregates every route
if abs(tracker.total_cost - sum(tracker.costs_by_route.values())) > 1e-12:
    fail("total_cost aggregation")
pass_("total_cost aggregation")

# 5. an unpriced model raises rather than silently mispricing
try:
    tracker.record(usage, route="x", model="gpt-4")
    fail("unknown model should raise UsageTrackerError")
except UsageTrackerError:
    pass_("unpriced model raises UsageTrackerError")

# 6. usage objects without cache attributes default to zero, don't crash
usage_no_cache = SimpleNamespace(input_tokens=1, output_tokens=1)
before = tracker.cache_read_tokens
tracker.record(usage_no_cache, route="chat", model="claude-opus-5")
if tracker.cache_read_tokens != before:
    fail("missing cache attributes should default to zero")
pass_("usage without cache attributes defaults to zero")

# 7. different models in the same tracker are priced independently
solo = UsageTracker()
u = SimpleNamespace(input_tokens=1_000_000, output_tokens=0)
opus_cost = solo.record(u, route="r", model="claude-opus-5")
haiku_cost = solo.record(u, route="r", model="claude-haiku-4-5")
if opus_cost <= haiku_cost:
    fail("opus should cost more per input token than haiku", f"{opus_cost} <= {haiku_cost}")
pass_("per-model pricing is independent")

print("ALL USAGE TRACKER TESTS PASSED")
