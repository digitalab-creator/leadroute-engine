"""Production outbound email: body formatting, rep signature, Gmail/Zoho compose links."""

from __future__ import annotations

import html
import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from app.constants import DEFAULT_SITE_ORIGIN

SIGNATURE_MARKER = "\n--\n"
_LOGO_PATH = "/stargo-logo.svg"
_DEFAULT_REP_KEY = "Noa"


@dataclass(frozen=True)
class SalesRep:
    full_name: str
    title: str
    email: str
    phone: str


def load_sales_rep(data_dir: Path | None, owner: str | None, language: str) -> SalesRep:
    key = (owner or "").strip() or _DEFAULT_REP_KEY
    if data_dir is not None:
        path = data_dir / "sales_reps.json"
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            block = raw.get(key) if isinstance(raw, dict) else None
            if not isinstance(block, dict) and isinstance(raw, dict):
                block = raw.get(_DEFAULT_REP_KEY)
            if isinstance(block, dict):
                title_key = "title_he" if language == "he" else "title_en"
                return SalesRep(
                    full_name=str(block.get("full_name") or key),
                    title=str(block.get(title_key) or block.get("title_en") or ""),
                    email=str(block.get("email") or "hello@stargo.co"),
                    phone=str(block.get("phone") or ""),
                )
    return SalesRep(
        full_name=key,
        title="Account Executive",
        email="hello@stargo.co",
        phone="+972-3-555-0100",
    )


def normalize_body_paragraphs(body: str) -> str:
    text = body.strip()
    if not text:
        return text
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line.strip():
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        cleaned.append(line.strip())
    parts: list[str] = []
    buffer: list[str] = []
    for line in cleaned:
        if line == "":
            if buffer:
                parts.append("\n".join(buffer))
                buffer = []
            continue
        buffer.append(line)
    if buffer:
        parts.append("\n".join(buffer))
    return "\n\n".join(parts)


def plain_signature(rep: SalesRep, *, language: str) -> str:
    closing = "Best," if language != "he" else "בברכה,"
    return (
        f"{closing}\n"
        f"{rep.full_name}\n"
        f"{rep.title}\n"
        f"{rep.email} · {rep.phone}\n"
        f"Stargo · stargo.co"
    )


def html_signature(rep: SalesRep, *, language: str, logo_url: str) -> str:
    closing = "Best," if language != "he" else "בברכה,"
    name = html.escape(rep.full_name)
    title = html.escape(rep.title)
    email = html.escape(rep.email)
    phone = html.escape(rep.phone)
    logo = html.escape(logo_url)
    return (
        f'<p style="margin:24px 0 8px;">{html.escape(closing)}</p>'
        f'<table cellpadding="0" cellspacing="0" style="border-top:1px solid #e3d9cc;'
        f'padding-top:12px;"><tr><td style="padding-right:12px;vertical-align:top;">'
        f'<img src="{logo}" alt="Stargo" width="120" height="32" style="display:block;"/>'
        f"</td><td style=\"vertical-align:top;font-family:Segoe UI,sans-serif;font-size:14px;"
        f'color:#1c1915;line-height:1.4;">'
        f"<strong>{name}</strong><br/>{title}<br/>"
        f'<a href="mailto:{email}">{email}</a> · {phone}<br/>'
        f'<span style="color:#5e574e;">stargo.co</span></td></tr></table>'
    )


def body_to_html_paragraphs(body: str) -> str:
    chunks: list[str] = []
    for block in normalize_body_paragraphs(body).split("\n\n"):
        lines = [line for line in block.split("\n") if line.strip()]
        if lines and all(line.strip().startswith(("-", "•", "*")) for line in lines):
            items = "".join(
                f"<li>{html.escape(line.lstrip('-•* ').strip())}</li>" for line in lines
            )
            chunks.append(f'<ul style="margin:0 0 12px;padding-left:20px;">{items}</ul>')
        else:
            joined = "<br/>".join(html.escape(line) for line in lines)
            chunks.append(f'<p style="margin:0 0 12px;">{joined}</p>')
    return "".join(chunks)


def split_body_and_signature(plain: str) -> tuple[str, str | None]:
    if SIGNATURE_MARKER in plain:
        body, sig = plain.split(SIGNATURE_MARKER, 1)
        return body.strip(), sig.strip()
    return plain.strip(), None


