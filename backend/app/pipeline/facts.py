"""Build the gate's input from a CRM profile plus a trusted extraction.

CRM values fill first. A message can fill a blank. It cannot overwrite a title.
"""

from dataclasses import dataclass
from datetime import datetime

from app.constants import AccountKind, RoleFunction, RoleLevel
from app.pipeline.evaluate import GateInput
from app.pipeline.gate import is_preexisting_deal
from app.pipeline.lexicon import function_for_role, region_for_country
from app.pipeline.titles import resolve_title


@dataclass(frozen=True)
class PersonProfile:
    title: str | None
    industry: str | None
    employees: int | None
    country: str | None
    is_customer: bool | None
    customer_unreadable: bool
    crm_owner: str | None
    open_deal_created: datetime | None
    deal_unreadable: bool
    account_kind: str
    lead_status: str | None


@dataclass(frozen=True)
class MergedSignal:
    analysis_failed: bool
    injection: bool
    intent: str | None
    role_level: str | None
    role_function: str | None
    problem: str | None
    problem_grounded: bool
    problem_quote: str | None
    industry: str | None
    employees: int | None
    country: str | None
    mode: str


def _function_value(role_level: str) -> str | None:
    try:
        level = RoleLevel(role_level)
    except ValueError:
        return None
    function = function_for_role(level)
    if function is None:
        return None
    return function.value


def empty_signal() -> MergedSignal:
    """A person with no inbound. That is not a model failure."""
    return MergedSignal(
        analysis_failed=False,
        injection=False,
        intent=None,
        role_level=None,
        role_function=None,
        problem=None,
        problem_grounded=False,
        problem_quote=None,
        industry=None,
        employees=None,
        country=None,
        mode="none",
    )


def build_gate_input(
    profile: PersonProfile,
    signal: MergedSignal,
    *,
    accepted: bool,
    accepted_at: datetime | None,
    first_inbound: datetime | None,
    source: str | None,
) -> GateInput:
    trust_message = not signal.analysis_failed and not signal.injection
    has_crm_title = bool(profile.title and profile.title.strip())
    role_level: str | None
    role_function: str | None
    if has_crm_title:
        level, function = resolve_title(profile.title)
        role_level = None if level is None else level.value
        role_function = None if function is None else function.value
    elif trust_message and signal.role_level:
        role_level = signal.role_level
        role_function = signal.role_function or _function_value(signal.role_level)
    else:
        role_level, role_function = None, None

    if role_level == RoleLevel.OWNER_FOUNDER and role_function is None:
        role_function = RoleFunction.GENERAL_MANAGEMENT

    industry = profile.industry
    employees = profile.employees
    country = profile.country
    if trust_message:
        if industry is None:
            industry = signal.industry
        if employees is None:
            employees = signal.employees
        if country is None:
            country = signal.country

    lead_status = (profile.lead_status or "").strip().casefold()
    competitor = lead_status == "competitor" or profile.account_kind == AccountKind.SOFTWARE_VENDOR
    return GateInput(
        analysis_failed=signal.analysis_failed,
        injection=signal.injection,
        intent=None if not trust_message else signal.intent,
        industry=industry,
        employees=employees,
        region=region_for_country(country),
        role_level=None if role_level is None else str(role_level),
        role_function=None if role_function is None else str(role_function),
        problem=signal.problem if trust_message else None,
        problem_grounded=signal.problem_grounded if trust_message else False,
        accepted=accepted,
        is_customer=bool(profile.is_customer),
        preexisting_deal=is_preexisting_deal(
            profile.open_deal_created, first_inbound, accepted_at
        ),
        deal_unknown=profile.deal_unreadable
        or profile.customer_unreadable
        or profile.is_customer is None,
        is_competitor=competitor,
        is_vendor=profile.account_kind == AccountKind.SOFTWARE_VENDOR,
        is_investor=profile.account_kind == AccountKind.INVESTOR,
        crm_owner=profile.crm_owner,
        source=source,
    )
