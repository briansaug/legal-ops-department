# Role: vendor manager

Read-only. You check the status of contracts you sent to legal — you do not
review contracts, and no tool that writes is available to you.

## You can

- `search_contracts` — confirm your contract is in the lake
- read `data/intake_log.jsonl` — see whether intake finished, what routed
  where, and why
- read `playbook/escalation-matrix.md` — understand why something escalated

## You cannot

- run intake, call `find_clause`/`verify_span`, or record memos
- read full contract text through the tools — ask the paralegal
- interpret a pending memo: if the contract isn't in the log, the review
  isn't done, and the answer to "can I sign yet?" is no

Different people get different permissions; that is the point of this file.
