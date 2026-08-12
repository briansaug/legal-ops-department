#!/usr/bin/env python3
"""Build (or verify) the frozen gold set for contract intake triage.

The selection rule below was written down before any model call was made,
then frozen. It is deterministic end to end — no randomness, no manual picks.

  1. Candidates: CUAD contracts whose plain-text file is under 120 KB and
     whose CSV row maps exactly to a text file by filename stem.
  2. Pick 12 contracts by a greedy balance rule: repeatedly take the
     candidate that most improves positive/negative coverage across the ten
     intake fields (target: >=3 present and >=3 absent per field among the
     12), ties broken by sorted filename order.
  3. The chosen 12 are written to contract_manifest.json. Once that file
     exists the selection never re-runs — the manifest is the frozen truth,
     and this script only re-stages files and re-verifies labels against it.

Outputs
  data/gold/contract_manifest.json   the 12 frozen contracts
  data/gold/intake_gold.csv          120 rows: one per (contract, field)
  data/contracts/<id>.txt            staged contract text (gitignored)

Gold labels come from CUAD's master_clauses.csv (annotated by law students
under attorney supervision), extracted programmatically — not hand-labeled.
"""

import ast
import csv
import json
import re
import shutil
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent
CUAD = DATA / "cuad" / "CUAD_v1"
GOLD = DATA / "gold"
CONTRACTS = DATA / "contracts"

MAX_TXT_BYTES = 120_000
N_CONTRACTS = 12
PER_FIELD_TARGET = 3  # aim for >=3 present and >=3 absent per field

# canonical field id -> master_clauses.csv column
FIELDS = {
    "anti_assignment": "Anti-Assignment",
    "change_of_control": "Change Of Control",
    "termination_for_convenience": "Termination For Convenience",
    "cap_on_liability": "Cap On Liability",
    "uncapped_liability": "Uncapped Liability",
    "non_compete": "Non-Compete",
    "exclusivity": "Exclusivity",
    "most_favored_nation": "Most Favored Nation",
    "governing_law": "Governing Law",
    "renewal_term": "Renewal Term",
}


def parse_spans(cell: str) -> list[str]:
    """CUAD span cells are python-list literals of verbatim quotes."""
    cell = (cell or "").strip()
    if not cell or cell == "[]":
        return []
    try:
        spans = ast.literal_eval(cell)
    except (ValueError, SyntaxError):
        return []
    return [s for s in spans if isinstance(s, str) and s.strip()]


def is_present(answer: str, spans: list[str]) -> bool:
    """Yes/No columns are authoritative; text columns (Governing Law,
    Renewal Term) count as present when annotators extracted a span."""
    answer = (answer or "").strip()
    if answer in ("Yes", "No"):
        return answer == "Yes"
    return bool(spans) or bool(answer)


def norm(text: str) -> str:
    """Whitespace-insensitive form for span-grounding checks."""
    return re.sub(r"\s+", " ", text).strip()


def make_id(stem: str, taken: set) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", stem.split("_")[0].lower()).strip("-")[:28]
    cid, n = slug, 2
    while cid in taken:
        cid, n = f"{slug}-{n}", n + 1
    taken.add(cid)
    return cid


def load_rows():
    with open(CUAD / "master_clauses.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def candidates(rows):
    txt_dir = CUAD / "full_contract_txt"
    stems = {p.stem: p for p in txt_dir.glob("*.txt")}
    out = []
    for row in rows:
        stem = Path(row["Filename"]).stem
        path = stems.get(stem)
        if path is None:
            continue
        size = path.stat().st_size
        if size >= MAX_TXT_BYTES:
            continue
        labels = {}
        for fid, col in FIELDS.items():
            spans = parse_spans(row[col])
            labels[fid] = {
                "present": is_present(row[col + "-Answer"], spans),
                "answer": (row[col + "-Answer"] or "").strip(),
                "spans": spans,
            }
        out.append({"stem": stem, "path": path, "size": size, "labels": labels})
    return sorted(out, key=lambda c: c["stem"])


def select(cands):
    """Greedy: maximize marginal gain toward >=3 present / >=3 absent per
    field. Deterministic — ties go to sorted filename order."""
    counts = {fid: {"yes": 0, "no": 0} for fid in FIELDS}
    chosen = []
    pool = list(cands)
    while len(chosen) < N_CONTRACTS and pool:
        best, best_gain = None, -1
        for c in pool:
            gain = 0
            for fid in FIELDS:
                side = "yes" if c["labels"][fid]["present"] else "no"
                if counts[fid][side] < PER_FIELD_TARGET:
                    gain += 1
            if gain > best_gain:
                best, best_gain = c, gain
        chosen.append(best)
        pool.remove(best)
        for fid in FIELDS:
            side = "yes" if best["labels"][fid]["present"] else "no"
            counts[fid][side] += 1
    return chosen, counts


def main():
    rows = load_rows()
    manifest_path = GOLD / "contract_manifest.json"

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        by_stem = {c["stem"]: c for c in candidates(rows)}
        chosen = []
        for entry in manifest:
            c = by_stem.get(entry["stem"])
            if c is None:
                sys.exit(f"FROZEN CONTRACT MISSING FROM CUAD DATA: {entry['stem']}")
            c["id"] = entry["id"]
            chosen.append(c)
        print(f"Frozen manifest found — re-staging {len(chosen)} contracts, not re-selecting.")
    else:
        cands = candidates(rows)
        print(f"{len(cands)} candidate contracts under {MAX_TXT_BYTES // 1000} KB")
        chosen, counts = select(cands)
        taken = set()
        for c in chosen:
            c["id"] = make_id(c["stem"], taken)
        manifest = [{"id": c["id"], "stem": c["stem"], "size_bytes": c["size"]} for c in chosen]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print("Field balance across the 12 (present/absent):")
        for fid in FIELDS:
            print(f"  {fid:28} {counts[fid]['yes']:2d} / {counts[fid]['no']:2d}")

    # stage contract text
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    for c in chosen:
        shutil.copyfile(c["path"], CONTRACTS / f"{c['id']}.txt")

    # write gold rows + span-grounding verification
    gold_path = GOLD / "intake_gold.csv"
    grounded = total_spans = 0
    with open(gold_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["contract_id", "field", "present", "gold_answer", "gold_spans"])
        for c in chosen:
            text = norm((CONTRACTS / f"{c['id']}.txt").read_text(encoding="utf-8", errors="replace"))
            for fid in FIELDS:
                lab = c["labels"][fid]
                for s in lab["spans"]:
                    total_spans += 1
                    if norm(s) in text:
                        grounded += 1
                w.writerow([
                    c["id"], fid,
                    "yes" if lab["present"] else "no",
                    lab["answer"] if fid == "governing_law" else "",
                    json.dumps(lab["spans"]),
                ])
    n_rows = len(chosen) * len(FIELDS)
    print(f"Wrote {n_rows} gold judgments to {gold_path.relative_to(DATA.parent)}")
    print(f"Span grounding check: {grounded}/{total_spans} gold spans found verbatim "
          f"(whitespace-normalized) in staged contract text")
    if manifest_path.exists() and n_rows != N_CONTRACTS * len(FIELDS):
        sys.exit("row count mismatch — investigate before using")


if __name__ == "__main__":
    main()
