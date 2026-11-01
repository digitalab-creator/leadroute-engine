"""Seed and paste share ingest_inbound. The gate runs again when a decision changes."""

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.clock import JERUSALEM, in_reporting_week, parse_timestamp
from app.constants import PIPELINE_EVENT_TYPES, AccountKind, configured_site_origin
from app.ingest.files import read_crm, read_events
from app.ingest.firmographics import agree_columns, fill_company_gaps
from app.ingest.identity import company_domain_from_email, normalize_email, normalize_linkedin
from app.ingest.records import InboundRecord
from app.ingest.validate import validate_inbound
from app.kpi.pack import KpiPack, PackEvent, PackPerson, build_pack
from app.logging_config import get_logger
from app.pipeline.extract import CompletionClient, ExtractOutcome, extract_message
from app.pipeline.facts import PersonProfile, build_gate_input
from app.pipeline.gate import decide
from app.pipeline.merge import merge_outcomes
from app.pipeline.schemas import Extraction
from app.brand_docs import read_brand_context
from app.pipeline.client_context import build_client_context_json
from app.labels import draft_matches_language
from app.pipeline.draft_learning import writer_addendum
from app import repo
from app.pipeline.email_draft import compose_outbound_draft
from app.pipeline.writer import writer_draft
from app.pipeline.writer_brief import WriterInput

logger = get_logger()

_MAX_FEEDBACK_COMMENT = 2000


def _feedback_comment(raw: str | None) -> str:
    if raw is None:
        return ""
    text = raw.strip()
    if len(text) > _MAX_FEEDBACK_COMMENT:
        return text[:_MAX_FEEDBACK_COMMENT]
    return text


