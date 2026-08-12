# legal-ops-department

> **PRE-REGISTRATION DRAFT.** This README is committed before any model eval
> has run. Sections marked `[RESULTS PENDING]` are filled in from measured
> numbers after the runs; §5's "either outcome is a win" paragraph and §6
> Limitations are written now, so they cannot be read as post-hoc.

## 5. Evaluation (pre-registered framing)

**Either outcome is a win.** Config C routes the cheap model (Haiku) to the
six standard fields and the expensive model (Opus) to the four high-stakes
fields, with a regex on governing law. If Haiku matches Opus on the standard
flags, that is the routing rule validated: the department ships the cheap
model where the evals show it is reliable. If Haiku falls short, the
escalation rule caught the gap before a human saw a wrong answer — and the
eval is what found it. The failure mode this design cannot excuse is a wrong
answer that self-served; that count is reported per config in the results
table. Prompts are frozen before the first run and will not be tuned against
the gold set.

`[RESULTS PENDING]`

## 6. Limitations — when I would NOT use this (drafted before the build)

- **CUAD's label definitions are not this department's.** The gold labels
  follow CUAD's annotation guidelines. Where they diverge from everyday usage
  (exclusivity is the documented case — see `data/README.md`), the playbook
  adopts CUAD's definition and says so, because silently relabeling gold data
  is worse than an unfamiliar definition.
- **120 judgments is small.** Rare clause types rest on a handful of
  examples; per-field numbers on the four high-stakes fields are directional,
  not precise.
- **The time baseline is self-timed, n=3, by a non-lawyer.** It is an
  order-of-magnitude anchor, not a benchmark.
- **CUAD contracts are public-company SEC filings** — better drafted than the
  mid-market vendor NDAs real legal ops sees. Real-world recall is likely
  lower than measured here.
- **Would not use for:** final decisions on high-stakes clauses (the memo is
  a recommendation to an attorney by design), non-US law, adversarial
  counterparties, or as a system of record.
- **Governing law ships as a regex** if the eval shows the model adds cost
  without accuracy there — the comparison table decides it, and either way
  the field is deterministic enough that a model is the wrong tool.
- **The JSONL intake log is not a compliance-grade record.** It is an
  append-only file, not an immutable audit system.
