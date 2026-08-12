# Eval results

120 field-level judgments (12 contracts × 10 intake fields) against the
frozen CUAD-derived gold set. Scoring rules and metric definitions:
[`score.py`](../score.py). Prompts were frozen before the first run and
never tuned against the gold set.

**Grounding is enforced in the headline numbers**: a "present" call whose
quote fails span verification counts as a false positive even when the
presence flag was right.

## Headline

| Config | Models | Precision | Recall | F1 | Halluc. spans | % escalated | Caught / production errors | Cost / contract | Wall clock |
|---|---|---|---|---|---|---|---|---|---|
| baseline | keyword cue-pattern search (the Ctrl-F process), $0.00 | 0.714 | 0.849 | **0.776** | n/a | 0% | 0 / 26 | $0.0000 | 0s |
| B | claude-haiku-4-5 everywhere (floor) | 0.864 | 0.717 | **0.784** | 4 | 32% | 7 / 14 | $0.0150 | 23s |
| C | routed: haiku standard fields, opus high-stakes, regex governing law (shipped) | 0.895 | 0.642 | **0.747** | 6 | 58% | 13 / 10 | $0.0442 | 42s |
| A | claude-opus-5 everywhere (ceiling) | 0.911 | 0.774 | **0.837** | 0 | 90% | 14 / 2 | $0.0951 | 73s |

## Confidence calibration

Does self-reported confidence predict accuracy? (It is the weakest of the
three routing signals, so its calibration is measured and published.)

| Config | Confidence | n | Accuracy |
|---|---|---|---|
| B | high | 118 | 0.831 |
| B | medium | 2 | 0.500 |
| C | high | 82 | 0.780 |
| C | low | 13 | 0.769 |
| C | medium | 25 | 0.920 |
| A | high | 35 | 0.914 |
| A | low | 13 | 0.692 |
| A | medium | 72 | 0.875 |

## Per-field accuracy

| Field | baseline | B | C | A |
|---|---|---|---|---|
| anti_assignment | 0.75 | 0.75 | 0.58 | 0.92 |
| cap_on_liability | 0.92 | 0.67 | 0.67 | 0.75 |
| change_of_control | 0.58 | 0.67 | 0.67 | 0.67 |
| exclusivity | 0.75 | 0.92 | 1.00 | 1.00 |
| governing_law | 1.00 | 1.00 | 0.83 | 1.00 |
| most_favored_nation | 0.83 | 0.83 | 0.92 | 0.92 |
| non_compete | 0.75 | 1.00 | 1.00 | 1.00 |
| renewal_term | 0.92 | 0.92 | 0.92 | 0.92 |
| termination_for_convenience | 0.67 | 0.92 | 0.92 | 0.92 |
| uncapped_liability | 0.67 | 0.58 | 0.58 | 0.58 |

## Governing law: regex vs model

Jurisdiction extraction accuracy on the contracts with a gold
governing-law answer — the "when NOT to use an LLM" comparison.

| Config | Extractor | Jurisdiction accuracy | n |
|---|---|---|---|
| baseline | regex | 0.778 | 9 |
| B | model | 1.000 | 9 |
| C | regex | 0.778 | 9 |
| A | model | 1.000 | 9 |

## Business framing

Keyword F1 0.776 → routed F1 0.747, at $0.0442 and 4s of pipeline per contract, with human review on the 58% of field judgments that escalated. No manual-time baseline was measured (see README §5), so no hours-saved claim is made.
