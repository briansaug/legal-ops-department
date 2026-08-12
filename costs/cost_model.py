#!/usr/bin/env python3
"""Cost model from logged usage on the real eval runs — not estimates.

Reads evals/results/run-{A,B,C}.json, prices every call at list rates
(cache-write 1.25x, cache-read 0.1x), and writes cost_model.md.

The 200 contracts/month volume is HYPOTHETICAL and labeled as such in the
output: per-contract cost is measured; volume is a scaling input.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

from configs import CONFIGS, PRICES  # noqa: E402
from score import call_cost  # noqa: E402

RESULTS = ROOT / "evals" / "results"
N_CONTRACTS = 12
VOLUME_PER_MONTH = 200          # hypothetical — stated inline in the output
PARALEGAL_HOUR_USD = 60         # loaded-cost assumption, stated inline


def main():
    rows = []
    for cfg in ("B", "C", "A"):
        run = json.loads((RESULTS / f"run-{cfg}.json").read_text())
        tok_in = sum(r["usage"]["input_tokens"] + r["usage"]["cache_creation_input_tokens"]
                     + r["usage"]["cache_read_input_tokens"] for r in run["results"])
        tok_out = sum(r["usage"]["output_tokens"] for r in run["results"])
        cost = sum(call_cost(r["model"], r["usage"]) for r in run["results"])
        rows.append({
            "config": cfg,
            "desc": CONFIGS[cfg],
            "tok_in_per_contract": tok_in / N_CONTRACTS,
            "tok_out_per_contract": tok_out / N_CONTRACTS,
            "cost_per_contract": cost / N_CONTRACTS,
            "annual": cost / N_CONTRACTS * VOLUME_PER_MONTH * 12,
        })

    by = {r["config"]: r for r in rows}
    gap_ac = by["A"]["annual"] - by["C"]["annual"]
    gap_ab = by["A"]["annual"] - by["B"]["annual"]
    # contracts/month where the monthly A-vs-C gap equals one paralegal hour
    per_contract_gap = by["A"]["cost_per_contract"] - by["C"]["cost_per_contract"]
    breakeven = PARALEGAL_HOUR_USD / per_contract_gap

    md = [
        "# Cost model",
        "",
        "Token counts come from logged `usage` on the real eval calls in",
        "`evals/results/run-*.json` — not estimates. Prices are Anthropic list",
        "rates (2026-08): claude-opus-5 $5/$25 per MTok, claude-haiku-4-5 $1/$5,",
        "cache writes 1.25×, cache reads 0.1×. Regenerate with",
        "`python costs/cost_model.py`.",
        "",
        "**Volume is hypothetical.** I did not measure a real legal department's",
        f"contract volume. {VOLUME_PER_MONTH}/month is the scaling input, not a finding.",
        "Per-contract cost is measured; multiply by your own volume.",
        "",
        "| Config | Tokens in / contract | Tokens out / contract | Cost / contract | "
        f"Annual @ {VOLUME_PER_MONTH}/mo (hypothetical) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        md.append(
            f"| {r['config']} — {r['desc']} | {r['tok_in_per_contract']:,.0f} "
            f"| {r['tok_out_per_contract']:,.0f} | ${r['cost_per_contract']:.4f} "
            f"| ${r['annual']:.0f} |"
        )

    md += [
        "",
        "## The finding to lead with",
        "",
        "**The model cost is noise.** The gap between running the expensive model",
        f"on everything (A) and the routed pipeline (C) is about **${gap_ac:.0f}/year**",
        f"at this volume — roughly {gap_ac / PARALEGAL_HOUR_USD:.0f}–{gap_ac / PARALEGAL_HOUR_USD + 1:.0f} hours of a paralegal's loaded time",
        f"(at an assumed ${PARALEGAL_HOUR_USD}/hr, stated here, not measured). You'd need",
        f"~**{breakeven:,.0f} contracts/month** before the monthly gap equals one",
        "paralegal hour. So the routing design is not a cost play. It's an",
        "accuracy-and-routing play — and the eval numbers say that at this volume",
        "the expensive model wins even that: config A had the fewest wrong answers",
        "that self-served (2, vs 10 for the routed config), which is the failure",
        "mode that actually costs money. The ROI, if any, is in the manual-intake",
        "hours — not the tokens.",
        "",
        f"(The A-vs-B gap is ${gap_ab:.0f}/year at the same hypothetical volume —",
        "the same conclusion holds against the cheapest config.)",
        "",
        "## Levers not claimed",
        "",
        "- **Batch API** halves all of these numbers; intake is not",
        "  latency-sensitive, so it would qualify. Not used in the measured runs.",
        "- **Prompt caching** was enabled on the shared system prompt only; the",
        "  playbook sections and retrieval windows were not cached. More",
        "  aggressive caching would cut input cost further. Measured numbers",
        "  include the actual cache hits from the runs, nothing assumed.",
    ]

    out = ROOT / "costs" / "cost_model.md"
    out.write_text("\n".join(md) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
    for r in rows:
        print(f"  {r['config']}: ${r['cost_per_contract']:.4f}/contract, ${r['annual']:.0f}/yr @ {VOLUME_PER_MONTH}/mo")


if __name__ == "__main__":
    main()
