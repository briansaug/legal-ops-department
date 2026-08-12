#!/usr/bin/env python3
"""Run one eval config over the 120 frozen scenarios.

    python evals/run_eval.py --config C            # full run
    python evals/run_eval.py --config C --limit 1  # one contract (token check)
    python evals/run_eval.py --config C --demo aurasystemsinc
                                                   # one contract end-to-end,
                                                   # records a real intake memo

Each scenario = (contract, field). The pipeline per scenario:

  1. find_clause          deterministic retrieval  (no model)
  2. get_playbook_standard                          (no model)
  3. one model call -> JSON judgment                (the only model step;
                                                    governing_law in config C
                                                    uses a regex instead)
  4. verify_span          deterministic check       (no model)
  5. escalation matrix    deterministic routing     (no model)

Raw results go to evals/results/run-<config>.json with logged token usage
per call. Scoring is a separate step: evals/score.py.
"""

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp" / "contract_lake"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import anthropic  # noqa: E402
import prompts  # noqa: E402
import routing  # noqa: E402
import tools  # noqa: E402
from configs import CONFIGS, REGEX, model_for  # noqa: E402
from schema import ClauseType  # noqa: E402

RESULTS_DIR = ROOT / "evals" / "results"
SCENARIOS = ROOT / "evals" / "scenarios.jsonl"
GOLD = ROOT / "data" / "gold" / "intake_gold.csv"

client = anthropic.Anthropic(max_retries=4)


def load_scenarios() -> list[dict]:
    """scenarios.jsonl is derived 1:1 from the frozen gold set."""
    if not SCENARIOS.exists():
        with open(GOLD, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with open(SCENARIOS, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"contract_id": r["contract_id"], "field": r["field"]}) + "\n")
    return [json.loads(line) for line in SCENARIOS.read_text().splitlines() if line.strip()]


def judge_with_model(model: str, contract_id: str, clause_type: ClauseType) -> dict:
    """Steps 1-3: retrieval, playbook, one structured-output model call."""
    retrieval = tools.find_clause(contract_id, clause_type)
    standard = tools.get_playbook_standard(clause_type)
    user_prompt = prompts.build_user_prompt(
        clause_type.value, standard.standard, [w.text for w in retrieval.windows]
    )
    t0 = time.monotonic()
    msg = client.messages.create(
        model=model,
        max_tokens=16000,
        system=[{"type": "text", "text": prompts.SYSTEM, "cache_control": {"type": "ephemeral"}}],
        output_config={"format": {"type": "json_schema", "schema": prompts.JUDGMENT_SCHEMA}},
        messages=[{"role": "user", "content": user_prompt}],
    )
    wall = time.monotonic() - t0
    text = next(b.text for b in msg.content if b.type == "text")
    judgment = json.loads(text)
    return {
        "judgment": judgment,
        "n_windows": len(retrieval.windows),
        "usage": {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
            "cache_creation_input_tokens": msg.usage.cache_creation_input_tokens or 0,
            "cache_read_input_tokens": msg.usage.cache_read_input_tokens or 0,
        },
        "wall_clock_s": round(wall, 2),
    }


