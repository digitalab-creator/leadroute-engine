"""Identity: email, LinkedIn, and company domain. Name and company do not merge people."""

import asyncio
import json
from pathlib import Path

import httpx

from app.db import apply_schema, connect
from app.ingest.identity import (
    company_domain_from_email,
    normalize_email,
    normalize_linkedin,
    registered_domain,
)
from app.logging_config import configure_logging
from app.main import create_app
from app.service import load_seed
from tests.conftest import DATA_DIR

import pytest


def test_email_case_is_the_same_mailbox() -> None:
    assert normalize_email("Rachel.Lim@Lionport.com.sg") == "rachel.lim@lionport.com.sg"


def test_bad_email_shape_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_email("asdf@asdf")


def test_blank_email_is_missing_not_invalid() -> None:
    assert normalize_email("  ") is None
    assert normalize_email(None) is None


def test_linkedin_ignores_www_case_and_trailing_slash() -> None:
    left = normalize_linkedin("https://www.linkedin.com/in/pieterclaes-bcl")
    right = normalize_linkedin("https://linkedin.com/in/TomBecker-Logistics/")
    assert left == "pieterclaes-bcl"
    assert right == "tombecker-logistics"


def test_company_page_is_not_a_person() -> None:
    with pytest.raises(ValueError):
        normalize_linkedin("https://www.linkedin.com/company/stargo")


def test_domains_keep_multipart_suffixes_and_drop_subdomains() -> None:
    assert registered_domain("www.NordhavenFreight.com") == "nordhavenfreight.com"
    assert registered_domain("nl.nordhavenfreight.com") == "nordhavenfreight.com"
    assert registered_domain("meridianhaulage.co.uk") == "meridianhaulage.co.uk"
    assert registered_domain("lionport.com.sg") == "lionport.com.sg"
    assert registered_domain("ashdodbay.co.il") == "ashdodbay.co.il"


def test_free_mail_does_not_name_a_company() -> None:
    assert company_domain_from_email("yossi.mizrahi@gmail.com") is None
    assert company_domain_from_email("lior.bd@outlook.com") is None
    assert company_domain_from_email("ada@example-forwarder.com") == "example-forwarder.com"


def test_seed_matches_email_case_and_linkedin_but_not_company(tmp_path: Path) -> None:
    configure_logging(tmp_path / "logs")
    connection = connect(tmp_path / "revops.sqlite")
    apply_schema(connection)
    report = load_seed(connection, DATA_DIR)

    rachel = connection.execute(
        "SELECT id FROM persons WHERE email = ?",
        ("rachel.lim@lionport.com.sg",),
    ).fetchone()
    assert rachel is not None
    decisions = connection.execute(
        "SELECT COUNT(*) AS n FROM sales_decisions WHERE person_id = ?",
        (rachel["id"],),
    ).fetchone()
    assert decisions["n"] == 2

    pieter = connection.execute(
        "SELECT id FROM persons WHERE email = ?",
        ("p.claes@balticacargo.eu",),
    ).fetchone()
    by_linkedin = connection.execute(
        "SELECT id FROM persons WHERE linkedin_slug = ?",
        ("pieterclaes-bcl",),
    ).fetchone()
    assert pieter["id"] == by_linkedin["id"]
    inbounds = connection.execute(
        "SELECT COUNT(*) AS n FROM inbounds WHERE person_id = ?",
        (pieter["id"],),
    ).fetchone()
    assert inbounds["n"] == 2

    anouk = connection.execute(
        "SELECT id FROM persons WHERE email = ?",
        ("anouk.devries@nordhavenfreight.com",),
    ).fetchone()
    sanne = connection.execute(
        "SELECT id FROM persons WHERE email = ?",
        ("sanne.jansen@nl.nordhavenfreight.com",),
    ).fetchone()
    assert anouk["id"] != sanne["id"]

    skipped = connection.execute("SELECT id FROM inbounds WHERE id = ?", ("IN-019",)).fetchone()
    assert skipped is None
    assert ("IN-019", "message text is empty") in report.rejected
    kept = connection.execute("SELECT id FROM inbounds WHERE id = ?", ("IN-020",)).fetchone()
    assert kept is not None
    connection.close()


def test_paste_rejects_a_bad_row_with_a_clear_400(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "revops.sqlite",
        data_dir=DATA_DIR,
        log_dir=tmp_path / "logs",
        load_env=False,
    )
    async def _post_bad_rows() -> tuple[httpx.Response, httpx.Response, httpx.Response, httpx.Response]:
        # Start the app the same way a server does, then send HTTP.
        # httpx talks to the app directly, so this works on old and new Starlette.
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                missing_channel = await client.post(
                    "/api/inbound",
                    json={"text": "Hello there", "from_email": "ada@example.com"},
                )
                empty_text = await client.post(
                    "/api/inbound",
                    json={"channel": "email_reply", "text": "   ", "from_email": "ada@example.com"},
                )
                bad_email = await client.post(
                    "/api/inbound",
                    json={
                        "channel": "form_fill",
                        "text": "Please send a demo.",
                        "from_email": "asdf@asdf",
                    },
                )
                bad_time = await client.post(
                    "/api/inbound",
                    json={
                        "channel": "email_reply",
                        "text": "Please send a demo.",
                        "from_email": "ada@example.com",
                        "received_at": "next tuesday",
                    },
                )
        return missing_channel, empty_text, bad_email, bad_time

    missing_channel, empty_text, bad_email, bad_time = asyncio.run(_post_bad_rows())
    assert missing_channel.status_code == 400
    assert empty_text.status_code == 400
    assert bad_email.status_code == 400
    assert bad_time.status_code == 400
    assert "channel" in json.dumps(missing_channel.json()).lower()
    assert "empty" in json.dumps(empty_text.json()).lower()
    assert "email" in json.dumps(bad_email.json()).lower()
    assert "timestamp" in json.dumps(bad_time.json()).lower()
