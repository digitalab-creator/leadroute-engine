"""The QL gate. One function, in a fixed order. The score cannot promote a lead."""

from dataclasses import replace
from datetime import datetime

from app.clock import JERUSALEM
from app.pipeline.evaluate import GateInput, evaluate_conditions
from app.pipeline.facts import PersonProfile, build_gate_input, empty_signal
from app.pipeline.facts import MergedSignal
from app.pipeline.gate import decide, is_preexisting_deal
from app.pipeline.quotes import extraction_is_grounded
from app.pipeline.schemas import Extraction, WriterOutput
from app.pipeline.score import score_lead

import pytest


def facts(**overrides: object) -> GateInput:
    base = GateInput(
        analysis_failed=False,
        injection=False,
        intent="demo",
        industry="freight_forwarder",
        employees=100,
        region="benelux",
        role_level="head",
        role_function="pricing",
        problem="rate_quoting",
        problem_grounded=True,
        accepted=True,
        is_customer=False,
        preexisting_deal=False,
        deal_unknown=False,
        is_competitor=False,
        is_vendor=False,
        is_investor=False,
        crm_owner="Dana",
        source="event-email",
    )
    return replace(base, **overrides)


def test_all_five_conditions_are_a_ql() -> None:
    decision = decide(facts())
    assert decision.status == "QL"
    assert decision.qualified is True
    assert decision.owner == "Dana"
    assert decision.score.total == 25 + 20 + 25 + 20 + 8
    assert decision.band == "A"
    assert decision.draft_allowed is True


def test_without_acceptance_the_lead_is_only_a_candidate() -> None:
    decision = decide(facts(accepted=False))
    assert decision.status == "QL candidate"
    assert decision.qualified is False


def test_acceptance_does_not_repair_a_failed_condition() -> None:
    decision = decide(facts(industry=None))
    assert decision.status != "QL"
    assert decision.status != "QL candidate"
    assert decision.conditions.icp.passed is False
    assert decision.conditions.acceptance.passed is True


def test_a_high_score_does_not_override_the_gate() -> None:
    decision = decide(facts(industry=None, source="warm-network"))
    assert decision.score.total >= 70
    assert decision.band == "A"
    assert decision.status != "QL"
    assert decision.status == "nurture"


def test_low_score_real_lead_is_nurture() -> None:
    decision = decide(
        facts(
            intent="not interested",
            problem=None,
            problem_grounded=False,
            accepted=False,
            role_level=None,
            role_function=None,
            industry=None,
            employees=None,
            region=None,
            source=None,
        )
    )
    assert decision.score.total < 40
    assert decision.band == "nurture"
    assert decision.status == "nurture"


def test_injection_is_needs_review_and_keeps_an_owner() -> None:
    decision = decide(facts(injection=True, intent="demo"))
    assert decision.status == "needs review"
    assert decision.status != "QL"
    assert decision.status != "disqualified"
    assert decision.owner == "Dana"
    assert decision.draft_allowed is False
    assert decision.conditions.interest.passed is False


def test_failed_analysis_is_needs_review_even_when_sales_accepted() -> None:
    decision = decide(facts(analysis_failed=True))
    assert decision.status == "needs review"
    assert decision.qualified is False
    assert decision.conditions.problem.passed is False


def test_unsubscribe_is_suppressed_and_has_no_draft() -> None:
    decision = decide(facts(intent="unsubscribe"))
    assert decision.status == "suppressed"
    assert decision.draft_allowed is False


def test_customer_is_excluded_and_keeps_the_crm_owner() -> None:
    decision = decide(facts(is_customer=True))
    assert decision.status == "excluded"
    assert decision.owner == "Dana"
    assert decision.expansion is True
    assert decision.draft_allowed is False
    assert decision.status != "QL"


def test_investor_goes_to_founders_even_with_a_region_owner() -> None:
    decision = decide(facts(is_investor=True, crm_owner=None, region="united_states"))
    assert decision.status == "excluded"
    assert decision.owner == "Founders"


def test_auto_reply_job_seeker_and_competitor_have_no_owner() -> None:
    auto = decide(facts(intent="auto-reply"))
    student = decide(facts(intent="job seeker", role_level="student"))
    rival = decide(facts(is_competitor=True, intent="demo"))
    assert auto.status == "disqualified" and auto.owner is None
    assert student.status == "disqualified" and student.owner is None
    assert rival.status == "disqualified" and rival.owner is None
    assert auto.draft_allowed is False


