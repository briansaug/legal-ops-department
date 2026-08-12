# Escalation matrix

Routing is a deterministic function, not a model decision. The code that
applies this matrix is `evals/routing.py` (the same function the
escalation-router skill describes). A memo escalates to
`attorney_review` when **any** of these fire:

| # | Trigger | Source of signal |
|---|---|---|
| 1 | A high-stakes clause is present: uncapped_liability, non_compete, exclusivity, most_favored_nation | model judgment, but the *routing* of a positive is fixed |
| 2 | Self-reported confidence is not `high` | model self-report (weakest signal — its calibration is measured and published in the eval results) |
| 3 | A clause is flagged present but its quote fails span verification (similarity < 0.95) | deterministic — `verify_span` |
| 4 | A clause is present and deviates from the playbook standard (`non_standard`) | model judgment against the playbook text |
| 5 | Governing law is outside the allowlist, or not found | deterministic — regex + `governing-law-allowlist.md` |

Rules 3 and 5 are fully deterministic. Rule 1's trigger condition depends on
the model's presence call, but a *missed* high-stakes clause is exactly what
the eval measures (recall on the four high-stakes fields), and a *found* one
routes to a human with no discretion.

## Decisions

- **No trigger fires** → `self_serve` — business owner proceeds on the
  counterparty's paper with the memo attached.
- **Any trigger fires** → `attorney_review` — the memo is a
  *recommendation to an attorney, not a decision*.
- `reject_counterparty_paper` is an attorney-only outcome. Intake never
  auto-rejects.

## What escalation means for accuracy accounting

A wrong field-level answer that escalated is a **caught** error — an
attorney sees the contract with the memo as a starting point. A wrong
answer that self-served is a **production** error. The eval results table
reports both, separately.
