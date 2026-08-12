"""Schemas for the contract-lake MCP server.

The domain knowledge lives here, in closed enums — a model talking to this
server cannot invent an eleventh clause type or a fourth decision.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    """The ten intake-memo fields. Closed set."""

    ANTI_ASSIGNMENT = "anti_assignment"
    CHANGE_OF_CONTROL = "change_of_control"
    TERMINATION_FOR_CONVENIENCE = "termination_for_convenience"
    CAP_ON_LIABILITY = "cap_on_liability"
    UNCAPPED_LIABILITY = "uncapped_liability"
    NON_COMPETE = "non_compete"
    EXCLUSIVITY = "exclusivity"
    MOST_FAVORED_NATION = "most_favored_nation"
    GOVERNING_LAW = "governing_law"
    RENEWAL_TERM = "renewal_term"


# Present in any form -> the memo escalates. No exceptions, not model-overridable.
HIGH_STAKES: frozenset[ClauseType] = frozenset(
    {
        ClauseType.UNCAPPED_LIABILITY,
        ClauseType.NON_COMPETE,
        ClauseType.EXCLUSIVITY,
        ClauseType.MOST_FAVORED_NATION,
    }
)


class Decision(str, Enum):
    """Where an intake memo can route. Closed set."""

    SELF_SERVE = "self_serve"
    ATTORNEY_REVIEW = "attorney_review"
    REJECT_COUNTERPARTY_PAPER = "reject_counterparty_paper"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlaybookStatus(str, Enum):
    STANDARD = "standard"
    NON_STANDARD = "non_standard"
    NOT_APPLICABLE = "not_applicable"


class ContractSummary(BaseModel):
    contract_id: str
    filename: str
    size_bytes: int
    est_tokens: int = Field(description="rough size/4 estimate — decide paging before reading")


class ContractPage(BaseModel):
    contract_id: str
    page: int
    total_pages: int
    text: str


class ClauseWindow(BaseModel):
    """A deterministic retrieval hit: cue pattern + surrounding context."""

    start_char: int
    end_char: int
    matched_cue: str
    text: str


class ClauseSearchResult(BaseModel):
    contract_id: str
    clause_type: ClauseType
    windows: list[ClauseWindow]
    est_tokens: int
    note: str = Field(
        default="",
        description="set when no cue fired — absence of cues is evidence, not proof, of absence",
    )


class SpanVerification(BaseModel):
    """The anti-hallucination primitive. found=True only for a verbatim
    (whitespace-normalized) match; otherwise similarity reports how close
    the nearest region of the document comes."""

    contract_id: str
    found: bool
    similarity: float = Field(ge=0.0, le=1.0)
    best_match: str = Field(default="", description="closest document text, for diagnosis")


class PlaybookStandard(BaseModel):
    clause_type: ClauseType
    standard: str
    escalation_rule: str
    high_stakes: bool


class FieldJudgment(BaseModel):
    clause_type: ClauseType
    present: bool
    quote: str = Field(default="", description="verbatim span; required when present=True")
    confidence: Confidence
    playbook_status: PlaybookStatus
    escalate: bool
    escalation_reasons: list[str] = Field(default_factory=list)


class IntakeMemo(BaseModel):
    contract_id: str
    reviewed_by: str = Field(description="role, e.g. 'paralegal'")
    fields: list[FieldJudgment]
    decision: Decision
    decision_basis: str
