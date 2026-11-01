"""HubSpot CRM v3 dry-run payloads from stored qualification rows.

No HTTP is sent. Each item is the PATCH body you would send to update a contact
after LeadRoute has scored and routed a lead.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app import repo
from app.constants import Status

HUBSPOT_API_BASE = "https://api.hubapi.com"

# Synthetic owner ids for the rep names in ql_standard routing (dry-run only).
HUBSPOT_OWNER_ID_BY_REP: dict[str, str] = {
    "Dana": "810001",
    "Leo": "810002",
    "Mei": "810003",
    "Sam": "810004",
    "Noa": "810005",
    "Founders": "810009",
    "Triage queue": "810000",
}

_ENGINE_STATUS_TO_CRM_LEAD_STATUS: dict[str, str] = {
    Status.QL.value: "QL",
    Status.QL_CANDIDATE.value: "Open",
    Status.NURTURE.value: "Nurture",
    Status.DISQUALIFIED.value: "Disqualified",
    Status.EXCLUDED.value: "Excluded",
    Status.SUPPRESSED.value: "Unsubscribed",
    Status.NEEDS_REVIEW.value: "Needs review",
}


def _owner_id(owner: str | None) -> str | None:
    if owner is None or not str(owner).strip():
        return None
    name = str(owner).strip()
    return HUBSPOT_OWNER_ID_BY_REP.get(name)


def _contact_object_id(person: sqlite3.Row) -> str:
    crm_id = person["crm_record_id"]
    if crm_id is not None and str(crm_id).strip():
        return str(crm_id).strip()
    return str(person["id"])


def _patch_contact_request(
    *,
    person: sqlite3.Row,
    qualification: sqlite3.Row,
) -> dict[str, Any]:
    object_id = _contact_object_id(person)
    status = str(qualification["status"])
    owner_name = qualification["owner"]
    owner_id = _owner_id(None if owner_name is None else str(owner_name))
    lead_status = _ENGINE_STATUS_TO_CRM_LEAD_STATUS.get(status, status)
    properties: dict[str, str] = {
        "lead_status": lead_status,
        "stargo_engine_status": status,
        "stargo_priority_score": str(int(qualification["score"])),
        "stargo_score_band": str(qualification["band"]),
    }
    if owner_id is not None:
        properties["hubspot_owner_id"] = owner_id
    rationale = qualification["rationale"]
    if rationale is not None and str(rationale).strip():
        properties["stargo_rationale"] = str(rationale).strip()[:500]
    email = person["email"]
    if email is not None and str(email).strip():
        properties["email"] = str(email).strip()

    return {
        "method": "PATCH",
        "url": f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{object_id}",
        "headers": {"Content-Type": "application/json"},
        "body": {"properties": properties},
        "meta": {
            "person_id": str(person["id"]),
            "crm_record_id": object_id,
            "engine_owner_name": None if owner_name is None else str(owner_name),
            "engine_owner_hubspot_id": owner_id,
        },
    }


def build_hubspot_dry_run(connection: sqlite3.Connection) -> dict[str, Any]:
    """Build the full dry-run document for every stored qualification."""
    requests: list[dict[str, Any]] = []
    for qualification in sorted(
        repo.list_qualifications(connection),
        key=lambda row: str(row["person_id"]),
    ):
        person_id = str(qualification["person_id"])
        person = repo.get_person(connection, person_id)
        if person is None:
            continue
        requests.append(
            _patch_contact_request(person=person, qualification=qualification)
        )
    return {
        "dry_run": True,
        "portal_calls": 0,
        "description": (
            "HubSpot CRM v3 contact updates from LeadRoute qualification rows. "
            "Owner ids are synthetic mappings for rep first names. "
            "Custom properties (stargo_*) would be created in the portal before a real sync."
        ),
        "owner_id_map": dict(HUBSPOT_OWNER_ID_BY_REP),
        "requests": requests,
    }
