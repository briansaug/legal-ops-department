"""contract-lake MCP server (stdio).

Thin wrapper: every tool is a one-line delegation to tools.py, so the eval
harness and the interactive department run the identical code path.
"""

from mcp.server.mcpserver import MCPServer

import tools
from schema import ClauseType, IntakeMemo

app = MCPServer(
    "contract-lake",
    instructions=(
        "Contract intake tools for the legal-ops department. "
        "Never assert a clause exists without a verbatim span; always confirm "
        "quotes with verify_span. Playbook standards win over model judgment. "
        "Every completed review must call record_intake_memo."
    ),
)


@app.tool()
def search_contracts(query: str = "") -> list[dict]:
    """List staged contracts (id substring filter optional). Returns ids,
    sizes, and est_tokens — check size before reading anything."""
    return [c.model_dump() for c in tools.search_contracts(query)]


@app.tool()
def get_contract(contract_id: str, page: int = 1) -> dict:
    """Read one ~12K-char page of a contract. Long contracts never enter
    context whole — page through, or better, use find_clause."""
    return tools.get_contract(contract_id, page).model_dump()


@app.tool()
def find_clause(contract_id: str, clause_type: ClauseType) -> dict:
    """Deterministic cue-pattern retrieval for one of the ten intake fields.
    No model involved. Returns candidate windows with char offsets; an empty
    result is evidence of absence, not proof."""
    return tools.find_clause(contract_id, clause_type).model_dump()


@app.tool()
def verify_span(contract_id: str, quote: str) -> dict:
    """Check that a quote appears verbatim (whitespace-normalized) in the
    contract. Required before asserting any clause exists. A quote that
    fails this check must not appear in a memo."""
    return tools.verify_span(contract_id, quote).model_dump()


@app.tool()
def get_playbook_standard(clause_type: ClauseType) -> dict:
    """The department's standard and escalation rule for a clause type.
    This text wins over model judgment."""
    return tools.get_playbook_standard(clause_type).model_dump()


@app.tool()
def record_intake_memo(memo: IntakeMemo) -> dict:
    """Append a completed intake memo to data/intake_log.jsonl. Every
    completed review ends with this call — it is the audit trail."""
    return tools.record_intake_memo(memo)


if __name__ == "__main__":
    app.run()
