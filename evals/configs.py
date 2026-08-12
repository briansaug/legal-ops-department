"""Eval configurations and pricing.

Three configs, frozen before any eval ran:

  A  ceiling — claude-opus-5 on all ten fields, model defaults
  B  floor   — claude-haiku-4-5 on all ten fields, no thinking
  C  routed (the shipped design) — claude-haiku-4-5 on the five standard
     fields, claude-opus-5 on the four high-stakes fields, and a regex
     (no model at all) on governing_law

C's field->model map is a prior, decided before results existed: spend the
expensive model where a miss hurts most, none where the field is
deterministic. The A/B comparison tests that prior; the "either outcome is
a win" paragraph in the README was written before the runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp" / "contract_lake"))

from schema import HIGH_STAKES, ClauseType  # noqa: E402

OPUS = "claude-opus-5"
HAIKU = "claude-haiku-4-5"
REGEX = "regex"  # sentinel: deterministic path, no model call

# list prices, USD per million tokens (Anthropic API, 2026-08)
PRICES = {
    OPUS: {"in": 5.00, "out": 25.00},
    HAIKU: {"in": 1.00, "out": 5.00},
    REGEX: {"in": 0.0, "out": 0.0},
}


def model_for(config: str, clause_type: ClauseType) -> str:
    if config == "A":
        return OPUS
    if config == "B":
        return HAIKU
    if config == "C":
        if clause_type == ClauseType.GOVERNING_LAW:
            return REGEX
        return OPUS if clause_type in HIGH_STAKES else HAIKU
    raise ValueError(f"unknown config {config!r}")


CONFIGS = {
    "A": "claude-opus-5 everywhere (ceiling)",
    "B": "claude-haiku-4-5 everywhere (floor)",
    "C": "routed: haiku standard fields, opus high-stakes, regex governing law (shipped)",
}
