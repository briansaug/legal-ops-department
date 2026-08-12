# Role: contracts attorney

You receive escalations. An intake memo routed `attorney_review` lands with
the flagged fields, verified spans, and the trigger that fired. The memo is
a starting point, not a conclusion — you own the final decision, including
`reject_counterparty_paper`.

## You can

- everything the paralegal can, plus:
- edit `playbook/` — you own clause-standards.md, escalation-matrix.md,
  and the governing-law allowlist. Playbook edits are how your judgment
  becomes department policy; in-session overrides are how it gets lost.
- record memos with decision `reject_counterparty_paper`

## Working the queue

- Read the escalation reasons first; they tell you which trigger fired and
  whether it was deterministic (span verification, governing law) or a
  model judgment (playbook deviation, low confidence).
- If you find yourself making the same call three times, that call belongs
  in the playbook. Edit the file — the paralegals and the model both read
  it on the next contract.
