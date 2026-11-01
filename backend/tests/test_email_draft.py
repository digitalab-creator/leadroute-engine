"""Outbound email signature and compose links."""

from app.constants import DEFAULT_SITE_ORIGIN
from app.pipeline.email_draft import (
    SIGNATURE_MARKER,
    compose_links,
    compose_outbound_draft,
    gmail_compose_url,
    load_sales_rep,
    normalize_body_paragraphs,
    split_body_and_signature,
)
from tests.conftest import DATA_DIR


def test_compose_adds_rep_signature_for_owner() -> None:
    body = "שלום,\n\n- נקודה אחת\n- נקודה שתיים"
    plain, html = compose_outbound_draft(
        body,
        owner="Noa",
        language="he",
        data_dir=DATA_DIR,
        site_origin=DEFAULT_SITE_ORIGIN,
    )
    assert "Noa Cohen" in plain
    assert "noa@stargo.co" in plain
    assert SIGNATURE_MARKER in plain
    assert split_body_and_signature(plain)[0].startswith("שלום")
    assert "stargo-logo.svg" in html
    assert DEFAULT_SITE_ORIGIN in html
    assert "<ul" in html


def test_gmail_compose_url_encodes_body() -> None:
    body = "Hello\n\nBest,\nNoa"
    url = gmail_compose_url(to="noam@ashdodbay.co.il", subject="Re: test", body=body)
    assert "mail.google.com" in url
    assert "noam%40ashdodbay.co.il" in url
    from app.pipeline.email_draft import decode_gmail_compose_url

    decoded = decode_gmail_compose_url(url)
    assert decoded["to"] == "noam@ashdodbay.co.il"
    assert decoded["subject"] == "Re: test"
    assert decoded["body"] == body


def test_compose_rejects_html() -> None:
    import pytest

    with pytest.raises(ValueError):
        gmail_compose_url(to="a@b.co", subject="x", body="<p>bad</p>")


def test_compose_links_requires_recipient() -> None:
    links = compose_links(to_email=None, subject="Re:", plain_body="x")
    assert links["gmail_url"] is None
    filled = compose_links(
        to_email="noam@ashdodbay.co.il", subject="Re: hi", plain_body="Body"
    )
    assert filled["gmail_url"]
    assert filled["zoho_url"]


def test_normalize_keeps_paragraph_breaks() -> None:
    text = normalize_body_paragraphs("Line one\n\nLine two")
    assert text == "Line one\n\nLine two"


def test_load_sales_rep_fallback() -> None:
    rep = load_sales_rep(DATA_DIR, "Unknown", "en")
    assert rep.email
