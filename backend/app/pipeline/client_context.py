"""Everything we know about the buyer, for the writer and for feedback rows."""

import json
import sqlite3

from app import repo


def build_client_context_json(connection: sqlite3.Connection, person_id: str) -> str:
    """CRM person, every inbound, and stored extractions. One JSON string."""
    person = repo.get_person(connection, person_id)
    if person is None:
        return "{}"
    person_block = {
        "person_id": person_id,
        "display_name": str(person["display_name"] or ""),
        "email": None if person["email"] is None else str(person["email"]),
        "company_name": None if person["company_name"] is None else str(person["company_name"]),
        "company_domain": None if person["company_domain"] is None else str(person["company_domain"]),
        "industry": None if person["industry"] is None else str(person["industry"]),
        "employees": person["employees"],
        "country": None if person["country"] is None else str(person["country"]),
        "title": None if person["title"] is None else str(person["title"]),
        "account_kind": str(person["account_kind"]),
        "is_customer": bool(person["is_customer"]) if person["is_customer"] is not None else None,
        "crm_owner": None if person["crm_owner"] is None else str(person["crm_owner"]),
        "lead_status": None if person["lead_status"] is None else str(person["lead_status"]),
    }
    messages: list[dict[str, object]] = []
    for inbound in repo.list_inbounds(connection, person_id):
        extraction = repo.get_extraction(connection, str(inbound["id"]))
        payload = None
        if extraction is not None and extraction["payload_json"]:
            try:
                loaded = json.loads(str(extraction["payload_json"]))
                if isinstance(loaded, dict):
                    payload = loaded
            except json.JSONDecodeError:
                payload = None
        messages.append(
            {
                "inbound_id": str(inbound["id"]),
                "channel": str(inbound["channel"]),
                "source": None if inbound["source"] is None else str(inbound["source"]),
                "received_at": str(inbound["received_at"]),
                "subject": None if inbound["subject"] is None else str(inbound["subject"]),
                "body": str(inbound["body"]),
                "extraction": payload,
                "analysis_mode": None if extraction is None else str(extraction["mode"]),
                "analysis_failed": None if extraction is None else bool(extraction["failed"]),
            }
        )
    return json.dumps({"person": person_block, "messages": messages}, ensure_ascii=False)
