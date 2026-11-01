"""Read the two seed files. Parsing does not decide who is qualified."""

import csv
import json
from datetime import datetime
from pathlib import Path

from app.clock import parse_timestamp
from app.constants import VERTICAL_MAP, AccountKind
from app.ingest.identity import company_domain_from_email, normalize_email, normalize_linkedin, registered_domain
from app.ingest.records import CrmRow, EventsFile, InboundRecord, PipelineRow, SalesRow
from app.logging_config import get_logger

logger = get_logger()


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def parse_customer(value: str | None) -> tuple[bool | None, bool]:
    """Return (is_customer, unreadable). Blank is unknown, not false."""
    text = _blank(value)
    if text is None:
        return None, False
    folded = text.casefold()
    if folded == "true":
        return True, False
    if folded == "false":
        return False, False
    return None, True


def parse_employees(value: str | None) -> int | None:
    text = _blank(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def map_vertical(value: str | None) -> tuple[str | None, str]:
    text = _blank(value)
    if text is None:
        return None, AccountKind.UNKNOWN.value
    key = "".join(char for char in text.casefold() if char.isalnum())
    mapped = VERTICAL_MAP.get(key)
    if mapped is None:
        return None, AccountKind.UNKNOWN.value
    industry, kind = mapped
    return (None if industry is None else str(industry)), str(kind)


def _domain(company_cell: str | None, email: str | None) -> str | None:
    from_cell = registered_domain(company_cell) if _blank(company_cell) else None
    from_email = company_domain_from_email(email)
    if from_cell and from_email and from_cell != from_email:
        return None
    return from_cell or from_email


def _safe_email(raw: str | None, record_id: str) -> str | None:
    text = _blank(raw)
    if text is None:
        return None
    try:
        return normalize_email(text)
    except ValueError:
        logger.warning("crm_field_skipped record_id=%s reason=email_shape", record_id)
        return None


def _safe_linkedin(raw: str | None, record_id: str) -> str | None:
    text = _blank(raw)
    if text is None:
        return None
    try:
        return normalize_linkedin(text)
    except ValueError:
        logger.warning("crm_field_skipped record_id=%s reason=linkedin", record_id)
        return None


def _deal(deal_id: str | None, created: str | None) -> tuple[str | None, datetime | None, bool]:
    identifier = _blank(deal_id)
    if identifier is None:
        return None, None, False
    stamp = _blank(created)
    if stamp is None:
        return identifier, None, True
    try:
        return identifier, parse_timestamp(stamp), False
    except ValueError:
        return identifier, None, True


def read_crm(path: Path) -> list[CrmRow]:
    rows: list[CrmRow] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            record_id = (raw.get("record_id") or "").strip()
            email = _safe_email(raw.get("email"), record_id)
            industry, kind = map_vertical(raw.get("vertical"))
            is_customer, customer_unreadable = parse_customer(raw.get("is_customer"))
            deal_id, deal_at, deal_unreadable = _deal(
                raw.get("open_deal_id"), raw.get("open_deal_created")
            )
            first = _blank(raw.get("first_name")) or ""
            last = _blank(raw.get("last_name")) or ""
            rows.append(
                CrmRow(
                    record_id=record_id,
                    display_name=" ".join(part for part in (first, last) if part),
                    email=email,
                    linkedin_slug=_safe_linkedin(raw.get("linkedin_url"), record_id),
                    company_name=_blank(raw.get("company_name")) or "",
                    company_domain=_domain(raw.get("company_domain"), email),
                    industry=industry,
                    employees=parse_employees(raw.get("employees")),
                    country=_blank(raw.get("country")),
                    account_kind=kind,
                    title=_blank(raw.get("job_title")),
                    is_customer=is_customer,
                    customer_unreadable=customer_unreadable,
                    crm_owner=_blank(raw.get("owner")),
                    open_deal_id=deal_id,
                    open_deal_created=deal_at,
                    deal_unreadable=deal_unreadable,
                    lead_status=_blank(raw.get("lead_status")),
                )
            )
    return rows


def read_events(path: Path) -> EventsFile:
    payload = json.loads(path.read_text(encoding="utf-8"))
    inbounds = [
        InboundRecord(
            id=item["id"],
            channel=item.get("channel"),
            source=_blank(item.get("source")),
            received_at=item.get("received_at"),
            from_name=item.get("from_name") or "",
            from_email=item.get("from_email"),
            linkedin_url=item.get("linkedin_url"),
            subject=item.get("subject"),
            body=item.get("body"),
        )
        for item in payload["inbound"]
    ]
    decisions = [
        SalesRow(
            id=item["id"],
            email=item.get("contact_email"),
            decision=(item.get("decision") or "").strip().casefold(),
            decided_by=_blank(item.get("decided_by")),
            decided_at=item["decided_at"],
            note=item.get("note") or "",
        )
        for item in payload["sales_decisions"]
    ]
    events = [
        PipelineRow(
            id=item["id"],
            email=item.get("contact_email"),
            event_type=item.get("type") or "",
            occurred_at=item["occurred_at"],
        )
        for item in payload["pipeline_events"]
    ]
    feeds = {str(key): str(value) for key, value in payload["feed_status"].items()}
    return EventsFile(inbounds=inbounds, decisions=decisions, events=events, feeds=feeds)
