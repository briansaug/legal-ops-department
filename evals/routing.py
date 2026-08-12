"""The escalation matrix, as code.

This is the executable form of playbook/escalation-matrix.md. Routing is a
deterministic function of the judgment signals — not a model decision.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp" / "contract_lake"))

from schema import HIGH_STAKES, ClauseType  # noqa: E402

SPAN_SIMILARITY_FLOOR = 0.95


def escalate_field(
    clause_type: ClauseType,
    present: bool,
    confidence: str,
    span_similarity: float,
    playbook_status: str,
    jurisdiction_ok: bool | None = None,
) -> list[str]:
    """Return the escalation reasons that fire for one field judgment.
    Empty list = no escalation. Mirrors the five matrix rules."""
    reasons = []
    if clause_type in HIGH_STAKES and present:
        reasons.append(f"rule 1: high-stakes clause {clause_type.value} present — always attorney review")
    if confidence != "high":
        reasons.append(f"rule 2: self-reported confidence '{confidence}' != high")
    if present and span_similarity < SPAN_SIMILARITY_FLOOR:
        reasons.append(f"rule 3: span verification failed (similarity={span_similarity:.4f} < {SPAN_SIMILARITY_FLOOR})")
    if present and playbook_status == "non_standard":
        reasons.append("rule 4: deviates from playbook standard")
    if clause_type == ClauseType.GOVERNING_LAW and jurisdiction_ok is False:
        reasons.append("rule 5: governing law outside allowlist or not found")
    return reasons


def decide(field_escalations: dict[str, list[str]]) -> str:
    """Memo-level decision: any field escalated -> attorney_review.
    reject_counterparty_paper never comes from this function."""
    return "attorney_review" if any(field_escalations.values()) else "self_serve"
