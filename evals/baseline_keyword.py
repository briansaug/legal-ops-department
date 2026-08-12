#!/usr/bin/env python3
"""Keyword baseline — a faithful model of the Ctrl-F process.

Presence prediction = "did any cue pattern fire in the contract", using the
exact same cue patterns `find_clause` uses (the codified version of the
paralegal's search-term list). No model, no cost, instant. This is the
honest [baseline] -> [pipeline] reference the results table is built on.

Governing law additionally gets the regex jurisdiction extraction — the
candidate non-LLM path whose accuracy decides whether the model is used for
that field at all.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp" / "contract_lake"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tools  # noqa: E402
from run_eval import RESULTS_DIR, load_scenarios  # noqa: E402
from schema import ClauseType  # noqa: E402


def main():
    scenarios = load_scenarios()
    t0 = time.monotonic()
    results = []
    for s in scenarios:
        clause_type = ClauseType(s["field"])
        retrieval = tools.find_clause(s["contract_id"], clause_type)
        judgment = {
            "present": bool(retrieval.windows),
            "quote": "",
            "playbook_status": "not_applicable",
            "confidence": "high",
            "jurisdiction": "",
        }
        if clause_type == ClauseType.GOVERNING_LAW:
            hit = tools.extract_governing_law(s["contract_id"])
            judgment["jurisdiction"] = hit["jurisdiction"]
        results.append({
            "contract_id": s["contract_id"],
            "field": clause_type.value,
            "model": "keyword",
            "judgment": judgment,
            "n_windows": len(retrieval.windows),
            "usage": {"input_tokens": 0, "output_tokens": 0,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            "wall_clock_s": 0.0,
            "span_similarity": 1.0,   # asserts no spans, so nothing can hallucinate
            "escalate": False,        # the Ctrl-F process has no routing layer
            "escalation_reasons": [],
        })
    total_wall = time.monotonic() - t0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "run-baseline.json"
    out_path.write_text(json.dumps({
        "config": "baseline",
        "description": "keyword cue-pattern search (the Ctrl-F process), $0.00",
        "n_scenarios": len(results),
        "total_wall_clock_s": round(total_wall, 2),
        "results": results,
    }, indent=2) + "\n")
    print(f"wrote {out_path.relative_to(ROOT)} in {total_wall:.2f}s")


if __name__ == "__main__":
    main()
