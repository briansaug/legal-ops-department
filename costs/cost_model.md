# Cost model

Token counts come from logged `usage` on the real eval calls in
`evals/results/run-*.json` — not estimates. Prices are Anthropic list
rates (2026-08): claude-opus-5 $5/$25 per MTok, claude-haiku-4-5 $1/$5,
cache writes 1.25×, cache reads 0.1×. Regenerate with
`python costs/cost_model.py`.

**Volume is hypothetical.** I did not measure a real legal department's
contract volume. 200/month is the scaling input, not a finding.
Per-contract cost is measured; multiply by your own volume.

| Config | Tokens in / contract | Tokens out / contract | Cost / contract | Annual @ 200/mo (hypothetical) |
|---|---|---|---|---|
| B — claude-haiku-4-5 everywhere (floor) | 12,206 | 553 | $0.0150 | $36 |
| C — routed: haiku standard fields, opus high-stakes, regex governing law (shipped) | 12,946 | 785 | $0.0442 | $106 |
| A — claude-opus-5 everywhere (ceiling) | 16,933 | 1,523 | $0.0951 | $228 |

## The finding to lead with

**The model cost is noise.** The gap between running the expensive model
on everything (A) and the routed pipeline (C) is about **$122/year**
at this volume — roughly 2–3 hours of a paralegal's loaded time
(at an assumed $60/hr, stated here, not measured). You'd need
~**98 contracts/month** before that gap equals one paralegal hour
per month. So the routing design is not a cost play. It's an
accuracy-and-routing play — and the eval numbers say that at this volume
the expensive model wins even that: config A had the fewest wrong answers
that self-served (2, vs 10 for the routed config), which is the failure
mode that actually costs money. The ROI, if any, is in the manual-intake
hours — not the tokens.

(The A-vs-B gap is $192/year at the same hypothetical volume —
the same conclusion holds against the cheapest config.)

## Levers not claimed

- **Batch API** halves all of these numbers; intake is not
  latency-sensitive, so it would qualify. Not used in the measured runs.
- **Prompt caching** was enabled on the shared system prompt only; the
  playbook sections and retrieval windows were not cached. More
  aggressive caching would cut input cost further. Measured numbers
  include the actual cache hits from the runs, nothing assumed.
