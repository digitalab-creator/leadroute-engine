"""Run the labelled qualifier eval set. No LLM — gate + merge only."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.clock import JERUSALEM, parse_timestamp
from app.pipeline.facts import MergedSignal, PersonProfile, build_gate_input
from app.pipeline.gate import decide


class EvalExpected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    qualified: bool
    owner: str | None = None


class EvalSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_failed: bool = False
    injection: bool = False
    intent: str | None = None
    role_level: str | None = None
    role_function: str | None = None
    problem: str | None = None
    problem_grounded: bool = False
    problem_quote: str | None = None
    industry: str | None = None
    employees: int | None = None
    country: str | None = None
    mode: str = "eval"


class EvalProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    industry: str | None = None
    employees: int | None = None
    country: str | None = None
    is_customer: bool = False
    customer_unreadable: bool = False
    crm_owner: str | None = None
    open_deal_created: str | None = None
    deal_unreadable: bool = False
    account_kind: str = "unknown"
    lead_status: str | None = None


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    standard: str = Field(min_length=1)
    accepted: bool
    source: str | None = None
    accepted_at: str | None = None
    first_inbound: str | None = None
    profile: EvalProfile
    signal: EvalSignal
    expected: EvalExpected


class EvalFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    description: str
    cases: list[EvalCase] = Field(min_length=1)


def _optional_ts(raw: str | None) -> datetime | None:
    if raw is None or not str(raw).strip():
        return None
    return parse_timestamp(str(raw).strip())


def _profile(row: EvalProfile) -> PersonProfile:
    deal = _optional_ts(row.open_deal_created)
    return PersonProfile(
        title=row.title,
        industry=row.industry,
        employees=row.employees,
        country=row.country,
        is_customer=row.is_customer,
        customer_unreadable=row.customer_unreadable,
        crm_owner=row.crm_owner,
        open_deal_created=deal,
        deal_unreadable=row.deal_unreadable,
        account_kind=row.account_kind,
        lead_status=row.lead_status,
    )


def _signal(row: EvalSignal) -> MergedSignal:
    return MergedSignal(
        analysis_failed=row.analysis_failed,
        injection=row.injection,
        intent=row.intent,
        role_level=row.role_level,
        role_function=row.role_function,
        problem=row.problem,
        problem_grounded=row.problem_grounded,
        problem_quote=row.problem_quote,
        industry=row.industry,
        employees=row.employees,
        country=row.country,
        mode=row.mode,
    )


def load_eval_file(path: Path) -> EvalFile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return EvalFile.model_validate(raw)


def run_case(case: EvalCase) -> dict[str, Any]:
    accepted_at = _optional_ts(case.accepted_at)
    first_inbound = _optional_ts(case.first_inbound)
    gate_in = build_gate_input(
        _profile(case.profile),
        _signal(case.signal),
        accepted=case.accepted,
        accepted_at=accepted_at,
        first_inbound=first_inbound,
        source=case.source,
    )
    decision = decide(gate_in)
    actual_status = decision.status.value
    actual_owner = decision.owner
    expected = case.expected
    status_ok = actual_status == expected.status
    qualified_ok = decision.qualified is expected.qualified
    owner_ok = True
    if expected.owner is not None:
        owner_ok = actual_owner == expected.owner
    passed = status_ok and qualified_ok and owner_ok
    return {
        "id": case.id,
        "title": case.title,
        "standard": case.standard,
        "pass": passed,
        "expected_status": expected.status,
        "actual_status": actual_status,
        "expected_qualified": expected.qualified,
        "actual_qualified": decision.qualified,
        "expected_owner": expected.owner,
        "actual_owner": actual_owner,
    }


def run_qualifier_eval(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "qualifier_eval.json"
    if not path.is_file():
        raise FileNotFoundError("qualifier_eval.json is missing from the data pack")
    document = load_eval_file(path)
    results = [run_case(case) for case in document.cases]
    passed = sum(1 for row in results if row["pass"])
    total = len(results)
    accuracy = round(100.0 * passed / total, 2) if total else 0.0
    return {
        "eval_file": "data/qualifier_eval.json",
        "version": document.version,
        "description": document.description,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy_pct": accuracy,
        "all_pass": passed == total,
        "results": results,
        "run_at": datetime.now(JERUSALEM).isoformat(timespec="seconds"),
    }


def run_qualifier_eval_from_path(path: Path) -> dict[str, Any]:
    document = load_eval_file(path)
    results = [run_case(case) for case in document.cases]
    passed = sum(1 for row in results if row["pass"])
    total = len(results)
    accuracy = round(100.0 * passed / total, 2) if total else 0.0
    return {
        "eval_file": str(path),
        "version": document.version,
        "description": document.description,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy_pct": accuracy,
        "all_pass": passed == total,
        "results": results,
        "run_at": datetime.now(JERUSALEM).isoformat(timespec="seconds"),
    }