def judge_with_regex(contract_id: str) -> dict:
    """The governing-law non-LLM path: regex + allowlist. Zero tokens."""
    t0 = time.monotonic()
    hit = tools.extract_governing_law(contract_id)
    wall = time.monotonic() - t0
    return {
        "judgment": {
            "present": hit["found"],
            "quote": hit["evidence"],
            "playbook_status": "standard" if hit["found"] else "not_applicable",
            "confidence": "high",  # deterministic — reported for the routing signal
            "jurisdiction": hit["jurisdiction"],
        },
        "n_windows": None,
        "usage": {"input_tokens": 0, "output_tokens": 0,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        "wall_clock_s": round(wall, 4),
    }


def run_scenario(config: str, scenario: dict) -> dict:
    contract_id = scenario["contract_id"]
    clause_type = ClauseType(scenario["field"])
    model = model_for(config, clause_type)

    out = judge_with_regex(contract_id) if model == REGEX else judge_with_model(model, contract_id, clause_type)
    j = out["judgment"]

    # step 4: deterministic span verification
    if j["present"] and j["quote"]:
        v = tools.verify_span(contract_id, j["quote"])
        span_similarity = v.similarity
    elif j["present"]:
        span_similarity = 0.0  # present with no quote = automatic verification failure
    else:
        span_similarity = 1.0  # nothing asserted, nothing to verify

    # step 5: deterministic routing
    jurisdiction_ok = None
    if clause_type == ClauseType.GOVERNING_LAW:
        allow = [a.lower() for a in tools.governing_law_allowlist()]
        jur = (j.get("jurisdiction") or "").lower()
        jurisdiction_ok = bool(jur) and any(a in jur or jur in a for a in allow)
    reasons = routing.escalate_field(
        clause_type, j["present"], j["confidence"], span_similarity,
        j["playbook_status"], jurisdiction_ok,
    )

    return {
        "contract_id": contract_id,
        "field": clause_type.value,
        "model": model,
        **out,
        "span_similarity": round(span_similarity, 4),
        "escalate": bool(reasons),
        "escalation_reasons": reasons,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=sorted(CONFIGS))
    ap.add_argument("--limit", type=int, help="run only the first N contracts")
    ap.add_argument("--demo", metavar="CONTRACT_ID",
                    help="run one contract end-to-end and record an intake memo")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    scenarios = load_scenarios()
    if args.demo:
        scenarios = [s for s in scenarios if s["contract_id"] == args.demo]
        if not scenarios:
            sys.exit(f"no scenarios for contract {args.demo!r}")
    elif args.limit:
        keep = sorted({s["contract_id"] for s in scenarios})[: args.limit]
        scenarios = [s for s in scenarios if s["contract_id"] in keep]

    print(f"config {args.config} ({CONFIGS[args.config]}): {len(scenarios)} scenarios")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda s: run_scenario(args.config, s), scenarios))
    total_wall = time.monotonic() - t0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"-demo-{args.demo}" if args.demo else ("-limit" if args.limit else "")
    out_path = RESULTS_DIR / f"run-{args.config}{suffix}.json"
    out_path.write_text(json.dumps({
        "config": args.config,
        "description": CONFIGS[args.config],
        "n_scenarios": len(scenarios),
        "total_wall_clock_s": round(total_wall, 1),
        "results": results,
    }, indent=2) + "\n")

    tok_in = sum(r["usage"]["input_tokens"] + r["usage"]["cache_creation_input_tokens"]
                 + r["usage"]["cache_read_input_tokens"] for r in results)
    tok_out = sum(r["usage"]["output_tokens"] for r in results)
    print(f"wrote {out_path.relative_to(ROOT)} — {tok_in} prompt tokens, "
          f"{tok_out} output tokens, {total_wall:.0f}s wall clock")

    if args.demo:
        record_demo_memo(args.demo, results)


def record_demo_memo(contract_id: str, results: list[dict]):
    """The paralegal workflow's last step: a real memo in the audit trail."""
    from schema import Confidence, Decision, FieldJudgment, IntakeMemo, PlaybookStatus

    fields = []
    escalations = {}
    for r in sorted(results, key=lambda r: r["field"]):
        j = r["judgment"]
        quote_ok = r["span_similarity"] >= routing.SPAN_SIMILARITY_FLOOR
        fields.append(FieldJudgment(
            clause_type=ClauseType(r["field"]),
            present=j["present"],
            quote=j["quote"] if (j["present"] and quote_ok) else "",
            confidence=Confidence(j["confidence"]),
            playbook_status=PlaybookStatus(j["playbook_status"]),
            escalate=r["escalate"],
            escalation_reasons=r["escalation_reasons"],
        ))
        escalations[r["field"]] = r["escalation_reasons"]
    decision = routing.decide(escalations)
    memo = IntakeMemo(
        contract_id=contract_id,
        reviewed_by="paralegal",
        fields=fields,
        decision=Decision(decision),
        decision_basis="; ".join(
            f"{f}: {rs[0]}" for f, rs in escalations.items() if rs
        ) or "no escalation triggers fired",
    )
    out = tools.record_intake_memo(memo)
    print(f"demo memo recorded -> {out['path']} (decision: {decision})")
    for f in fields:
        flag = "ESCALATE" if f.escalate else "ok"
        print(f"  {f.clause_type.value:28} present={str(f.present):5} [{flag}]")


if __name__ == "__main__":
    main()
