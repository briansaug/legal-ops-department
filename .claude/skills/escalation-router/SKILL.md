---
name: escalation-router
description: Compute the routing decision for a completed set of field judgments by applying the escalation matrix. Deterministic — same judgments in, same decision out, no discretion. Use as step 4 of contract-intake-triage or to explain why a past memo routed the way it did.
---

# Escalation router

Routing is a function, not a conversation. The matrix lives in
`playbook/escalation-matrix.md`; the executable form is
`evals/routing.py::decide`. This skill applies it and shows its work.

## The function

A field escalates when ANY of:

1. `clause_type` is high-stakes (uncapped_liability, non_compete,
   exclusivity, most_favored_nation) and the clause is present
2. self-reported confidence ≠ `high`
3. present, and the quote's `verify_span` similarity < 0.95
4. present, and playbook status is `non_standard`
5. (governing_law only) jurisdiction missing or not on the allowlist

Memo decision: any field escalated → `attorney_review`; none → `self_serve`.
`reject_counterparty_paper` never comes from this function.

## Output

For each escalated field, one line: the field, the rule number that fired,
and the signal value that fired it (e.g. `similarity=0.91 < 0.95`). These
lines go in the memo verbatim as `Escalation reasons`.

## Rules

- Never suppress a trigger, never add one. If the result feels wrong,
  that's feedback on the matrix — file it with the contracts attorney.
- When asked "why did this escalate?", re-derive from the logged judgment
  values; do not speculate.
