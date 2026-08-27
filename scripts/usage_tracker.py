#!/usr/bin/env python3
"""usage_tracker.py — tallies Anthropic Messages API token usage and cost.

Feed it the `usage` object off any `client.messages.create(...)` response
(or a `SimpleNamespace` with the same attribute names, for tests) plus a
route label and the model string that was actually called. It accumulates
totals and per-route cost so a caller can answer "what did today's fan-out
across providers cost, broken down by route".

Kept deliberately separate from wkb.py's `dispatch` command: dispatch
providers are shell commands by design (no real model credentials exist
in this environment — see the note at the top of `dispatch` in wkb.py),
so nothing here is wired into that path. This is a standalone utility for
a caller that does hold real Anthropic credentials and wants correctly
priced, per-route usage accounting.

Two bugs in the snippet this was built from, fixed here:
  - the cost formula charged $15/MTok output while the comment claimed
    $10/MTok — output pricing now comes from the same table as input,
    keyed by the model actually passed in, not hardcoded to one model.
  - cache_read/cache_creation tokens were tallied but never billed, even
    though they carry their own (much cheaper / slightly pricier) rate.

Pricing source: claude.com/pricing rates as of 2026-08 (Sonnet 5 is
$2/$10 per MTok — the current listed rate, not a discounted intro rate
as an earlier draft of this file assumed). If that rate changes after
2026-08-31, update this table then; don't pre-guess a future price now.
"""

from dataclasses import dataclass, field as dataclass_field
from collections import defaultdict

# USD per 1,000,000 tokens: (input, output).
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.00, 50.00),
    "claude-mythos-5": (10.00, 50.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Cache tokens are billed off the same model's input rate, scaled.
CACHE_WRITE_MULTIPLIER = 1.25  # cache_creation_input_tokens
CACHE_READ_MULTIPLIER = 0.1  # cache_read_input_tokens


class UsageTrackerError(Exception):
    pass


@dataclass
class UsageTracker:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    request_count: int = 0
    costs_by_route: dict = dataclass_field(default_factory=lambda: defaultdict(float))

    def record(self, usage, route: str, model: str) -> float:
        """Tally one response's usage against `route`/`model`, return its cost."""
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0

        cost = self._calculate_cost(
            input_tokens, output_tokens, cache_read, cache_creation, model
        )

        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_read_tokens += cache_read
        self.cache_creation_tokens += cache_creation
        self.request_count += 1
        self.costs_by_route[route] += cost
        return cost

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cache_creation: int,
        model: str,
    ) -> float:
        if model not in MODEL_PRICING:
            raise UsageTrackerError(
                f"no pricing for model '{model}' — add it to MODEL_PRICING "
                "before tracking usage against it"
            )
        input_rate, output_rate = MODEL_PRICING[model]
        cost = input_tokens * input_rate / 1_000_000
        cost += output_tokens * output_rate / 1_000_000
        cost += cache_creation * (input_rate * CACHE_WRITE_MULTIPLIER) / 1_000_000
        cost += cache_read * (input_rate * CACHE_READ_MULTIPLIER) / 1_000_000
        return cost

    @property
    def total_cost(self) -> float:
        return sum(self.costs_by_route.values())
