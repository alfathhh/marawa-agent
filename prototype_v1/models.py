from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    role: str
    content: str
    message_id: str
    created_at: datetime
    provenance_refs: list[str] = field(default_factory=list)

    def __post_init__(self):
        limits = {"user": 8000, "assistant": 12000, "tool": 20000}
        if self.role not in limits or not isinstance(self.content, str) or len(self.content) > limits[self.role]:
            raise ValueError("invalid_message")


@dataclass
class Candidate:
    code: str
    source_family: str
    source_identifier: str
    title: str
    url: str
    subject: str | None = None
    periods: list[str] = field(default_factory=list)
    abstract: str | None = None
    page_offered: int = 1


@dataclass
class PeriodOption:
    value: str
    upstream_id: str
    label: str


@dataclass
class SearchFrame:
    search_id: str
    query: str
    canonical_query: str
    page: int = 1
    candidates: dict[str, Candidate] = field(default_factory=dict)
    selected_code: str | None = None
    offered_periods: list[PeriodOption] = field(default_factory=list)
    selected_period: str | None = None
    verified_rows: dict[str, Any] = field(default_factory=dict)

    def resolve_candidate(self, code, handler):
        candidate = self.candidates.get(code)
        if candidate is None:
            return {"error": {"code": "candidate_not_found"}}
        return handler(candidate)


@dataclass
class SessionState:
    session_id: str
    server_generation: str
    created_at: datetime
    last_active_at: datetime
    state_version: int = 0
    messages: list[Message] = field(default_factory=list)
    frame: SearchFrame | None = None
    pending_topic: str | None = None
    response_cache: dict[str, dict] = field(default_factory=dict)
    lock: Any = None
    turn_timestamps: list[float] = field(default_factory=list)
