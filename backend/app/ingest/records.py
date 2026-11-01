"""Rows after the files are read, before anyone is qualified."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class InboundRecord:
    id: str
    channel: str | None
    source: str | None
    received_at: str | None
    from_name: str
    from_email: str | None
    linkedin_url: str | None
    subject: str | None
    body: str | None


@dataclass(frozen=True)
class CrmRow:
    record_id: str
    display_name: str
    email: str | None
    linkedin_slug: str | None
    company_name: str
    company_domain: str | None
    industry: str | None
    employees: int | None
    country: str | None
    account_kind: str
    title: str | None
    is_customer: bool | None
    customer_unreadable: bool
    crm_owner: str | None
    open_deal_id: str | None
    open_deal_created: datetime | None
    deal_unreadable: bool
    lead_status: str | None


@dataclass(frozen=True)
class SalesRow:
    id: str
    email: str | None
    decision: str
    decided_by: str | None
    decided_at: str
    note: str


@dataclass(frozen=True)
class PipelineRow:
    id: str
    email: str | None
    event_type: str
    occurred_at: str


@dataclass(frozen=True)
class EventsFile:
    inbounds: list[InboundRecord]
    decisions: list[SalesRow]
    events: list[PipelineRow]
    feeds: dict[str, str]
