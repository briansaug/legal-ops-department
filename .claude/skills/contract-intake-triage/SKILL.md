---
name: contract-intake-triage
description: Run the ten-field intake memo on a third-party-paper contract and produce a routing recommendation. Use when a contract needs intake review, triage, or a "can the business sign this?" first pass. This is the department's main workflow and the one the evals exercise.
---

# Contract intake triage

Input: a `contract_id` from the lake. Output: a ten-field memo recorded via
`record_intake_memo`, routed by the escalation matrix.

## Procedure

1. `search_contracts` — confirm the contract exists, note `est_tokens`.
   Never read the whole document; retrieval comes first.
2. For each of the ten fields, in this order (high-stakes first —
   uncapped_liability, non_compete, exclusivity, most_favored_nation, then
   anti_assignment, change_of_control, termination_for_convenience,
   cap_on_liability, renewal_term — governing_law last, it isn't yours):
   a. `find_clause(contract_id, field)` — read the candidate windows.
   b. `get_playbook_standard(field)` — read the department position.
   c. Judge: present or absent. If present, pick the single best verbatim
      quote from a window and grade it against the playbook standard
      (`standard` / `non_standard`). Report your confidence honestly —
      calibration is measured.
   d. `verify_span(contract_id, quote)` for every quote. If it fails,
      re-quote from the window text exactly; if it still fails, the field
      escalates (that is matrix rule 3, and it is not overridable).
3. Governing law: do **not** judge it. `extract_governing_law` + the
   allowlist decide; your only job is recording what the regex found.
4. Apply the escalation matrix (`escalation-router` skill) — the decision
   is computed, not chosen.
5. Draft the memo with `intake-memo-writer` formatting.
6. `record_intake_memo`. A review without a log entry didn't happen.

## Non-negotiables (repeated from department CLAUDE.md because they bind here)

- No "present" without a verified verbatim span.
- High-stakes present ⇒ `attorney_review`; the memo recommends, an
  attorney decides.
- A `find_clause` result with no windows is evidence of absence, not
  proof. For the four high-stakes fields, confirm with one paged
  `get_contract` pass before recording "absent" with high confidence.
- The playbook wins over your judgment. Disagreement goes in memo notes.