def compose_outbound_draft(
    body: str,
    *,
    owner: str | None,
    language: str,
    data_dir: Path | None,
    site_origin: str = DEFAULT_SITE_ORIGIN,
) -> tuple[str, str]:
    rep = load_sales_rep(data_dir, owner, language)
    normalized = normalize_body_paragraphs(body)
    plain = f"{normalized}{SIGNATURE_MARKER}{plain_signature(rep, language=language)}"
    logo_url = f"{site_origin.rstrip('/')}{_LOGO_PATH}"
    direction = "rtl" if language == "he" else "ltr"
    html_body = body_to_html_paragraphs(normalized) + html_signature(
        rep, language=language, logo_url=logo_url
    )
    wrapped = (
        f'<!DOCTYPE html><html><body dir="{direction}" style="font-family:Segoe UI,sans-serif;'
        f"font-size:15px;color:#1c1915;max-width:36rem;direction:{direction};text-align:"
        f'{"right" if language == "he" else "left"};">'
        f"{html_body}</body></html>"
    )
    return plain, wrapped


def draft_html_from_plain(
    plain: str,
    *,
    owner: str | None,
    language: str,
    data_dir: Path | None,
    site_origin: str = DEFAULT_SITE_ORIGIN,
) -> str:
    body, _sig = split_body_and_signature(plain)
    if not body:
        return ""
    rep = load_sales_rep(data_dir, owner, language)
    logo_url = f"{site_origin.rstrip('/')}{_LOGO_PATH}"
    direction = "rtl" if language == "he" else "ltr"
    html_body = body_to_html_paragraphs(body) + html_signature(
        rep, language=language, logo_url=logo_url
    )
    return (
        f'<!DOCTYPE html><html><body dir="{direction}" style="font-family:Segoe UI,sans-serif;'
        f"font-size:15px;color:#1c1915;max-width:36rem;direction:{direction};text-align:"
        f'{"right" if language == "he" else "left"};">'
        f"{html_body}</body></html>"
    )


def reply_subject(inbound_subject: str | None, language: str) -> str:
    if inbound_subject and inbound_subject.strip():
        subject = inbound_subject.strip()
        lower = subject.casefold()
        if not lower.startswith("re:") and not lower.startswith("fwd:"):
            return f"Re: {subject}"
        return subject
    if language == "he":
        return "Re: הפנייה שלך ל-Stargo"
    return "Re: Your note to Stargo"


def validate_compose_plain(body: str) -> None:
    """Compose URLs only carry plain text. Reject HTML or control chars."""
    text = body.strip()
    if not text:
        raise ValueError("draft is empty")
    if "<" in text and ">" in text:
        raise ValueError("draft must be plain text for mail compose")
    if "\x00" in text:
        raise ValueError("draft has invalid characters")


def decode_gmail_compose_url(url: str) -> dict[str, str]:
    """Test helper: parse a Gmail compose URL back to fields."""
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    return {
        "to": (params.get("to") or [""])[0],
        "subject": (params.get("su") or [""])[0],
        "body": (params.get("body") or [""])[0],
    }


def gmail_compose_url(*, to: str, subject: str, body: str) -> str:
    validate_compose_plain(body)
    query = urllib.parse.urlencode(
        {"view": "cm", "fs": "1", "to": to, "su": subject, "body": body},
        quote_via=urllib.parse.quote,
    )
    return f"https://mail.google.com/mail/?{query}"


def zoho_compose_url(*, to: str, subject: str, body: str) -> str:
    validate_compose_plain(body)
    query = urllib.parse.urlencode(
        {"to": to, "subject": subject, "body": body},
        quote_via=urllib.parse.quote,
    )
    return f"https://mail.zoho.com/zm/#mail/compose?{query}"


def compose_links(
    *,
    to_email: str | None,
    subject: str,
    plain_body: str,
) -> dict[str, str | None]:
    if not to_email or not to_email.strip():
        return {
            "to": None,
            "subject": subject,
            "gmail_url": None,
            "zoho_url": None,
        }
    to = to_email.strip()
    return {
        "to": to,
        "subject": subject,
        "gmail_url": gmail_compose_url(to=to, subject=subject, body=plain_body),
        "zoho_url": zoho_compose_url(to=to, subject=subject, body=plain_body),
    }
