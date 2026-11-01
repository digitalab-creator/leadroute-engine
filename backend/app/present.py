"""Turn stored rows into the JSON the screens read.

The queue, the lead, and the pack all come from here so the UI does not
invent a second definition of score, status, or Israel time.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app import repo
from app.clock import JERUSALEM, in_reporting_week, parse_timestamp, to_jerusalem
from app.pipeline.email_draft import compose_links, draft_html_from_plain, reply_subject
from app.constants import CHANNELS, KNOWN_FEEDS, configured_site_origin
from app.kpi.pack import CountLine
from app.labels import (
    evidence_label,
    label_analysis,
    label_channel,
    label_decision,
    label_draft_state,
    label_intent,
    label_language,
    label_pain,
    label_role,
    label_status,
    text_direction,
)
from app.service import pack_from_connection

_CONDITIONS = (
    ("icp", "Company fit"),
    ("buyer", "Buyer"),
    ("problem", "Data problem"),
    ("interest", "Interest"),
    ("acceptance", "Sales acceptance"),
)

_FACTORS = (
    ("icp", "ICP fit"),
    ("buyer", "Buyer"),
    ("problem", "Problem"),
    ("intent", "Intent"),
    ("source_warmth", "Source warmth"),
    ("total", "Total"),
)


def now_israel() -> str:
    return datetime.now(JERUSALEM).isoformat(timespec="seconds")


def israel_parts(value: str) -> tuple[str, str]:
    local = to_jerusalem(parse_timestamp(value))
    return local.strftime("%d %b %Y, %H:%M"), local.isoformat(timespec="seconds")


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def company_label(name: object, domain: object) -> str:
    named = _text(name)
    if named:
        return named
    domain_text = _text(domain)
    if domain_text:
        return domain_text
    return "Company not recorded"


def person_label(name: object) -> str:
    named = _text(name)
    return named or "Name not recorded"


def _json_object(raw: str) -> dict[str, object]:
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("stored json is not an object")
    return {str(key): value for key, value in loaded.items()}


def _conditions(raw: str) -> list[dict[str, object]]:
    parsed = _json_object(raw)
    rows: list[dict[str, object]] = []
    for key, label in _CONDITIONS:
        item = parsed.get(key)
        if not isinstance(item, dict):
            raise ValueError(f"condition {key} is missing")
        passed = item.get("passed")
        evidence = item.get("evidence")
        if not isinstance(passed, bool) or not isinstance(evidence, str):
            raise ValueError(f"condition {key} has a bad shape")
        rows.append(
            {
                "key": key,
                "label": label,
                "passed": passed,
                "evidence": evidence_label(evidence),
            }
        )
    return rows


def _breakdown(raw: str) -> dict[str, object]:
    parsed = _json_object(raw)
    factors: list[dict[str, object]] = []
    for key, label in _FACTORS:
        points = parsed.get(key)
        if isinstance(points, bool) or not isinstance(points, int):
            raise ValueError(f"score {key} is missing")
        factors.append({"key": key, "label": label, "points": points})
    band = parsed.get("band")
    if not isinstance(band, str):
        raise ValueError("score band is missing")
    return {"band": band, "factors": factors}


def _as_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _extraction(raw: object) -> dict[str, object] | None:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise ValueError("extraction payload is not text")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("extraction payload is not an object")
    public: dict[str, object] = {str(key): value for key, value in loaded.items()}
    language = _as_str(public.get("language"))
    intent = _as_str(public.get("intent"))
    problem = public.get("stated_problem")
    role = public.get("stated_role")
    public["language_label"] = label_language(language)
    public["intent_label"] = label_intent(intent)
    public["stated_problem_label"] = label_pain(problem) if isinstance(problem, str) and problem else None
    public["stated_role_label"] = label_role(role) if isinstance(role, str) and role else None
    return public


def queue_payload(connection: sqlite3.Connection) -> dict[str, object]:
    leads: list[dict[str, object]] = []
    for row in repo.list_lead_queue(connection):
        clock, iso = israel_parts(str(row["received_at"]))
        owner = row["owner"]
        leads.append(
            {
                "person_id": str(row["person_id"]),
                "name": person_label(row["display_name"]),
                "company": company_label(row["company_name"], row["company_domain"]),
                "channel": str(row["channel"]),
                "channel_label": label_channel(str(row["channel"])),
                "received_at_israel": clock,
                "received_at": iso,
                "score": int(row["score"]),
                "band": str(row["band"]),
                "status": str(row["status"]),
                "status_label": label_status(str(row["status"])),
                "owner": None if owner is None else str(owner),
            }
        )
    return {"leads": leads}


def _messages(connection: sqlite3.Connection, person_id: str) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    for inbound in repo.list_inbounds(connection, person_id):
        clock, iso = israel_parts(str(inbound["received_at"]))
        extraction = repo.get_extraction(connection, str(inbound["id"]))
        payload = None
        mode = None
        failed = None
        injection = None
        if extraction is not None:
            mode = str(extraction["mode"])
            failed = bool(extraction["failed"])
            injection = bool(extraction["injection"])
            payload = _extraction(extraction["payload_json"])
        source = inbound["source"]
        body = str(inbound["body"])
        language = ""
        if isinstance(payload, dict):
            language = _as_str(payload.get("language"))
        messages.append(
            {
                "inbound_id": str(inbound["id"]),
                "channel": str(inbound["channel"]),
                "channel_label": label_channel(str(inbound["channel"])),
                "direction": text_direction(language, body),
                "source": None if source is None else str(source),
                "from_name": person_label(inbound["from_name"]),
                "subject": None if inbound["subject"] is None else str(inbound["subject"]),
                "body": body,
                "received_at_israel": clock,
                "received_at": iso,
                "analysis_mode": mode,
                "analysis_mode_label": None if mode is None else label_analysis(mode),
                "analysis_failed": failed,
                "injection": injection,
                "extraction": payload,
            }
        )
    return messages


def _lead_mail_bundle(
    *,
    person: sqlite3.Row,
    draft_text: str,
    owner_text: str | None,
    reply_language: str,
    messages: list[dict[str, object]],
    data_dir: Path | None,
) -> tuple[str, dict[str, object]]:
    draft_html = draft_html_from_plain(
        draft_text,
        owner=owner_text,
        language=reply_language,
        data_dir=data_dir,
        site_origin=configured_site_origin(),
    )
    latest_subject = None
    for message in reversed(messages):
        subj = message.get("subject")
        if isinstance(subj, str) and subj.strip():
            latest_subject = subj
            break
    subject = reply_subject(latest_subject, reply_language)
    to_email = None if person["email"] is None else str(person["email"])
    compose: dict[str, object] = dict(
        compose_links(
            to_email=to_email,
            subject=subject,
            plain_body=draft_text,
        )
    )
    return draft_html, compose


def lead_payload(
    connection: sqlite3.Connection,
    person_id: str,
    *,
    data_dir: Path | None = None,
) -> dict[str, object] | None:
    person = repo.get_person(connection, person_id)
    qualification = repo.get_qualification(connection, person_id)
    if person is None or qualification is None:
        return None
    owner = qualification["owner"]
    draft = qualification["draft"]
    draft_text = None if draft is None else str(draft)
    messages = _messages(connection, person_id)
    reply_language = _reply_language(messages)
    owner_text = None if owner is None else str(owner)
    draft_html = None
    compose: dict[str, object] = {
        "to": None,
        "subject": None,
        "gmail_url": None,
        "zoho_url": None,
    }
    if draft_text:
        draft_html, compose = _lead_mail_bundle(
            person=person,
            draft_text=draft_text,
            owner_text=owner_text,
            reply_language=reply_language,
            messages=messages,
            data_dir=data_dir,
        )
    return {
        "person_id": person_id,
        "name": person_label(person["display_name"]),
        "company": company_label(person["company_name"], person["company_domain"]),
        "status": str(qualification["status"]),
        "status_label": label_status(str(qualification["status"])),
        "owner": None if owner is None else str(owner),
        "score": int(qualification["score"]),
        "band": str(qualification["band"]),
        "analysis_mode": str(qualification["analysis_mode"]),
        "analysis_mode_label": label_analysis(str(qualification["analysis_mode"])),
        "rationale": str(qualification["rationale"]),
        "draft": draft_text,
        "draft_html": draft_html,
        "compose": compose,
        "draft_state": str(qualification["draft_state"]),
        "draft_state_label": label_draft_state(str(qualification["draft_state"])),
        "draft_direction": text_direction(reply_language, draft_text or ""),
        "draft_feedback": _draft_feedback(connection, person_id, draft_text),
        "writer_learning_week": _writer_learning_week(connection),
        "sales_decision": _sales_decision(connection, person_id),
        "breakdown": _breakdown(str(qualification["breakdown_json"])),
        "conditions": _conditions(str(qualification["conditions_json"])),
        "messages": messages,
        "now_israel": now_israel(),
    }


def _draft_feedback(
    connection: sqlite3.Connection, person_id: str, draft_text: str | None
) -> dict[str, object]:
    if not draft_text:
        return {"rating": None, "comment": None}
    found = repo.get_draft_feedback(connection, person_id, draft_text)
    if found is None:
        return {"rating": None, "comment": None}
    rating, comment = found
    return {"rating": rating, "comment": comment or None}


def _writer_learning_week(connection: sqlite3.Connection) -> str | None:
    state = repo.get_writer_learning_state(connection)
    if state is None or not str(state["last_week_key"]):
        return None
    return str(state["last_week_key"])


def _reply_language(messages: list[dict[str, object]]) -> str:
    language = "en"
    for message in messages:
        extraction = message.get("extraction")
        if not isinstance(extraction, dict):
            continue
        code = extraction.get("language")
        if isinstance(code, str) and code:
            language = code
            if extraction.get("stated_problem_quote"):
                language = code
    return language


def _sales_decision(connection: sqlite3.Connection, person_id: str) -> dict[str, str] | None:
    sales = repo.list_sales(connection, person_id)
    if not sales:
        return None
    latest = sales[-1]
    clock, _iso = israel_parts(str(latest["decided_at"]))
    kind = str(latest["decision"])
    return {
        "decision": kind,
        "decision_label": label_decision(kind),
        "decided_at_israel": clock,
    }


def decision_note(*, decision: str, decided_at: str, status: str) -> str:
    """Plain sentence for the button result. The week window is written out."""
    when, _iso = israel_parts(decided_at)
    status_words = label_status(status)
    window = "Sunday 4 October 2026 and Thursday 8 October 2026"
    if decision == "rejected":
        return (
            f"Saved. Sales said no on {when} (Israel time). "
            "Any earlier yes was cleared. "
            f"The status is now {status_words}. "
            "This person is not in this week's qualified-lead count."
        )
    in_week = in_reporting_week(parse_timestamp(decided_at))
    if status == "QL" and in_week:
        return (
            f"Saved. Sales said yes on {when} (Israel time). "
            f"The status is {status_words}. "
            f"That time is between {window}, "
            "so this person counts in this week's qualified leads."
        )
    if status == "QL":
        return (
            f"Saved. Sales said yes on {when} (Israel time). "
            f"The status is {status_words}. "
            f"That time is outside {window}, "
            "so this week's qualified-lead number stays the same. The yes is still saved."
        )
    return (
        f"Saved. Sales said yes on {when} (Israel time). "
        f"The status is {status_words}, because the other checks are not all passing. "
        "They are not in this week's qualified-lead count yet."
    )


def _record(
    record_id: str,
    people: dict[str, sqlite3.Row],
    events: dict[str, sqlite3.Row],
) -> dict[str, object]:
    if record_id in people:
        return {
            "id": record_id,
            "person_id": record_id,
            "label": person_label(people[record_id]["display_name"]),
        }
    event = events.get(record_id)
    if event is None or event["person_id"] is None:
        return {"id": record_id, "person_id": None, "label": record_id}
    person_id = str(event["person_id"])
    person = people.get(person_id)
    name = person_label(person["display_name"]) if person is not None else person_id
    return {"id": record_id, "person_id": person_id, "label": f"{record_id} · {name}"}


def _line(
    line: CountLine,
    people: dict[str, sqlite3.Row],
    events: dict[str, sqlite3.Row],
) -> dict[str, object]:
    return {
        "actual": line.actual,
        "target": line.target,
        "unknown": line.actual is None,
        "records": [_record(record_id, people, events) for record_id in line.ids],
    }


def kpi_payload(connection: sqlite3.Connection) -> dict[str, object]:
    pack = pack_from_connection(connection)
    people = {str(row["id"]): row for row in repo.list_persons(connection)}
    events = {str(row["id"]): row for row in repo.list_pipeline_events(connection)}
    return {
        "week_start": pack.week_start,
        "week_end": pack.week_end,
        "qls": _line(pack.qls, people, events),
        "meetings_booked": _line(pack.meetings_booked, people, events),
        "meetings_held": _line(pack.meetings_held, people, events),
        "opportunities": _line(pack.opportunities, people, events),
        "by_source": {
            source: _line(line, people, events) for source, line in pack.by_source.items()
        },
        "expansion_meetings_booked": _line(pack.expansion_meetings_booked, people, events),
        "expansion_meetings_held": _line(pack.expansion_meetings_held, people, events),
        "expansion_opportunities": _line(pack.expansion_opportunities, people, events),
        "expansion_people": [
            _record(person_id, people, events) for person_id in pack.expansion_people
        ],
    }


def options_payload() -> dict[str, object]:
    return {"channels": list(CHANNELS), "sources": list(KNOWN_FEEDS)}
