---
name: intake-memo-writer
description: Format a completed set of field judgments into the standard intake memo. Formatting only — this skill makes no legal judgments, changes no findings, and computes no routing. Use after triage judgments exist and before record_intake_memo.
---

# Intake memo writer

Deliberately dumb. Judgments come in, a memo comes out, nothing is decided
here. If a judgment is missing or malformed, stop and say which — do not
fill gaps.

## Memo format

```
INTAKE MEMO — <contract_id>
Reviewed by: <role> · <date>
Decision: <self_serve | attorney_review>   (computed by escalation-router)

| Field | Present | Quote (verified) | Playbook | Confidence | Escalates |
|-------|---------|------------------|----------|------------|-----------|
| ...ten rows, always all ten, in playbook order... |

Escalation reasons: <verbatim list from escalation-router, or "none">
Basis: <one sentence per escalated field, citing the playbook section>
```

## Rules

- All ten fields appear, always — an absent clause is a row that says
  "absent", not a missing row.
- Quotes appear exactly as verified by `verify_span`; no ellipses inside a
  quote, no cleaned-up punctuation.
- The decision line is whatever escalation-router computed. If someone
  wants a different decision, that conversation happens with the attorney,
  not with the formatter.
