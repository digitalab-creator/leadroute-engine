"""Combine every message from one person. One bad message does not erase a good one.

An unsubscribe, a job seeker, or an injection on any message sticks.
"""

from datetime import datetime

from app.constants import Intent
from app.pipeline.extract import ExtractOutcome
from app.pipeline.facts import MergedSignal

_STICKY = {Intent.UNSUBSCRIBE, Intent.JOB_SEEKER, Intent.INVESTOR}


def _mode(outcomes: list[ExtractOutcome], failed: bool) -> str:
    if not outcomes:
        return "none"
    if failed:
        if any(item.mode == "failed" for item in outcomes):
            return "failed"
        if any(item.mode == "rules" for item in outcomes):
            return "rules"
        return "failed"
    modes = [item.mode for item in outcomes if not item.failed]
    if modes and all(mode == "fixture" for mode in modes):
        return "fixture"
    if "gemini" in modes:
        return "gemini"
    if "rules" in modes:
        return "rules"
    return modes[-1] if modes else "none"


def merge_outcomes(items: list[tuple[datetime, ExtractOutcome]]) -> MergedSignal:
    if not items:
        from app.pipeline.facts import empty_signal

        return empty_signal()

    ordered = [item for _, item in sorted(items, key=lambda pair: pair[0])]
    injection = any(item.injection for item in ordered)
    usable = [item for item in ordered if not item.failed and item.extraction is not None]
    if not usable:
        return MergedSignal(
            analysis_failed=True,
            injection=injection,
            intent=None,
            role_level=None,
            role_function=None,
            problem=None,
            problem_grounded=False,
            problem_quote=None,
            industry=None,
            employees=None,
            country=None,
            mode=_mode(ordered, failed=True),
        )

    intents = [item.extraction.intent for item in usable if item.extraction is not None]
    sticky = next((intent for intent in intents if intent in _STICKY), None)
    if sticky is not None:
        intent = sticky
    else:
        human = [
            item.extraction.intent
            for item in usable
            if item.extraction is not None and item.extraction.intent is not Intent.AUTO_REPLY
        ]
        intent = human[-1] if human else intents[-1]

    problem = None
    problem_quote = None
    role_level = None
    industry = None
    employees = None
    country = None
    for item in usable:
        extraction = item.extraction
        if extraction is None:
            continue
        if extraction.stated_problem is not None and extraction.stated_problem_quote:
            problem = extraction.stated_problem.value
            problem_quote = extraction.stated_problem_quote
        if extraction.stated_role is not None:
            role_level = extraction.stated_role.value
        if extraction.stated_industry is not None:
            industry = extraction.stated_industry.value
        if extraction.stated_employees is not None:
            employees = extraction.stated_employees
        if extraction.stated_country is not None:
            country = extraction.stated_country
    if any(
        item.extraction is not None and item.extraction.stated_role is not None
        and item.extraction.stated_role.value == "student"
        for item in usable
    ):
        role_level = "student"

    return MergedSignal(
        analysis_failed=False,
        injection=injection,
        intent=intent.value,
        role_level=role_level,
        role_function=None,
        problem=problem,
        problem_grounded=problem is not None,
        problem_quote=problem_quote,
        industry=industry,
        employees=employees,
        country=country,
        mode=_mode(usable, failed=False),
    )
