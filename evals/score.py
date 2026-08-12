#!/usr/bin/env python3
"""Score eval runs against the frozen gold set and write results/results.md.

Four things are recorded per judgment, and all four are scored:
  1. presence correctness vs the CUAD-derived gold label (P/R/F1)
  2. span grounding — a "present" whose quote fails verification (< 0.95
     whitespace-normalized similarity) is counted as a false positive even
     when the presence flag was right: an unsupported assertion is not a
     correct answer in this workflow
  3. routing outcome — a wrong answer that escalated is a *caught* error;
     a wrong answer that self-served is a *production* error
  4. tokens and wall-clock, priced at list rates
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from configs import PRICES  # noqa: E402

RESULTS_DIR = ROOT / "evals" / "results"
GOLD = ROOT / "data" / "gold" / "intake_gold.csv"
SIM_FLOOR = 0.95
RUN_ORDER = ["baseline", "B", "C", "A"]
N_CONTRACTS = 12


def load_gold() -> dict:
    with open(GOLD, newline="", encoding="utf-8") as f:
        return {(r["contract_id"], r["field"]): r for r in csv.DictReader(f)}


def call_cost(model: str, usage: dict) -> float:
    p = PRICES.get(model, {"in": 0.0, "out": 0.0})
    return (
        usage["input_tokens"] * p["in"]
        + usage["cache_creation_input_tokens"] * p["in"] * 1.25
        + usage["cache_read_input_tokens"] * p["in"] * 0.10
        + usage["output_tokens"] * p["out"]
    ) / 1_000_000


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec, rec, f1


def score_run(run: dict, gold: dict) -> dict:
    is_model_run = run["config"] != "baseline"
    tp = fp = fn = tn = 0
    hallucinated = 0
    escalated = 0
    caught = production = 0
    cost = 0.0
    calib = defaultdict(lambda: [0, 0])       # confidence -> [n, n_correct]
    by_field = defaultdict(lambda: [0, 0])    # field -> [n, n_correct]
    jur_rows = []

    for r in run["results"]:
        g = gold[(r["contract_id"], r["field"])]
        gold_present = g["present"] == "yes"
        j = r["judgment"]
        pred_present = j["present"]
        grounded = (not is_model_run) or (not pred_present) or (r["span_similarity"] >= SIM_FLOOR)
        if is_model_run and pred_present and not grounded:
            hallucinated += 1

        # grounded confusion matrix: an ungrounded "present" is a false positive
        eff_pred = pred_present and grounded
        if eff_pred and gold_present:
            tp += 1
        elif eff_pred and not gold_present:
            fp += 1
        elif not eff_pred and gold_present:
            fn += 1
        else:
            tn += 1

        correct = eff_pred == gold_present
        calib[j["confidence"]][0] += 1
        calib[j["confidence"]][1] += correct
        by_field[r["field"]][0] += 1
        by_field[r["field"]][1] += correct

        if r["escalate"]:
            escalated += 1
        if not correct:
            caught += r["escalate"]
            production += not r["escalate"]

        cost += call_cost(r["model"], r["usage"])

        if r["field"] == "governing_law" and g["gold_answer"]:
            got = (j.get("jurisdiction") or "").strip().lower()
            want = g["gold_answer"].strip().lower()
            jur_rows.append(bool(got) and (got in want or want in got))

    prec, rec, f1 = prf(tp, fp, fn)
    n = len(run["results"])
    return {
        "config": run["config"],
        "description": run["description"],
        "n": n,
        "precision": prec, "recall": rec, "f1": f1,
        "accuracy": (tp + tn) / n,
        "hallucinated_spans": hallucinated if is_model_run else None,
        "pct_escalated": escalated / n,
        "caught_errors": caught, "production_errors": production,
        "cost_total": cost, "cost_per_contract": cost / N_CONTRACTS,
        "wall_clock_s": run["total_wall_clock_s"],
        "calibration": {k: {"n": v[0], "accuracy": v[1] / v[0]} for k, v in sorted(calib.items())},
        "by_field": {k: v[1] / v[0] for k, v in sorted(by_field.items())},
        "jurisdiction_accuracy": (sum(jur_rows) / len(jur_rows)) if jur_rows else None,
        "jurisdiction_n": len(jur_rows),
    }


def main():
    gold = load_gold()
    scored = []
    for cfg in RUN_ORDER:
        path = RESULTS_DIR / f"run-{cfg}.json"
        if path.exists():
            scored.append(score_run(json.loads(path.read_text()), gold))
    if not scored:
        sys.exit("no run-*.json files in evals/results/")

    lines = [
        "# Eval results",
        "",
        "120 field-level judgments (12 contracts × 10 intake fields) against the",
        "frozen CUAD-derived gold set. Scoring rules and metric definitions:",
        "[`score.py`](../score.py). Prompts were frozen before the first run and",
        "never tuned against the gold set.",
        "",
        "**Grounding is enforced in the headline numbers**: a \"present\" call whose",
        "quote fails span verification counts as a false positive even when the",
        "presence flag was right.",
        "",
        "## Headline",
        "",
        "| Config | Models | Precision | Recall | F1 | Halluc. spans | % escalated | Caught / production errors | Cost / contract | Wall clock |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in scored:
        halluc = "n/a" if s["hallucinated_spans"] is None else str(s["hallucinated_spans"])
        lines.append(
            f"| {s['config']} | {s['description']} | {s['precision']:.3f} | {s['recall']:.3f} "
            f"| **{s['f1']:.3f}** | {halluc} | {s['pct_escalated']:.0%} "
            f"| {s['caught_errors']} / {s['production_errors']} "
            f"| ${s['cost_per_contract']:.4f} | {s['wall_clock_s']:.0f}s |"
        )

    lines += ["", "## Confidence calibration", "",
              "Does self-reported confidence predict accuracy? (It is the weakest of the",
              "three routing signals, so its calibration is measured and published.)", "",
              "| Config | Confidence | n | Accuracy |", "|---|---|---|---|"]
    for s in scored:
        if s["config"] == "baseline":
            continue
        for conf, v in s["calibration"].items():
            lines.append(f"| {s['config']} | {conf} | {v['n']} | {v['accuracy']:.3f} |")

    fields = sorted(scored[0]["by_field"])
    lines += ["", "## Per-field accuracy", "",
              "| Field | " + " | ".join(s["config"] for s in scored) + " |",
              "|---|" + "---|" * len(scored)]
    for f in fields:
        lines.append(f"| {f} | " + " | ".join(f"{s['by_field'][f]:.2f}" for s in scored) + " |")

    lines += ["", "## Governing law: regex vs model", "",
              "Jurisdiction extraction accuracy on the contracts with a gold",
              "governing-law answer — the \"when NOT to use an LLM\" comparison.", "",
              "| Config | Extractor | Jurisdiction accuracy | n |", "|---|---|---|---|"]
    for s in scored:
        if s["jurisdiction_accuracy"] is None:
            continue
        extractor = "regex" if s["config"] in ("baseline", "C") else "model"
        lines.append(f"| {s['config']} | {extractor} | {s['jurisdiction_accuracy']:.3f} | {s['jurisdiction_n']} |")

    by_cfg = {s["config"]: s for s in scored}
    if "baseline" in by_cfg and "C" in by_cfg:
        b, c = by_cfg["baseline"], by_cfg["C"]
        lines += ["", "## Business framing", "",
                  f"Keyword F1 {b['f1']:.3f} → routed F1 {c['f1']:.3f}. "
                  f"Manual intake [SELF-TIMED, n=3 — see README §5] → "
                  f"${c['cost_per_contract']:.4f} and {c['wall_clock_s'] / N_CONTRACTS:.0f}s of pipeline "
                  f"per contract, with human review on the {c['pct_escalated']:.0%} of field "
                  "judgments that escalated."]

    out = RESULTS_DIR / "results.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
    (RESULTS_DIR / "scores.json").write_text(json.dumps(scored, indent=2) + "\n")
    print(f"wrote {(RESULTS_DIR / 'scores.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
