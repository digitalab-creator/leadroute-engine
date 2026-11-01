"""The one status function. Exclusions run in the order the standard gives."""

from dataclasses import dataclass
from datetime import datetime

from app.constants import (
    APAC_OWNER,
    FOUNDERS_OWNER,
    NO_DRAFT_STATUSES,
    REGION_OWNERS,
    TRIAGE_OWNER,
    Intent,
    Status,
)
from app.pipeline.evaluate import Conditions, GateInput, evaluate_conditions
from app.pipeline.score import Score, score_lead


@dataclass(frozen=True)
class Decision:
    status: Status
    owner: str | None
    score: Score
    conditions: Conditions
    rationale: str
    draft_allowed: bool
    expansion: bool
    qualified: bool

    @property
    def band(self) -> str:
        return self.score.band


def is_preexisting_deal(
    deal_created: datetime | None,
    first_inbound: datetime | None,
    accepted_at: datetime | None,
) -> bool:
    """True only when the deal was opened before the first inbound and before acceptance.

    A deal opened after acceptance is the outcome of the lead, not a reason to exclude it.
    No deal means this rule does not apply.
    """
    if deal_created is None:
        return False
    before_inbound = first_inbound is None or deal_created < first_inbound
    before_acceptance = accepted_at is None or deal_created < accepted_at
    return before_inbound and before_acceptance


def _is_investor(facts: GateInput) -> bool:
    return facts.is_investor or facts.intent == Intent.INVESTOR


def _is_disqualified_kind(facts: GateInput) -> bool:
    if facts.is_competitor or facts.is_vendor:
        return True
    if facts.intent in {Intent.JOB_SEEKER, Intent.AUTO_REPLY}:
        return True
    return facts.role_level == "student"


def _region_owner(region: str | None) -> str:
    if region is None:
        return TRIAGE_OWNER
    if region == "apac":
        return APAC_OWNER
    return REGION_OWNERS.get(region, TRIAGE_OWNER)


def owner_for(status: Status, facts: GateInput) -> str | None:
    if status is Status.DISQUALIFIED:
        return None
    investor = _is_investor(facts)
    account = facts.is_customer or facts.preexisting_deal
    if status is Status.EXCLUDED and investor and not account:
        return FOUNDERS_OWNER
    if facts.crm_owner:
        return facts.crm_owner
    return _region_owner(facts.region)


def _rationale(status: Status, conditions: Conditions) -> str:
    if status is Status.NEEDS_REVIEW:
        return "The analysis did not finish cleanly, so a person needs to decide."
    if status is Status.SUPPRESSED:
        return "They asked to be removed. No outreach is drafted."
    if status is Status.EXCLUDED:
        return "This is an existing account, an older open deal, or an investor."
    if status is Status.DISQUALIFIED:
        return "Competitor, vendor, job seeker, student, or an auto-reply."
    if status is Status.QL:
        return "All five QL conditions hold."
    if status is Status.QL_CANDIDATE:
        return "Fit, buyer, problem, and interest hold. Sales has not accepted yet."
    failed = [
        name
        for name, item in (
            ("company fit", conditions.icp),
            ("buyer", conditions.buyer),
            ("data problem", conditions.problem),
            ("interest", conditions.interest),
            ("sales acceptance", conditions.acceptance),
        )
        if not item.passed
    ]
    if status is Status.NURTURE and failed:
        return "Not a QL yet. Still open: " + ", ".join(failed) + "."
    return "Not a QL."


def pick_status(facts: GateInput, conditions: Conditions) -> Status:
    """Order is the product rule. The score is not an input, so it cannot promote a lead."""
    if facts.analysis_failed or facts.injection or facts.deal_unknown:
        return Status.NEEDS_REVIEW
    if facts.intent == Intent.UNSUBSCRIBE:
        return Status.SUPPRESSED
    if facts.is_customer or facts.preexisting_deal:
        return Status.EXCLUDED
    if _is_investor(facts):
        return Status.EXCLUDED
    if _is_disqualified_kind(facts):
        return Status.DISQUALIFIED
    if conditions.first_four and conditions.acceptance.passed:
        return Status.QL
    if conditions.first_four:
        return Status.QL_CANDIDATE
    # Missing at least one of the first four conditions. The score band is
    # stored beside this status and is not allowed to change it.
    return Status.NURTURE


def decide(facts: GateInput) -> Decision:
    conditions = evaluate_conditions(facts)
    scored = score_lead(conditions, facts.source)
    status = pick_status(facts, conditions)
    expansion = facts.is_customer or facts.preexisting_deal
    return Decision(
        status=status,
        owner=owner_for(status, facts),
        score=scored,
        conditions=conditions,
        rationale=_rationale(status, conditions),
        draft_allowed=status not in NO_DRAFT_STATUSES,
        expansion=expansion,
        qualified=status is Status.QL,
    )
