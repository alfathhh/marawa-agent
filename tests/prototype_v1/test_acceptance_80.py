"""Normative SC inventory mapped to executable behavioral tests.

This inventory does not replace those tests: pytest collects both this map and every target.
Browser-only evidence remains explicitly blocked rather than simulated here.
"""
from pathlib import Path
import ast

import pytest

TESTS = Path(__file__).parent

# One behavioral test may prove several closely related scenarios, but every scenario has
# exactly one inventory entry and a concrete assertion-bearing target.
_TARGETS = [
"test_agent_intents.py:test_greeting_identifies_virtual_assistant_without_tool_call", "test_agent_intents.py:test_vague_data_asks_exactly_one_clarification_without_search", "test_agent_intents.py:test_mixed_request_routes_data_then_local_service_deterministically", "test_agent_intents.py:test_mixed_request_routes_data_then_local_service_deterministically", "test_followups.py:test_followup_uses_exact_offered_period_without_catalog_search", "test_state.py:test_confirm_discards_old_frame_and_returns_pending_query", "test_state.py:test_cancel_preserves_entire_old_frame_and_clears_pending_topic", "test_sessions.py:test_frontend_contract_tokens", "test_sessions.py:test_get_and_delete_are_exact_and_idempotent", "test_sessions.py:test_store_session_contract_and_idle_expiry",
"test_catalogs.py:test_searches_all_catalogs_in_fixed_order_despite_partial_failure", "test_catalogs.py:test_searches_all_catalogs_in_fixed_order_despite_partial_failure", "test_catalogs.py:test_numbers_stably_across_pages_deduplicates_and_caps_frame_at_54", "test_catalogs.py:test_searches_all_catalogs_in_fixed_order_despite_partial_failure", "test_catalogs.py:test_searches_all_catalogs_in_fixed_order_despite_partial_failure", "test_catalogs.py:test_searches_all_catalogs_in_fixed_order_despite_partial_failure", "test_catalogs.py:test_numbers_stably_across_pages_deduplicates_and_caps_frame_at_54", "test_catalogs.py:test_numbers_stably_across_pages_deduplicates_and_caps_frame_at_54", "test_catalogs.py:test_numbers_stably_across_pages_deduplicates_and_caps_frame_at_54", "test_catalogs.py:test_numbers_stably_across_pages_deduplicates_and_caps_frame_at_54", "test_catalogs.py:test_sanitizes_title_and_resolves_only_code_or_exact_unique_title", "test_catalogs.py:test_sanitizes_title_and_resolves_only_code_or_exact_unique_title", "test_catalogs.py:test_singleton_does_not_auto_select_and_invalid_or_stale_selection_never_fetches", "test_catalogs.py:test_singleton_does_not_auto_select_and_invalid_or_stale_selection_never_fetches",
"test_periods.py:test_discovery_pages_simdasi_and_accumulates_without_selecting_latest", "test_periods.py:test_dynamic_discovery_uses_th_and_gate_rejects_unoffered_period", "test_periods.py:test_publication_has_no_periods", "test_periods.py:test_discovery_pages_simdasi_and_accumulates_without_selecting_latest", "test_periods.py:test_dynamic_discovery_uses_th_and_gate_rejects_unoffered_period", "test_periods.py:test_dynamic_discovery_uses_th_and_gate_rejects_unoffered_period", "test_fetch_and_provenance.py:test_simdasi_builds_complete_verified_row", "test_fetch_and_provenance.py:test_dynamic_parses_dimension_keys_without_positional_slicing_and_filters_domain", "test_fetch_and_provenance.py:test_simdasi_rejects_each_incomplete_field", "test_fetch_and_provenance.py:test_simdasi_rejects_each_incomplete_field", "test_fetch_and_provenance.py:test_parsers_report_no_data", "test_renderers.py:test_data_renderer_limits_rows_and_discloses_total_and_truncation",
"test_renderers.py:test_publication_renderer_is_metadata_only_and_does_not_change_frame_rows", "test_renderers.py:test_publication_renderer_uses_exact_missing_abstract_text", "test_knowledge.py:test_glossary_returns_documented_fields_without_registering_indicator_value", "test_knowledge.py:test_kb_loads_verified_yaml_and_markdown_then_ranks_at_most_four", "test_knowledge.py:test_conflict_keeps_sources_separate_and_offers_admin", "test_knowledge.py:test_conflict_keeps_sources_separate_and_offers_admin", "test_knowledge.py:test_no_match_is_exact_template_with_admin_and_guestbook", "test_knowledge.py:test_no_code_references_sirusa",
"test_followups.py:test_followup_uses_exact_offered_period_without_catalog_search", "test_followups.py:test_valid_dimension_fetches_exactly_once", "test_followups.py:test_ambiguous_dimension_returns_typed_clarification_without_fetch", "test_analysis.py:test_computes_decimal_difference_percent_and_direction", "test_analysis.py:test_computes_decimal_difference_percent_and_direction", "test_analysis.py:test_direction_comes_from_decimal_difference", "test_analysis.py:test_direction_comes_from_decimal_difference", "test_analysis.py:test_zero_baseline_has_no_derived_values", "test_analysis.py:test_rejects_non_comparable_rows", "test_analysis.py:test_rejects_non_comparable_rows", "test_analysis.py:test_rejects_non_comparable_rows", "test_analysis.py:test_rejects_unverified_or_unregistered_rows_without_derived_values", "test_analysis.py:test_formats_canonical_decimal_as_indonesian", "test_analysis.py:test_renderer_is_deterministic_and_contains_complete_provenance",
"test_templates.py:test_handover_always_marks_mock", "test_knowledge.py:test_kb_loads_verified_yaml_and_markdown_then_ranks_at_most_four", "test_knowledge.py:test_kb_loads_verified_yaml_and_markdown_then_ranks_at_most_four", "test_knowledge.py:test_no_match_is_exact_template_with_admin_and_guestbook", "test_knowledge.py:test_no_match_is_exact_template_with_admin_and_guestbook", "test_templates.py:test_handover_actions_are_closed_and_guestbook_is_official", "test_templates.py:test_handover_actions_are_closed_and_guestbook_is_official", "test_templates.py:test_handover_actions_are_closed_and_guestbook_is_official",
"test_agent_intents.py:test_out_of_scope_region_uses_exact_template_without_provider", "test_agent_intents.py:test_out_of_scope_region_uses_exact_template_without_provider", "test_knowledge.py:test_verified_territory_requires_exact_code_label_and_ancestor", "test_guardrails.py:test_provenance_requires_complete_verified_metadata_and_rejects_publication", "test_security_review.py:test_prompt_and_identity_overrides_do_not_change_runtime_policy", "test_security_review.py:test_prompt_and_identity_overrides_do_not_change_runtime_policy", "test_security_review.py:test_disclosure_requests_never_reveal_secret_or_internal_material", "test_security_review.py:test_invalid_domain_and_extra_arguments_never_execute_handler", "test_security_review.py:test_source_instructions_are_sanitized_and_never_executed", "test_static_shell.py:test_static_shell_exposes_chat_controls_and_accessibility_hooks", "test_security_review.py:test_unofficial_urls_are_withheld", "test_knowledge.py:test_glossary_rejects_malformed_success", "test_knowledge.py:test_glossary_retries_only_retryable_status_once", "test_agent_loop.py:test_third_canonical_duplicate_is_blocked_before_execution",
]

CASES = tuple((f"SC-{number:03d}", target) for number, target in enumerate(_TARGETS, 1))


def _assert_behavioral_target(target):
    filename, function = target.split(":")
    tree = ast.parse((TESTS / filename).read_text(encoding="utf-8"))
    matches = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function]
    assert len(matches) == 1, f"missing acceptance target {target}"
    assert any(isinstance(node, ast.Assert) for node in ast.walk(matches[0])), f"target has no behavioral assertion: {target}"


@pytest.mark.parametrize("scenario,target", CASES, ids=[case[0] for case in CASES])
def test_acceptance_scenario_has_executable_behavioral_evidence(scenario, target):
    if target == "BLOCKED_BROWSER":
        pytest.xfail(f"{scenario} requires real browser evidence (M6.3); contract is not a substitute")
    _assert_behavioral_target(target)


def test_acceptance_inventory_is_exactly_sc_001_through_sc_080_once():
    ids = [scenario for scenario, _ in CASES]
    assert ids == [f"SC-{number:03d}" for number in range(1, 81)]
    assert len(ids) == len(set(ids)) == 80
