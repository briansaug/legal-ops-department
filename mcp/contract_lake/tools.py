"""contract-lake core logic.

Pure functions over the staged contract files. Two frontends use this module:
`server.py` exposes it over MCP for interactive work in Claude Code, and
`evals/run_eval.py` imports it directly so the eval exercises the exact same
retrieval and verification code the department uses.

Nothing in this file calls a model. `find_clause` is deterministic cue-pattern
retrieval; `verify_span` is string matching. That is the point: retrieval and
verification are checkable, so the model is only trusted for the judgment in
between.
"""

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from schema import (
    HIGH_STAKES,
    ClauseSearchResult,
    ClauseType,
    ClauseWindow,
    ContractPage,
    ContractSummary,
    IntakeMemo,
    PlaybookStandard,
    SpanVerification,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "data" / "contracts"
PLAYBOOK_DIR = ROOT / "playbook"
INTAKE_LOG = ROOT / "data" / "intake_log.jsonl"

PAGE_CHARS = 12_000          # ~3K tokens per page
WINDOW_PAD = 700             # context chars around a cue hit
MAX_WINDOW_CHARS = 16_000    # ~4K tokens ceiling per find_clause call
MAX_WINDOWS = 8

# Deterministic retrieval cues per clause type. These are the codified version
# of the Ctrl-F list that used to live in a senior paralegal's head — and they
# double as the keyword baseline in evals/baseline_keyword.py.
CUE_PATTERNS: dict[ClauseType, list[str]] = {
    ClauseType.ANTI_ASSIGNMENT: [
        r"\bassign(?:ment|able|ed|s)?\b",
        r"\btransfer\s+(?:of\s+)?this\s+agreement\b",
    ],
    ClauseType.CHANGE_OF_CONTROL: [
        r"\bchange\s+(?:of|in)\s+control\b",
        r"\bmerger\b|\bconsolidation\b",
        r"\bcontrolling\s+interest\b|\bacquisition\s+of\b",
    ],
    ClauseType.TERMINATION_FOR_CONVENIENCE: [
        r"\bterminat\w*[^.]{0,80}\b(?:convenience|without\s+cause|for\s+any\s+reason|at\s+any\s+time)\b",
        r"\b(?:convenience|without\s+cause|for\s+any\s+reason)[^.]{0,80}\bterminat\w*",
    ],
    ClauseType.CAP_ON_LIABILITY: [
        r"\bliabilit\w+[^.]{0,120}\b(?:exceed|limited\s+to|in\s+no\s+event|aggregate)\b",
        r"\b(?:not\s+exceed|limited\s+to|in\s+no\s+event)[^.]{0,120}\bliabilit\w+",
        r"\blimitation\s+of\s+liability\b",
    ],
    ClauseType.UNCAPPED_LIABILITY: [
        r"\b(?:unlimited|uncapped)\s+liabilit\w+",
        r"\b(?:limitation|cap)s?\b[^.]{0,120}\bshall\s+not\s+apply\b",
        r"\bnothing[^.]{0,80}\b(?:limit|exclude)[^.]{0,60}\bliabilit\w+",
        r"\bexcept\s+for[^.]{0,120}\b(?:indemnif\w+|gross\s+negligence|willful|confidential)",
    ],
    ClauseType.NON_COMPETE: [
        r"\bcompet\w+\b",
        r"\bnon-?compete\b",
    ],
    ClauseType.EXCLUSIVITY: [
        r"\bexclusiv\w+\b",
        r"\bsole(?:ly)?\s+(?:and\s+exclusive|source|provider|distributor)\b",
    ],
    ClauseType.MOST_FAVORED_NATION: [
        r"\bmost\s+favou?red\b",
        r"\bno\s+less\s+favou?rable\b|\bat\s+least\s+as\s+favou?rable\b",
    ],
    ClauseType.GOVERNING_LAW: [
        r"\bgoverned\s+by\b|\bgoverning\s+law\b",
        r"\bconstrued\s+(?:and\s+enforced\s+)?in\s+accordance\s+with\b",
        r"\blaws?\s+of\s+the\s+(?:State|Commonwealth|Province)\b",
    ],
    ClauseType.RENEWAL_TERM: [
        r"\brenew\w*\b",
        r"\bsuccessive\s+(?:one|two|\d+|\(\d+\))[^.]{0,40}\b(?:year|month)\b",
        r"\bautomatically\s+(?:extend|renew)\w*\b",
    ],
}

# Governing-law jurisdiction extraction — the "when NOT to use an LLM" field.
GOVERNING_LAW_RE = re.compile(
    r"(?:governed\s+by|in\s+accordance\s+with|pursuant\s+to)[^.]{0,120}?"
    r"laws?\s+of(?:\s+the)?(?:\s+(?:state|commonwealth|province|federal\s+republic|republic))?(?:\s+of)?\s+"
    r"([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+){0,3})",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _read(contract_id: str) -> str:
    path = CONTRACTS_DIR / f"{contract_id}.txt"
    if not path.exists():
        known = ", ".join(sorted(p.stem for p in CONTRACTS_DIR.glob("*.txt"))) or "(none staged)"
        raise FileNotFoundError(
            f"no contract '{contract_id}' in data/contracts/ — known ids: {known}"
        )
    return path.read_text(encoding="utf-8", errors="replace")


def search_contracts(query: str = "") -> list[ContractSummary]:
    """List staged contracts, optionally filtered by id substring."""
    out = []
    for path in sorted(CONTRACTS_DIR.glob("*.txt")):
        if query and query.lower() not in path.stem.lower():
            continue
        size = path.stat().st_size
        out.append(
            ContractSummary(
                contract_id=path.stem,
                filename=path.name,
                size_bytes=size,
                est_tokens=size // 4,
            )
        )
    return out


def get_contract(contract_id: str, page: int = 1) -> ContractPage:
    """Paged read — a 40-page contract never enters context whole."""
    text = _read(contract_id)
    total = max(1, -(-len(text) // PAGE_CHARS))
    page = max(1, min(page, total))
    start = (page - 1) * PAGE_CHARS
    return ContractPage(
        contract_id=contract_id,
        page=page,
        total_pages=total,
        text=text[start : start + PAGE_CHARS],
    )


def find_clause(contract_id: str, clause_type: ClauseType) -> ClauseSearchResult:
    """Deterministic cue-pattern retrieval. No model call. Turns a ~35K-token
    read into a few thousand tokens of candidate windows."""
    text = _read(contract_id)
    hits: list[tuple[int, int, str]] = []
    for pattern in CUE_PATTERNS[clause_type]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            hits.append((m.start(), m.end(), m.group(0)[:60]))
    hits.sort()

    windows: list[ClauseWindow] = []
    total_chars = 0
    for start, end, cue in hits:
        w_start, w_end = max(0, start - WINDOW_PAD), min(len(text), end + WINDOW_PAD)
        if windows and w_start <= windows[-1].end_char:  # merge overlap
            merged_end = max(windows[-1].end_char, w_end)
            total_chars += merged_end - windows[-1].end_char
            windows[-1] = ClauseWindow(
                start_char=windows[-1].start_char,
                end_char=merged_end,
                matched_cue=windows[-1].matched_cue,
                text=text[windows[-1].start_char : merged_end],
            )
            continue
        if len(windows) >= MAX_WINDOWS or total_chars + (w_end - w_start) > MAX_WINDOW_CHARS:
            break
        windows.append(
            ClauseWindow(start_char=w_start, end_char=w_end, matched_cue=cue,
                         text=text[w_start:w_end])
        )
        total_chars += w_end - w_start

    note = ""
    if not windows:
        note = ("no cue pattern fired — treat as evidence of absence, not proof; "
                "confirm with get_contract if the field is high-stakes")
    return ClauseSearchResult(
        contract_id=contract_id,
        clause_type=clause_type,
        windows=windows,
        est_tokens=total_chars // 4,
        note=note,
    )


def verify_span(contract_id: str, quote: str) -> SpanVerification:
    """The anti-hallucination primitive. A quote that is not in the document
    is a miss, whatever the model thought of it."""
    text = _read(contract_id)
    n_text, n_quote = _norm(text), _norm(quote)
    if not n_quote:
        return SpanVerification(contract_id=contract_id, found=False, similarity=0.0)
    if n_quote in n_text:
        return SpanVerification(contract_id=contract_id, found=True, similarity=1.0,
                                best_match=n_quote)

    # fuzzy fallback: closest window, for diagnosis and the routing signal
    step = max(1, len(n_quote) // 4)
    best_ratio, best_start = 0.0, 0
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(n_quote)
    for start in range(0, max(1, len(n_text) - len(n_quote) + 1), step):
        window = n_text[start : start + len(n_quote) + 40]
        sm.set_seq1(window)
        if sm.real_quick_ratio() <= best_ratio or sm.quick_ratio() <= best_ratio:
            continue
        ratio = sm.ratio()
        if ratio > best_ratio:
            best_ratio, best_start = ratio, start
    return SpanVerification(
        contract_id=contract_id,
        found=False,
        similarity=round(best_ratio, 4),
        best_match=n_text[best_start : best_start + len(n_quote) + 40][:400],
    )


def get_playbook_standard(clause_type: ClauseType) -> PlaybookStandard:
    """Pull the department standard for a clause type from playbook/
    clause-standards.md. The playbook file wins over model judgment."""
    text = (PLAYBOOK_DIR / "clause-standards.md").read_text(encoding="utf-8")
    marker = f"## {clause_type.value}"
    idx = text.find(marker)
    if idx == -1:
        raise KeyError(f"playbook has no section '{marker}'")
    section = text[idx:]
    nxt = section.find("\n## ", 1)
    section = section[: nxt if nxt != -1 else len(section)].strip()
    m = re.search(r"\*\*Escalate when:\*\*\s*(.+)", section)
    escalation = m.group(1).strip() if m else ""
    return PlaybookStandard(
        clause_type=clause_type,
        standard=section,
        escalation_rule=escalation,
        high_stakes=clause_type in HIGH_STAKES,
    )


def record_intake_memo(memo: IntakeMemo) -> dict:
    """Append the completed memo to the audit trail the old process lacked."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **memo.model_dump(mode="json"),
    }
    INTAKE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(INTAKE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"logged": True, "path": str(INTAKE_LOG.relative_to(ROOT)), "ts": entry["ts"]}


def extract_governing_law(contract_id: str) -> dict:
    """Regex jurisdiction extraction — the deliberate non-LLM path for the
    one deterministic field. Compared against the model in the evals."""
    result = find_clause(contract_id, ClauseType.GOVERNING_LAW)
    for w in result.windows:
        m = GOVERNING_LAW_RE.search(_norm(w.text))
        if m:
            jurisdiction = m.group(1).strip()
            # trim trailing boilerplate words the pattern can drag in
            jurisdiction = re.sub(
                r"\s+(?:without|excluding|applicable|and|shall|as)\b.*$", "", jurisdiction
            ).strip()
            return {"found": True, "jurisdiction": jurisdiction, "evidence": _norm(m.group(0))}
    return {"found": False, "jurisdiction": "", "evidence": ""}


def governing_law_allowlist() -> list[str]:
    """Jurisdictions that do NOT auto-escalate, per the playbook file."""
    text = (PLAYBOOK_DIR / "governing-law-allowlist.md").read_text(encoding="utf-8")
    return [line.lstrip("- ").strip() for line in text.splitlines()
            if line.startswith("- ")]
