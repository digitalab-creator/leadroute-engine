"""The five QL conditions. The gate turns these booleans into one status."""

from dataclasses import dataclass

from app.constants import (
    ICP_REGIONS,
    INFLUENCE_FUNCTIONS,
    INTEREST_INTENTS,
    MANAGER_OR_ABOVE,
    MIN_EMPLOYEES,
    OWNER_EMPLOYEES_UNDER,
    Industry,
    Pain,
    RoleLevel,
)


@dataclass(frozen=True)
class GateInput:
    """Facts the gate may use. The raw message is not one of them."""

    analysis_failed: bool
    injection: bool
    intent: str | None
    industry: str | None
    employees: int | None
    region: str | None
    role_level: str | None
    role_function: str | None
    problem: str | None
    problem_grounded: bool
    accepted: bool
    is_customer: bool
    preexisting_deal: bool
    deal_unknown: bool
    is_competitor: bool
    is_vendor: bool
    is_investor: bool
    crm_owner: str | None
    source: str | None


@dataclass(frozen=True)
class Condition:
    passed: bool
    evidence: str


@dataclass(frozen=True)
class Conditions:
    icp: Condition
    buyer: Condition
    problem: Condition
    interest: Condition
    acceptance: Condition

    def as_dict(self) -> dict[str, dict[str, object]]:
        return {
            name: {"passed": item.passed, "evidence": item.evidence}
            for name, item in (
                ("icp", self.icp),
                ("buyer", self.buyer),
                ("problem", self.problem),
                ("interest", self.interest),
                ("acceptance", self.acceptance),
            )
        }

    @property
    def first_four(self) -> bool:
        return (
            self.icp.passed
            and self.buyer.passed
            and self.problem.passed
            and self.interest.passed
        )


def buyer_passes(level: str | None, function: str | None, employees: int | None) -> bool:
    """Manager-or-above in a buying function, or a founder under 200 people."""
    if level == RoleLevel.OWNER_FOUNDER:
        return employees is not None and employees < OWNER_EMPLOYEES_UNDER
    if level not in MANAGER_OR_ABOVE:
        return False
    return function in INFLUENCE_FUNCTIONS


def _icp(facts: GateInput) -> Condition:
    industry_ok = facts.industry in {item.value for item in Industry}
    size_ok = facts.employees is not None and facts.employees >= MIN_EMPLOYEES
    region_ok = facts.region in ICP_REGIONS
    passed = industry_ok and size_ok and region_ok
    parts = [
        f"industry {facts.industry or 'unknown'}",
        f"employees {facts.employees if facts.employees is not None else 'unknown'}",
        f"region {facts.region or 'unknown'}",
    ]
    return Condition(passed, ", ".join(parts))


def _buyer(facts: GateInput) -> Condition:
    passed = buyer_passes(facts.role_level, facts.role_function, facts.employees)
    if facts.role_level is None:
        return Condition(False, "Role is unknown")
    function = facts.role_function or "unknown"
    return Condition(passed, f"role {facts.role_level} / {function}")


def evaluate_conditions(facts: GateInput) -> Conditions:
    """Problem and interest need a trusted read. A failed model call gets neither."""
    trust_message = not facts.analysis_failed and not facts.injection

    if not trust_message:
        problem = Condition(False, "Message was not trusted")
        interest = Condition(False, "Message was not trusted")
    else:
        pain_ok = facts.problem in {item.value for item in Pain} and facts.problem_grounded
        problem = Condition(
            pain_ok,
            f"pain {facts.problem}" if pain_ok else "No grounded data problem",
        )
        intent_ok = facts.intent in {item.value for item in INTEREST_INTENTS}
        interest = Condition(
            intent_ok,
            f"intent {facts.intent}" if intent_ok else "No expressed interest",
        )

    acceptance = Condition(
        facts.accepted,
        "Sales acceptance is on record" if facts.accepted else "No sales acceptance",
    )
    return Conditions(
        icp=_icp(facts),
        buyer=_buyer(facts),
        problem=problem,
        interest=interest,
        acceptance=acceptance,
    )
