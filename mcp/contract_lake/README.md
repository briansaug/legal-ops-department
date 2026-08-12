# contract-lake MCP server

Six tools over the staged contract files. Stdio transport, registered in the
repo's `.mcp.json`. The schemas in [`schema.py`](schema.py) carry the domain
knowledge: `clause_type` is a closed enum of the ten intake fields,
`decision` is a closed enum of three routes — a model talking to this server
cannot invent an eleventh field or a fourth decision.

`server.py` is a thin wrapper over [`tools.py`](tools.py); the eval harness
imports `tools.py` directly, so evals exercise the identical retrieval and
verification code the interactive department uses.

## Tools

| Tool | Purpose | Model involved? |
|---|---|---|
| `search_contracts` | list staged contracts with `est_tokens` so callers can decide paging before reading | no |
| `get_contract` | **paged** read (~12K chars/page) — a 40-page contract never enters context whole | no |
| `find_clause` | **deterministic** cue-pattern retrieval for one field; turns a ~35K-token read into a few K tokens of candidate windows | no |
| `verify_span` | anti-hallucination primitive: verbatim (whitespace-normalized) match, with fuzzy similarity for diagnosis — also the primary routing confidence signal | no |
| `get_playbook_standard` | the department standard + escalation rule for a clause type; this text wins over model judgment | no |
| `record_intake_memo` | appends to `data/intake_log.jsonl` — the audit trail the old process lacked | no |

None of the six calls a model. The model sits *between* the tools: it reads
`find_clause` windows and produces judgments; the tools make its inputs small
and its outputs checkable.

## Constraints

- `find_clause` returns at most 8 windows / ~16K chars (~4K tokens). Cue
  patterns are in `tools.CUE_PATTERNS` — they double as the eval's keyword
  baseline.
- `verify_span` normalizes whitespace only. Case and punctuation must match
  the document.
- `record_intake_memo` validates against the full `IntakeMemo` model —
  malformed memos are rejected at the schema layer, before anything is
  written.

## Failure modes

| Failure | Behavior |
|---|---|
| unknown `contract_id` | error message lists the known ids — no silent empty result |
| no cue fires in `find_clause` | empty window list + an explicit note that absence of cues is evidence, not proof, of absence |
| fabricated quote to `verify_span` | `found=false` with the closest real text and its similarity, so the caller can see *how* wrong the quote was |
| clause type missing from the playbook | `KeyError` — a field with no written standard should fail loudly, not default |
| CUAD text artifacts (page-break `Source:` watermarks) | spans that straddle a watermark fail verbatim match and surface via the fuzzy similarity score instead |

## Smoke tests run during the build

Each tool was exercised as it was written (see the build log in the repo
history): 12 contracts listed, paged reads, retrieval windows for all ten
fields, a real quote verifying at 1.0 vs a fabricated quote at 0.44, a
playbook lookup, and a logged memo. The server was also driven end-to-end
over stdio MCP (`initialize` → `list_tools` → `call_tool`).
