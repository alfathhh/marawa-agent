import re
from pathlib import Path

from prototype_v1.agent_loop import (
    DEADLINE_SECONDS,
    MAX_DUPLICATES,
    MAX_MODEL_REQUESTS,
    MAX_TOOL_EXECUTIONS,
)
from prototype_v1.guardrails import DOMAIN
from prototype_v1.templates import TEMPLATES

ROOT = Path(__file__).parents[2]
SPECS = [
    "FEATURES.md", "PRD.md", "ARCHITECTURE.md", "DATABASE.md", "API-SPEC.md",
    "AGENT.md", "TEST-SCENARIOS.md", "DECISIONS.md", "TASKS.md", "README.md",
]


def text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_normative_spec_inventory_exists_and_readme_orders_every_document():
    readme = text("README.md")

    assert all((ROOT / name).is_file() for name in SPECS)
    numbered = re.findall(r"^\d+\. \*\*([^*]+)\*\*", readme, re.M)
    assert numbered[:9] == [
        "FEATURES.md", "PRD.md", "DECISIONS.md", "ARCHITECTURE.md", "DATABASE.md",
        "API-SPEC.md", "AGENT.md", "TEST-SCENARIOS.md", "TASKS.md",
    ]


def test_test_scenario_spec_has_exact_contiguous_inventory_and_matching_matrix():
    scenarios = text("TEST-SCENARIOS.md")
    headings = re.findall(r"^#### (SC-\d{3}) —", scenarios, re.M)

    assert headings == [f"SC-{number:03d}" for number in range(1, 81)]
    assert "**Total** | **SC-001–SC-080** | **80**" in scenarios


def test_domain_and_loop_budgets_match_all_normative_specs():
    agent, architecture, scenarios = map(text, ("AGENT.md", "ARCHITECTURE.md", "TEST-SCENARIOS.md"))

    assert DOMAIN == "1306"
    assert all("`1306`" in document for document in (agent, architecture, scenarios))
    assert (MAX_MODEL_REQUESTS, MAX_TOOL_EXECUTIONS, MAX_DUPLICATES, DEADLINE_SECONDS) == (6, 10, 2, 120)
    architecture = text("ARCHITECTURE.md")
    assert all(token in architecture for token in ("6", "10", "2", "120"))


def test_exact_agent_templates_match_the_normative_template_section():
    agent = text("AGENT.md")

    assert all(value in agent for value in TEMPLATES.values())
    assert len(TEMPLATES) == 10


def test_api_and_agent_tool_names_are_closed_and_consistent():
    expected = {
        "bps_search_catalogs", "bps_list_periods", "bps_get_selected_data",
        "glossary_search", "kb_search", "compare_verified_rows", "mock_handover",
    }
    api, agent = text("API-SPEC.md"), text("AGENT.md")
    api_tools = set(re.findall(r"^### 4\.\d `([^`]+)`", api, re.M))
    agent_tools = set(re.findall(r"^\| `([^`]+)` \|", agent, re.M)) & expected

    assert api_tools == expected
    assert agent_tools == expected


def test_unresolved_gates_remain_explicit_and_are_not_marked_complete():
    tasks, decisions = text("TASKS.md"), text("DECISIONS.md")

    assert "- [x] **6.3" in tasks
    assert "- [ ] **6.4" in tasks and "- [ ] **6.8" in tasks
    assert "BELUM TERJAWAB" in tasks
    assert "belum direkomendasikan ke fase 2" in tasks
    assert "Glosarium" in decisions and "HTTP 500" in decisions


def test_scope_exclusions_are_normatively_documented():
    corpus = "\n".join(text(name) for name in ("FEATURES.md", "PRD.md", "ARCHITECTURE.md"))

    assert all(term.casefold() in corpus.casefold() for term in ("WhatsApp", "dashboard", "database", "SIRuSa"))
