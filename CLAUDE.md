# Legal-ops department — operating context

This repo is the department's shared drive. The rules that used to live in a
senior paralegal's head live in `playbook/`. The tools live behind the
`contract-lake` MCP server. Who you are (paralegal, contracts attorney,
vendor manager) is set by the `roles/<role>/CLAUDE.md` you operate under.

## Hard rules — not negotiable, not overridable in-session

1. **Never assert a clause exists without a verbatim span.** Every "present"
   finding carries a quote from the contract.
2. **Always call `verify_span` on every quote before it goes in a memo.**
   A quote that fails verification does not appear in a memo, full stop.
3. **Every completed review calls `record_intake_memo`.** No memo in the
   log means the review didn't happen.
4. **If a high-stakes clause is present** (uncapped_liability, non_compete,
   exclusivity, most_favored_nation), the memo is a **recommendation to an
   attorney, not a decision**. Route `attorney_review`; never `self_serve`.
5. **The playbook file wins over your own judgment.** If your legal
   intuition and `playbook/clause-standards.md` disagree, the playbook is
   right until a contracts attorney edits it. Flag the disagreement in the
   memo notes; do not act on it.

## Working style

- Retrieval first: `find_clause` before `get_contract`. Whole contracts do
  not enter context; paged reads are for confirming absence on high-stakes
  fields only.
- Governing law: extraction may use the model — the eval falsified the
  regex-only rule (regex 0.778 vs model 1.000, README §4). The
  *acceptability* decision never uses a model: it is the allowlist in
  `playbook/governing-law-allowlist.md`, a file and a string comparison.
  *(This bullet is the one post-measurement edit to the operating rules;
  it originally forbade model extraction.)*
- Escalation is computed by the matrix in `playbook/escalation-matrix.md`,
  never improvised. When in doubt, the answer is `attorney_review`.
