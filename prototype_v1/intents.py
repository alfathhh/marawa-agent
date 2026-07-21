from dataclasses import dataclass, field
from enum import Enum

from .guardrails import canonical
from .templates import render


class Intent(str, Enum):
    DATA_SEARCH = "DATA_SEARCH"
    DEFINITION = "DEFINITION"
    PST_SERVICE = "PST_SERVICE"
    ADMIN_REQUEST = "ADMIN_REQUEST"
    GENERAL_GREETING = "GENERAL_GREETING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    CLARIFICATION = "CLARIFICATION"


@dataclass(frozen=True)
class IntentResult:
    intents: tuple[Intent, ...]
    reply: str | None = None


@dataclass
class ProviderMock:
    calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def call(self, tool: str, arguments: dict[str, object]) -> None:
        self.calls.append((tool, arguments))


_SECRET_TERMS = ("prompt", "api key", "credential", "config", "raw trace", "jejak tool")
_OUTSIDE_REGIONS = ("kota pariaman", "kota padang", "sumatera barat", "indonesia")


def route_intents(text: str, provider: ProviderMock) -> IntentResult:
    query = canonical(text)
    if any(term in query for term in _SECRET_TERMS):
        return IntentResult((Intent.OUT_OF_SCOPE,), render("SECRET_REFUSAL"))
    if "data" in query and any(region in query for region in _OUTSIDE_REGIONS):
        return IntentResult((Intent.OUT_OF_SCOPE,), render("OUT_OF_SCOPE_REGION"))
    if query in {"halo", "hai", "selamat pagi"}:
        return IntentResult(
            (Intent.GENERAL_GREETING,),
            "Saya Marawa, asisten virtual. Saya dapat membantu mencari data, konsep "
            "statistik, atau layanan PST.",
        )
    if query in {"data", "saya butuh data"}:
        return IntentResult(
            (Intent.DATA_SEARCH,), "Topik atau indikator data apa yang Kakak perlukan?"
        )

    intents: list[Intent] = []
    if "data" in query:
        intents.append(Intent.DATA_SEARCH)
        provider.call(
            "bps_search_catalogs",
            {"keyword": _data_keyword(query), "page": 1},
        )
    if "konsultasi" in query or "layanan" in query:
        intents.append(Intent.PST_SERVICE)
        provider.call(
            "kb_search",
            {"query": "konsultasi" if "konsultasi" in query else "layanan"},
        )
    if query.startswith("apa arti") or "definisi" in query:
        intents.append(Intent.DEFINITION)
        provider.call("glossary_search", {"query": _definition_query(query)})
    if "admin" in query or "petugas" in query:
        intents.append(Intent.ADMIN_REQUEST)
        provider.call("mock_handover", {"action": "offer_admin"})
    if intents:
        return IntentResult(tuple(intents))
    return IntentResult(
        (Intent.CLARIFICATION,),
        "Apakah Kakak memerlukan data, konsep statistik, atau layanan PST?",
    )


def _data_keyword(query: str) -> str:
    after_data = query.split("data", 1)[1].strip()
    return after_data.split(" dan ", 1)[0].strip()


def _definition_query(query: str) -> str:
    if query.startswith("apa arti"):
        query = query.removeprefix("apa arti").strip()
    return query.removeprefix("konsep ").rstrip("?").strip()
