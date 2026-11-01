"""The only SQL in the app. Callers pass values. They do not build query strings."""

import sqlite3
from datetime import datetime

from app.ingest.records import CrmRow


def _flag(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _stamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def count_persons(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS n FROM persons").fetchone()
    return int(row["n"])


def upsert_crm_person(connection: sqlite3.Connection, row: CrmRow) -> None:
    connection.execute(
        """
        INSERT INTO persons (
            id, display_name, email, linkedin_slug, company_name, company_domain,
            industry, employees, country, account_kind, title, is_customer, crm_owner,
            open_deal_id, open_deal_created, deal_unreadable, lead_status, crm_record_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            display_name = excluded.display_name,
            email = excluded.email,
            linkedin_slug = excluded.linkedin_slug,
            company_name = excluded.company_name,
            company_domain = excluded.company_domain,
            industry = excluded.industry,
            employees = excluded.employees,
            country = excluded.country,
            account_kind = excluded.account_kind,
            title = excluded.title,
            is_customer = excluded.is_customer,
            crm_owner = excluded.crm_owner,
            open_deal_id = excluded.open_deal_id,
            open_deal_created = excluded.open_deal_created,
            deal_unreadable = excluded.deal_unreadable,
            lead_status = excluded.lead_status,
            crm_record_id = excluded.crm_record_id
        """,
        (
            row.record_id,
            row.display_name,
            row.email,
            row.linkedin_slug,
            row.company_name,
            row.company_domain,
            row.industry,
            row.employees,
            row.country,
            row.account_kind,
            row.title,
            _flag(row.is_customer),
            row.crm_owner,
            row.open_deal_id,
            _stamp(row.open_deal_created),
            1 if row.deal_unreadable else 0,
            row.lead_status,
            row.record_id,
        ),
    )


def insert_external_person(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    display_name: str,
    email: str | None,
    linkedin_slug: str | None,
    company_domain: str | None,
    industry: str | None,
    employees: int | None,
    country: str | None,
    account_kind: str,
) -> None:
    connection.execute(
        """
        INSERT INTO persons (
            id, display_name, email, linkedin_slug, company_domain,
            industry, employees, country, account_kind, is_customer, deal_unreadable
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (
            person_id,
            display_name,
            email,
            linkedin_slug,
            company_domain,
            industry,
            employees,
            country,
            account_kind,
        ),
    )


def fill_identifier(
    connection: sqlite3.Connection,
    person_id: str,
    *,
    email: str | None,
    linkedin_slug: str | None,
) -> None:
    if email:
        connection.execute(
            """
            UPDATE persons SET email = ?
            WHERE id = ? AND (email IS NULL OR email = '')
            """,
            (email, person_id),
        )
    if linkedin_slug:
        connection.execute(
            """
            UPDATE persons SET linkedin_slug = ?
            WHERE id = ? AND (linkedin_slug IS NULL OR linkedin_slug = '')
            """,
            (linkedin_slug, person_id),
        )


def find_person_id_by_email(connection: sqlite3.Connection, email: str) -> str | None:
    row = connection.execute("SELECT id FROM persons WHERE email = ?", (email,)).fetchone()
    return None if row is None else str(row["id"])


def find_person_id_by_linkedin(connection: sqlite3.Connection, slug: str) -> str | None:
    row = connection.execute(
        "SELECT id FROM persons WHERE linkedin_slug = ?", (slug,)
    ).fetchone()
    return None if row is None else str(row["id"])


def company_rows(connection: sqlite3.Connection, domain: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT industry, employees, country, account_kind
            FROM persons WHERE company_domain = ?
            """,
            (domain,),
        )
    )


def get_person(connection: sqlite3.Connection, person_id: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()


def list_persons(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM persons ORDER BY id"))


def insert_inbound(
    connection: sqlite3.Connection,
    *,
    inbound_id: str,
    person_id: str,
    channel: str,
    source: str | None,
    received_at: str,
    subject: str | None,
    body: str,
    from_name: str,
) -> None:
    connection.execute(
        """
        INSERT INTO inbounds (
            id, person_id, channel, source, received_at, subject, body, from_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (inbound_id, person_id, channel, source, received_at, subject, body, from_name),
    )


def save_extraction(
    connection: sqlite3.Connection,
    *,
    inbound_id: str,
    mode: str,
    failed: bool,
    injection: bool,
    payload_json: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO extractions (inbound_id, mode, failed, injection, payload_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(inbound_id) DO UPDATE SET
            mode = excluded.mode,
            failed = excluded.failed,
            injection = excluded.injection,
            payload_json = excluded.payload_json
        """,
        (inbound_id, mode, 1 if failed else 0, 1 if injection else 0, payload_json),
    )


def list_inbounds(connection: sqlite3.Connection, person_id: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT * FROM inbounds WHERE person_id = ? ORDER BY received_at, id
            """,
            (person_id,),
        )
    )


def get_extraction(connection: sqlite3.Connection, inbound_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM extractions WHERE inbound_id = ?", (inbound_id,)
    ).fetchone()


def insert_sales_decision(
    connection: sqlite3.Connection,
    *,
    decision_id: str,
    person_id: str,
    decision: str,
    decided_by: str | None,
    decided_at: str,
    note: str,
) -> None:
    connection.execute(
        """
        INSERT INTO sales_decisions (id, person_id, decision, decided_by, decided_at, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (decision_id, person_id, decision, decided_by, decided_at, note),
    )


def delete_decisions_of_kind(
    connection: sqlite3.Connection, person_id: str, decision: str
) -> None:
    connection.execute(
        "DELETE FROM sales_decisions WHERE person_id = ? AND decision = ?",
        (person_id, decision),
    )


def list_sales(connection: sqlite3.Connection, person_id: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            "SELECT * FROM sales_decisions WHERE person_id = ? ORDER BY decided_at, id",
            (person_id,),
        )
    )


def save_qualification(
    connection: sqlite3.Connection,
    *,
    person_id: str,
    status: str,
    owner: str | None,
    score: int,
    band: str,
    breakdown_json: str,
    conditions_json: str,
    rationale: str,
    draft: str | None,
    draft_state: str,
    analysis_mode: str,
    expansion: bool,
    qualified: bool,
) -> None:
    connection.execute(
        """
        INSERT INTO decisions (
            person_id, status, owner, score, band, breakdown_json, conditions_json,
            rationale, draft, draft_state, analysis_mode, expansion, qualified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET
            status = excluded.status,
            owner = excluded.owner,
            score = excluded.score,
            band = excluded.band,
            breakdown_json = excluded.breakdown_json,
            conditions_json = excluded.conditions_json,
            rationale = excluded.rationale,
            draft = excluded.draft,
            draft_state = excluded.draft_state,
            analysis_mode = excluded.analysis_mode,
            expansion = excluded.expansion,
            qualified = excluded.qualified
        """,
        (
            person_id,
            status,
            owner,
            score,
            band,
            breakdown_json,
            conditions_json,
            rationale,
            draft,
            draft_state,
            analysis_mode,
            1 if expansion else 0,
            1 if qualified else 0,
        ),
    )


def get_qualification(connection: sqlite3.Connection, person_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM decisions WHERE person_id = ?", (person_id,)
    ).fetchone()


def list_qualifications(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM decisions"))


def insert_pipeline_event(
    connection: sqlite3.Connection,
    *,
    event_id: str,
    person_id: str | None,
    event_type: str,
    occurred_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO pipeline_events (id, person_id, event_type, occurred_at)
        VALUES (?, ?, ?, ?)
        """,
        (event_id, person_id, event_type, occurred_at),
    )


def list_pipeline_events(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(connection.execute("SELECT * FROM pipeline_events"))


def save_feed(connection: sqlite3.Connection, source: str, status: str) -> None:
    connection.execute(
        """
        INSERT INTO feed_status (source, status) VALUES (?, ?)
        ON CONFLICT(source) DO UPDATE SET status = excluded.status
        """,
        (source, status),
    )


def list_feeds(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT source, status FROM feed_status")
    return {str(row["source"]): str(row["status"]) for row in rows}