def test_unknown_size_fails_icp_and_boundaries_are_exact() -> None:
    assert evaluate_conditions(facts(employees=None)).icp.passed is False
    assert evaluate_conditions(facts(employees=19)).icp.passed is False
    assert evaluate_conditions(facts(employees=20)).icp.passed is True
    assert evaluate_conditions(facts(industry=None)).icp.passed is False
    assert evaluate_conditions(facts(region="apac")).icp.passed is False


def test_buyer_rules() -> None:
    assert evaluate_conditions(facts(role_level="manager", role_function="operations")).buyer.passed
    assert not evaluate_conditions(
        facts(role_level="team_lead", role_function="operations")
    ).buyer.passed
    assert evaluate_conditions(
        facts(role_level="owner_founder", role_function=None, employees=199)
    ).buyer.passed
    assert not evaluate_conditions(
        facts(role_level="owner_founder", role_function=None, employees=200)
    ).buyer.passed
    assert not evaluate_conditions(
        facts(role_level="manager", role_function="other")
    ).buyer.passed


def test_deal_timing() -> None:
    inbound = datetime(2026, 10, 6, 9, 0, tzinfo=JERUSALEM)
    accepted = datetime(2026, 9, 24, 12, 0, tzinfo=JERUSALEM)
    before = datetime(2026, 8, 19, tzinfo=JERUSALEM)
    after_accept = datetime(2026, 10, 7, tzinfo=JERUSALEM)
    assert is_preexisting_deal(before, inbound, None) is True
    assert is_preexisting_deal(after_accept, None, accepted) is False
    assert is_preexisting_deal(None, inbound, accepted) is False


def test_a_crm_title_is_not_overwritten_by_the_message() -> None:
    profile = PersonProfile(
        title="Customer Service Team Lead",
        industry="carrier",
        employees=2200,
        country="BE",
        is_customer=False,
        customer_unreadable=False,
        crm_owner="Dana",
        open_deal_created=None,
        deal_unreadable=False,
        account_kind="icp",
        lead_status=None,
    )
    signal = replace(
        empty_signal(),
        intent="demo",
        role_level="owner_founder",
        problem="rate_quoting",
        problem_grounded=True,
        mode="rules",
    )
    built = build_gate_input(
        profile,
        signal,
        accepted=True,
        accepted_at=datetime(2026, 10, 6, tzinfo=JERUSALEM),
        first_inbound=datetime(2026, 10, 5, tzinfo=JERUSALEM),
        source="event-email",
    )
    decision = decide(built)
    assert built.role_level == "team_lead"
    assert decision.status != "QL"


def test_stated_facts_fill_a_blank_profile() -> None:
    profile = PersonProfile(
        title=None,
        industry=None,
        employees=None,
        country=None,
        is_customer=False,
        customer_unreadable=False,
        crm_owner=None,
        open_deal_created=None,
        deal_unreadable=False,
        account_kind="unknown",
        lead_status=None,
    )
    signal = MergedSignal(
        analysis_failed=False,
        injection=False,
        intent="pricing",
        role_level="owner_founder",
        role_function=None,
        problem="document_extraction",
        problem_grounded=True,
        problem_quote="import declarations",
        industry="customs_broker",
        employees=40,
        country="IL",
        mode="fixture",
    )
    built = build_gate_input(
        profile,
        signal,
        accepted=True,
        accepted_at=datetime(2026, 10, 7, 15, tzinfo=JERUSALEM),
        first_inbound=datetime(2026, 10, 6, 16, tzinfo=JERUSALEM),
        source="organic/referral",
    )
    assert decide(built).status == "QL"
    assert decide(built).owner == "Noa"


def test_a_quote_must_be_in_the_message() -> None:
    message = "I would like to see a demo next week."
    good = Extraction(
        language="en",
        intent="demo",
        quotes=["a demo"],
        instruction_override_attempt=False,
    )
    bad = Extraction(
        language="en",
        intent="demo",
        quotes=["a demo that was never said"],
        instruction_override_attempt=False,
    )
    assert extraction_is_grounded(message, good) is True
    assert extraction_is_grounded(message, bad) is False


def test_writer_schema_rejects_a_status_field() -> None:
    with pytest.raises(Exception):
        WriterOutput.model_validate_json(
            '{"rationale": "Sounds useful.", "draft": "Hello", "status": "QL"}'
        )


def test_score_breakdown_matches_the_conditions() -> None:
    scored = score_lead(evaluate_conditions(facts(source="paid")), "paid")
    assert scored.source_warmth == 2
    assert scored.total == scored.icp + scored.buyer + scored.problem + scored.intent + scored.source_warmth