class InboundRejected(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class SeedReport:
    rejected: tuple[tuple[str, str], ...]


def _external_id(email: str | None, slug: str | None, fallback: str) -> str:
    if email:
        token = f"email:{email}"
    elif slug:
        token = f"li:{slug}"
    else:
        token = f"row:{fallback}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"p-{digest}"


def _optional_email(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return normalize_email(value)


def _optional_linkedin(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return normalize_linkedin(value)


def _domain_facts(
    connection: sqlite3.Connection, domain: str | None
) -> tuple[str | None, int | None, str | None, str]:
    if not domain:
        return None, None, None, AccountKind.UNKNOWN.value
    rows = repo.company_rows(connection, domain)
    if not rows:
        return None, None, None, AccountKind.UNKNOWN.value
    return agree_columns(
        [row["industry"] for row in rows],
        [row["employees"] for row in rows],
        [row["country"] for row in rows],
        [str(row["account_kind"]) for row in rows],
    )


def _match_or_create(
    connection: sqlite3.Connection,
    *,
    email: str | None,
    slug: str | None,
    display_name: str,
    fallback_id: str,
) -> str:
    by_email = repo.find_person_id_by_email(connection, email) if email else None
    by_linkedin = repo.find_person_id_by_linkedin(connection, slug) if slug else None
    if by_email and by_linkedin and by_email != by_linkedin:
        raise InboundRejected(["email and LinkedIn belong to different people"])
    existing = by_email or by_linkedin
    if existing:
        repo.fill_identifier(connection, existing, email=email, linkedin_slug=slug)
        return existing
    person_id = _external_id(email, slug, fallback_id)
    domain = company_domain_from_email(email)
    industry, employees, country, kind = _domain_facts(connection, domain)
    repo.insert_external_person(
        connection,
        person_id=person_id,
        display_name=display_name,
        email=email,
        linkedin_slug=slug,
        company_domain=domain,
        industry=industry,
        employees=employees,
        country=country,
        account_kind=kind,
    )
    return person_id


def _outcome_from_row(row: sqlite3.Row | None) -> ExtractOutcome:
    if row is None:
        return ExtractOutcome(True, False, "failed", None)
    extraction = None
    if row["payload_json"]:
        extraction = Extraction.model_validate_json(row["payload_json"])
    return ExtractOutcome(
        failed=bool(row["failed"]),
        injection=bool(row["injection"]),
        mode=str(row["mode"]),
        extraction=extraction,
    )


def _profile(row: sqlite3.Row) -> PersonProfile:
    customer = row["is_customer"]
    deal_raw = row["open_deal_created"]
    return PersonProfile(
        title=row["title"],
        industry=row["industry"],
        employees=row["employees"],
        country=row["country"],
        is_customer=None if customer is None else bool(customer),
        customer_unreadable=False,
        crm_owner=row["crm_owner"],
        open_deal_created=None if not deal_raw else parse_timestamp(str(deal_raw)),
        deal_unreadable=bool(row["deal_unreadable"]),
        account_kind=row["account_kind"] or AccountKind.UNKNOWN.value,
        lead_status=row["lead_status"],
    )


def _reply_language(pairs: list[tuple[datetime, ExtractOutcome]]) -> str:
    """Language of the quote the reply answers, else the latest message."""
    language = "en"
    quoted: str | None = None
    for _received, outcome in pairs:
        extraction = outcome.extraction
        if extraction is None or not extraction.language:
            continue
        language = extraction.language
        if extraction.stated_problem_quote:
            quoted = extraction.language
    return quoted or language


def recompute_person(
    connection: sqlite3.Connection,
    person_id: str,
    client: CompletionClient | None,
    *,
    data_dir: Path | None = None,
) -> sqlite3.Row:
    """Read stored evidence and write one decision. Does not call the model again."""
    person = repo.get_person(connection, person_id)
    if person is None:
        raise KeyError(person_id)
    inbounds = repo.list_inbounds(connection, person_id)
    pairs = []
    earliest_source: str | None = None
    earliest_at: datetime | None = None
    latest_inbound_id = person_id
    for inbound in inbounds:
        received = parse_timestamp(str(inbound["received_at"]))
        if earliest_at is None or received < earliest_at:
            earliest_at = received
            earliest_source = inbound["source"]
        latest_inbound_id = str(inbound["id"])
        pairs.append((received, _outcome_from_row(repo.get_extraction(connection, inbound["id"]))))
    signal = merge_outcomes(pairs)
    accepted_at: datetime | None = None
    for sale in repo.list_sales(connection, person_id):
        if sale["decision"] != "accepted":
            continue
        stamp = parse_timestamp(str(sale["decided_at"]))
        if accepted_at is None or stamp < accepted_at:
            accepted_at = stamp
    facts = build_gate_input(
        _profile(person),
        signal,
        accepted=accepted_at is not None,
        accepted_at=accepted_at,
        first_inbound=earliest_at,
        source=earliest_source or None,
    )
    decision = decide(facts)
    latest_body = ""
    if inbounds:
        latest_body = str(inbounds[-1]["body"])
    brand_text = read_brand_context(data_dir) if data_dir is not None else ""
    reply_language = _reply_language(pairs)
    raw_draft, draft_state = writer_draft(
        client,
        allowed=decision.draft_allowed,
        fields=WriterInput(
            inbound_id=latest_inbound_id,
            language=reply_language,
            message_body=latest_body,
            problem_quote=signal.problem_quote,
            intent=signal.intent,
            stated_problem=signal.problem,
            client_context_json=build_client_context_json(connection, person_id),
            brand_context_markdown=brand_text,
            learned_addendum=writer_addendum(connection),
        ),
    )
    draft = raw_draft
    if raw_draft and draft_state in {"writer", "template"}:
        draft, _html = compose_outbound_draft(
            raw_draft,
            owner=decision.owner,
            language=reply_language,
            data_dir=data_dir,
            site_origin=configured_site_origin(),
        )
    repo.save_qualification(
        connection,
        person_id=person_id,
        status=decision.status.value,
        owner=decision.owner,
        score=decision.score.total,
        band=decision.band,
        breakdown_json=json.dumps(decision.score.as_dict()),
        conditions_json=json.dumps(decision.conditions.as_dict()),
        rationale=decision.rationale,
        draft=draft,
        draft_state=draft_state,
        analysis_mode=signal.mode,
        expansion=decision.expansion,
        qualified=decision.qualified,
    )
    logger.info(
        "qualified person_id=%s status=%s mode=%s score=%s",
        person_id,
        decision.status.value,
        signal.mode,
        decision.score.total,
    )
    saved = repo.get_qualification(connection, person_id)
    if saved is None:
        raise RuntimeError(f"decision was not stored for {person_id}")
    return saved


def _stored_pairs(
    connection: sqlite3.Connection, person_id: str
) -> list[tuple[datetime, ExtractOutcome]]:
    pairs: list[tuple[datetime, ExtractOutcome]] = []
    for inbound in repo.list_inbounds(connection, person_id):
        pairs.append(
            (
                parse_timestamp(str(inbound["received_at"])),
                _outcome_from_row(repo.get_extraction(connection, str(inbound["id"]))),
            )
        )
    return pairs


def repair_template_language(connection: sqlite3.Connection) -> None:
    """Rewrite a local template that is not in the inbound language.

    Runs only when no model client is configured. A configured client rewrites
    the template when that lead is opened, and does not keep the old mix.
    """
    changed = False
    for row in repo.list_qualifications(connection):
        if str(row["draft_state"]) != "template":
            continue
        person_id = str(row["person_id"])
        language = _reply_language(_stored_pairs(connection, person_id))
        draft = "" if row["draft"] is None else str(row["draft"])
        if draft_matches_language(draft, language):
            continue
        recompute_person(connection, person_id, None)
        changed = True
    if changed:
        connection.commit()


def upgrade_template_draft(
    connection: sqlite3.Connection,
    person_id: str,
    client: CompletionClient | None,
    *,
    data_dir: Path | None = None,
) -> None:
    """Regenerate the unsent draft when Gemini is on so learning and context stay fresh."""
    refresh_draft_on_view(connection, person_id, client, data_dir=data_dir)


def refresh_draft_on_view(
    connection: sqlite3.Connection,
    person_id: str,
    client: CompletionClient | None,
    *,
    data_dir: Path | None = None,
) -> None:
    if client is None:
        return
    qual = repo.get_qualification(connection, person_id)
    if qual is None:
        return
    state = str(qual["draft_state"])
    if state in {"edited", "not_applicable"}:
        return
    recompute_person(connection, person_id, client, data_dir=data_dir)
    connection.commit()
    logger.info("draft_refreshed_on_view person_id=%s prior_state=%s", person_id, state)


def record_draft_feedback(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    rating: str,
    comment: str | None = None,
) -> dict[str, str]:
    """Store thumbs up or down on the current unsent draft."""
    kind = rating.strip().casefold()
    if kind not in {"up", "down"}:
        raise InboundRejected(["rating must be up or down"])
    qual = repo.get_qualification(connection, person_id)
    if qual is None:
        raise InboundRejected(["lead has no qualification"])
    draft = qual["draft"]
    if draft is None or not str(draft).strip():
        raise InboundRejected(["no draft to rate"])
    draft_text = str(draft)
    inbounds = repo.list_inbounds(connection, person_id)
    inbound_id = str(inbounds[-1]["id"]) if inbounds else None
    stamp = datetime.now(JERUSALEM).isoformat(timespec="seconds")
    repo.upsert_draft_feedback(
        connection,
        feedback_id=f"DF-{uuid.uuid4().hex[:12]}",
        person_id=person_id,
        draft_text=draft_text,
        rating=kind,
        created_at=stamp,
        inbound_id=inbound_id,
        client_context_json=build_client_context_json(connection, person_id),
        comment=_feedback_comment(comment),
    )
    connection.commit()
    return {"rating": kind, "recorded_at": stamp}


def save_draft_edit(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    draft_text: str,
    data_dir: Path | None,
) -> dict[str, object]:
    from app.pipeline.email_draft import validate_compose_plain
    from app.present import _lead_mail_bundle, _messages, _reply_language

    text = draft_text.strip()
    if not text:
        raise InboundRejected(["draft is empty"])
    try:
        validate_compose_plain(text)
    except ValueError as exc:
        raise InboundRejected([str(exc)]) from exc
    person = repo.get_person(connection, person_id)
    qual = repo.get_qualification(connection, person_id)
    if person is None or qual is None:
        raise InboundRejected(["lead has no qualification"])
    repo.update_draft_text(connection, person_id=person_id, draft=text)
    connection.commit()
    messages = _messages(connection, person_id)
    language = _reply_language(messages)
    owner = qual["owner"]
    owner_text = None if owner is None else str(owner)
    draft_html, compose = _lead_mail_bundle(
        person=person,
        draft_text=text,
        owner_text=owner_text,
        reply_language=language,
        messages=messages,
        data_dir=data_dir,
    )
    return {
        "draft": text,
        "draft_state": "edited",
        "draft_html": draft_html,
        "compose": compose,
    }


def record_visibility_feedback(
    connection: sqlite3.Connection,
    *,
    prompt_id: str,
    brief_fingerprint: str,
    brief_snapshot: dict[str, object],
    rating: str,
    comment: str | None = None,
) -> dict[str, str]:
    kind = rating.strip().casefold()
    if kind not in {"up", "down"}:
        raise InboundRejected(["rating must be up or down"])
    if not prompt_id.strip() or not brief_fingerprint.strip():
        raise InboundRejected(["brief identity is missing"])
    stamp = datetime.now(JERUSALEM).isoformat(timespec="seconds")
    from app.pipeline.visibility_learning import brief_fingerprint as fp_fn

    clean = {
        key: value
        for key, value in brief_snapshot.items()
        if key not in {"brief_fingerprint", "feedback_rating"}
    }
    snapshot_json = json.dumps(clean, ensure_ascii=False, sort_keys=True)
    expected = fp_fn(prompt_id, snapshot_json)
    if brief_fingerprint != expected:
        raise InboundRejected(["brief fingerprint does not match the snapshot"])
    repo.upsert_visibility_feedback(
        connection,
        feedback_id=f"VF-{uuid.uuid4().hex[:12]}",
        prompt_id=prompt_id,
        brief_fingerprint=brief_fingerprint,
        brief_snapshot_json=snapshot_json,
        rating=kind,
        created_at=stamp,
        comment=_feedback_comment(comment),
    )
    connection.commit()
    return {"rating": kind, "recorded_at": stamp}


def ingest_inbound(
    connection: sqlite3.Connection,
    record: InboundRecord,
    client: CompletionClient | None = None,
    *,
    recompute_now: bool = True,
    data_dir: Path | None = None,
) -> str:
    """Validate, match a person, store the message, and (usually) qualify them."""
    errors = validate_inbound(record)
    if errors:
        raise InboundRejected(errors)
    email = _optional_email(record.from_email)
    slug = _optional_linkedin(record.linkedin_url)
    person_id = _match_or_create(
        connection,
        email=email,
        slug=slug,
        display_name=record.from_name.strip(),
        fallback_id=record.id,
    )
    received = record.received_at.strip() if record.received_at else ""
    if not received:
        received = datetime.now(JERUSALEM).isoformat()
    source = record.source.strip() if record.source else None
    body = record.body or ""
    channel = record.channel or ""
    repo.insert_inbound(
        connection,
        inbound_id=record.id,
        person_id=person_id,
        channel=channel,
        source=source or None,
        received_at=received,
        subject=record.subject,
        body=body,
        from_name=record.from_name,
    )
    outcome = extract_message(body, record.id, client)
    payload = None if outcome.extraction is None else outcome.extraction.model_dump_json()
    repo.save_extraction(
        connection,
        inbound_id=record.id,
        mode=outcome.mode,
        failed=outcome.failed,
        injection=outcome.injection,
        payload_json=payload,
    )
    if recompute_now:
        recompute_person(connection, person_id, client, data_dir=data_dir)
    return person_id


def _ensure_person_for_email(connection: sqlite3.Connection, email: str) -> str:
    existing = repo.find_person_id_by_email(connection, email)
    if existing:
        return existing
    domain = company_domain_from_email(email)
    industry, employees, country, kind = _domain_facts(connection, domain)
    person_id = _external_id(email, None, email)
    repo.insert_external_person(
        connection,
        person_id=person_id,
        display_name="",
        email=email,
        linkedin_slug=None,
        company_domain=domain,
        industry=industry,
        employees=employees,
        country=country,
        account_kind=kind,
    )
    return person_id


def record_sales_decision(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    decision: str,
    decided_at: str,
    decided_by: str | None = None,
    note: str = "",
    decision_id: str | None = None,
    replace: bool = False,
    client: CompletionClient | None = None,
    data_dir: Path | None = None,
) -> sqlite3.Row:
    """Store a human accept or reject, then qualify that person again."""
    parse_timestamp(decided_at)
    kind = decision.strip().casefold()
    if kind not in {"accepted", "rejected"}:
        raise InboundRejected(["decision must be accepted or rejected"])
    if replace:
        # The click is the current decision. A no clears an earlier yes, and a yes
        # clears an earlier no. Otherwise Reject cannot change a qualified lead.
        repo.delete_decisions_of_kind(connection, person_id, kind)
        other = "rejected" if kind == "accepted" else "accepted"
        repo.delete_decisions_of_kind(connection, person_id, other)
    repo.insert_sales_decision(
        connection,
        decision_id=decision_id or f"SD-{uuid.uuid4().hex[:12]}",
        person_id=person_id,
        decision=kind,
        decided_by=decided_by,
        decided_at=decided_at,
        note=note,
    )
    saved = recompute_person(connection, person_id, client, data_dir=data_dir)
    connection.commit()
    return saved


def recompute_all(
    connection: sqlite3.Connection,
    client: CompletionClient | None = None,
    *,
    data_dir: Path | None = None,
) -> None:
    for person in repo.list_persons(connection):
        recompute_person(connection, str(person["id"]), client, data_dir=data_dir)


def load_seed(
    connection: sqlite3.Connection,
    data_dir: Path,
    client: CompletionClient | None = None,
) -> SeedReport:
    """Load the CRM file and the event file through the same inbound function."""
    people = fill_company_gaps(read_crm(data_dir / "crm_export.csv"))
    events = read_events(data_dir / "gtm_events.json")
    for person in people:
        repo.upsert_crm_person(connection, person)
    rejected: list[tuple[str, str]] = []
    for inbound in events.inbounds:
        try:
            ingest_inbound(connection, inbound, client, recompute_now=False)
        except InboundRejected as exc:
            logger.warning(
                "rejected inbound_id=%s reason=%s", inbound.id, exc.errors[0]
            )
            rejected.append((inbound.id, exc.errors[0]))
    for sale in events.decisions:
        try:
            email = normalize_email(sale.email)
        except ValueError:
            logger.warning("decision_skipped decision_id=%s reason=email_shape", sale.id)
            continue
        if email is None:
            logger.warning("decision_skipped decision_id=%s reason=missing_email", sale.id)
            continue
        person_id = _ensure_person_for_email(connection, email)
        repo.insert_sales_decision(
            connection,
            decision_id=sale.id,
            person_id=person_id,
            decision=sale.decision,
            decided_by=sale.decided_by,
            decided_at=sale.decided_at,
            note=sale.note,
        )
    for event in events.events:
        if event.event_type not in PIPELINE_EVENT_TYPES:
            logger.warning("pipeline_skipped event_id=%s reason=unknown_type", event.id)
            continue
        try:
            email = normalize_email(event.email)
        except ValueError:
            logger.warning("pipeline_skipped event_id=%s reason=email_shape", event.id)
            continue
        if email is None:
            logger.warning("pipeline_skipped event_id=%s reason=missing_email", event.id)
            continue
        matched_person = repo.find_person_id_by_email(connection, email)
        if matched_person is None:
            logger.warning("pipeline_skipped event_id=%s reason=no_person", event.id)
            continue
        repo.insert_pipeline_event(
            connection,
            event_id=event.id,
            person_id=matched_person,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
        )
    for source, status in events.feeds.items():
        repo.save_feed(connection, source, status)
    recompute_all(connection, client, data_dir=data_dir)
    connection.commit()
    logger.info(
        "seed_loaded persons=%s rejected=%s",
        repo.count_persons(connection),
        len(rejected),
    )
    return SeedReport(rejected=tuple(rejected))


def pack_from_connection(connection: sqlite3.Connection) -> KpiPack:
    qualifications = {str(row["person_id"]): row for row in repo.list_qualifications(connection)}
    people: list[PackPerson] = []
    for person in repo.list_persons(connection):
        person_id = str(person["id"])
        inbounds = repo.list_inbounds(connection, person_id)
        earliest_at: datetime | None = None
        earliest_source: str | None = None
        inbound_in_week = False
        for inbound in inbounds:
            received = parse_timestamp(str(inbound["received_at"]))
            if earliest_at is None or received < earliest_at:
                earliest_at = received
                earliest_source = inbound["source"]
            if in_reporting_week(received):
                inbound_in_week = True
        accepted_at: datetime | None = None
        for sale in repo.list_sales(connection, person_id):
            if sale["decision"] != "accepted":
                continue
            stamp = parse_timestamp(str(sale["decided_at"]))
            if accepted_at is None or stamp < accepted_at:
                accepted_at = stamp
        qualification = qualifications.get(person_id)
        status = str(qualification["status"]) if qualification else "nurture"
        deal_raw = person["open_deal_created"]
        customer = person["is_customer"]
        people.append(
            PackPerson(
                person_id=person_id,
                status=status,
                accepted_at=accepted_at,
                source=earliest_source or None,
                is_customer=bool(customer) if customer is not None else False,
                deal_created=None if not deal_raw else parse_timestamp(str(deal_raw)),
                first_inbound_at=earliest_at,
                inbound_in_week=inbound_in_week,
            )
        )
    events: list[PackEvent] = []
    for event in repo.list_pipeline_events(connection):
        if event["person_id"] is None:
            continue
        events.append(
            PackEvent(
                event_id=str(event["id"]),
                person_id=str(event["person_id"]),
                event_type=str(event["event_type"]),
                occurred_at=parse_timestamp(str(event["occurred_at"])),
            )
        )
    return build_pack(people, events, repo.list_feeds(connection))


def paste_inbound(
    connection: sqlite3.Connection,
    *,
    from_name: str,
    channel: str | None,
    text: str | None,
    from_email: str | None = None,
    linkedin_url: str | None = None,
    received_at: str | None = None,
    source: str | None = None,
    client: CompletionClient | None = None,
    data_dir: Path | None = None,
) -> sqlite3.Row:
    inbound_id = f"PA-{uuid.uuid4().hex[:12]}"
    record = InboundRecord(
        id=inbound_id,
        channel=channel,
        source=source,
        received_at=received_at,
        from_name=from_name,
        from_email=from_email,
        linkedin_url=linkedin_url,
        subject=None,
        body=text,
    )
    person_id = ingest_inbound(
        connection, record, client, recompute_now=True, data_dir=data_dir
    )
    connection.commit()
    saved = repo.get_qualification(connection, person_id)
    if saved is None:
        raise RuntimeError("paste did not produce a decision")
    return saved
