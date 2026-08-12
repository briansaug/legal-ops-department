"""Frozen eval prompts. Written before the first run; not tuned against the
gold set at any point. If these ever change, every result in results.md is
stale and must be re-run.
"""

SYSTEM = """You are a contract-intake reviewer in a legal operations department.
You judge ONE intake field for ONE contract per request.

Hard rules:
- Never assert a clause exists without a verbatim quote from the provided
  contract text. The quote must be copied exactly — same words, same
  punctuation. A paraphrase counts as a miss.
- The playbook standard provided is the department's position and wins over
  your own legal judgment.
- Report confidence honestly; your calibration is measured. "high" means you
  would be surprised to be wrong.
- The retrieval windows below are candidate regions found by deterministic
  cue patterns. They may contain the clause, or may be false hits. Absence of
  a clause from the windows is evidence, not proof, that the contract lacks it.
"""

JUDGMENT_INSTRUCTIONS = """Judge whether the contract contains a {field_title} provision.

Respond with:
- present: true only if the windows contain an actual {field_title} provision
  per the playbook definition above.
- quote: if present, the single most probative verbatim span copied EXACTLY
  from the window text (a sentence or clause, not a whole section). Empty
  string if absent.
- playbook_status: "standard" if the provision matches the department
  standard, "non_standard" if it deviates, "not_applicable" if absent.
- confidence: "high", "medium", or "low".
- jurisdiction: for governing_law only, the governing jurisdiction as a short
  string (e.g. "New York", "Germany"). Empty string for all other fields.
"""

JUDGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "present": {"type": "boolean"},
        "quote": {"type": "string"},
        "playbook_status": {"type": "string", "enum": ["standard", "non_standard", "not_applicable"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "jurisdiction": {"type": "string"},
    },
    "required": ["present", "quote", "playbook_status", "confidence", "jurisdiction"],
    "additionalProperties": False,
}


def build_user_prompt(field_id: str, playbook_standard: str, windows: list[str]) -> str:
    field_title = field_id.replace("_", " ")
    windows_text = (
        "\n\n---\n\n".join(f"[window {i + 1}]\n{w}" for i, w in enumerate(windows))
        if windows
        else "(no cue pattern fired — no candidate windows)"
    )
    return (
        f"## Playbook standard for {field_id}\n\n{playbook_standard}\n\n"
        f"## Retrieval windows\n\n{windows_text}\n\n"
        f"## Task\n\n{JUDGMENT_INSTRUCTIONS.format(field_title=field_title)}"
    )
