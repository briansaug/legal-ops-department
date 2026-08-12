# Data provenance

## Corpus: CUAD v1

Contract text and gold labels come from **CUAD v1** (Contract Understanding
Atticus Dataset), published by [The Atticus Project](https://www.atticusprojectai.org/cuad):
510 commercial contracts with 13,000+ clause annotations across 41 categories,
labeled by law students under attorney supervision.

- Download: `https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1` (~106 MB)
- License: **CC BY 4.0** — the dataset and annotations are free for commercial
  use with attribution. Confirmed on the Zenodo record, the Atticus Project
  site, and the HuggingFace dataset card.
- Attribution: Hendrycks, Burns, Chen & Ball, *"CUAD: An Expert-Annotated NLP
  Dataset for Legal Contract Review"*, NeurIPS 2021 Datasets and Benchmarks.

**Required caveat:** Atticus makes no representation about the license status
of the underlying contracts, which are public SEC EDGAR filings. CC BY 4.0
covers the dataset and annotations.

Contract text is therefore **fetched, not committed** — `data/contracts/` and
`data/cuad/` are gitignored. Run `./fetch_cuad.sh` to reproduce them.

## The frozen gold set

`gold/intake_gold.csv` holds **120 gold judgments**: 12 contracts × the 10
intake fields, extracted programmatically from CUAD's `master_clauses.csv`
(one row per contract, one column per category — no hand-labeling).

The selection rule lives in [`gold/build_gold_set.py`](gold/build_gold_set.py)
and was written down before any model ran, then frozen:

1. candidates = contracts with plain-text under 120 KB,
2. greedy deterministic pick of 12 maximizing present/absent balance per field
   (target ≥3 each side), ties broken by sorted filename,
3. the picks freeze into `gold/contract_manifest.json` — once it exists, the
   selection never re-runs.

The gold set was committed before the first model eval and not touched after.

## Verification performed before freezing

- **Span grounding:** 92 of 98 annotated gold spans appear verbatim
  (whitespace-normalized) in the staged contract text. The 6 misses are CUAD
  annotation artifacts, not label errors: spans spliced with a literal
  `<omitted>` marker, or page-break `Source:` watermarks interleaved in the
  text. Presence labels are unaffected.
- **Spot-check:** 10 of the 120 labels were read against the contract text.
  9 were unambiguous. One (`ashworthinc` / exclusivity, a logo-exclusivity
  commitment) is correct under CUAD's definition of exclusivity, which is
  broader than a layperson's — the playbook adopts CUAD's definition and
  says so in `playbook/clause-standards.md`.

## Files

| File | What it is |
|---|---|
| `fetch_cuad.sh` | downloads + extracts CUAD, stages the 12 contracts |
| `gold/build_gold_set.py` | the selection rule, in code |
| `gold/contract_manifest.json` | the 12 frozen contracts |
| `gold/intake_gold.csv` | the 120 frozen labels |
| `contracts/` (gitignored) | staged plain-text contracts |
| `intake_log.jsonl` | append-only audit trail written by `record_intake_memo` |
