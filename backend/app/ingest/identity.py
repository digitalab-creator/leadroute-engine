"""Match a person by email or LinkedIn. Company domains use the public suffix list."""

import re
from urllib.parse import urlparse

import tldextract

from app.constants import FREE_MAIL_DOMAINS

# Bundled suffix list only. Tests and seed load must not fetch the public list.
_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str | None) -> str | None:
    """Lower-case a valid mailbox. Blank is missing. A bad shape is an error."""
    if value is None:
        return None
    text = value.strip().lower()
    if not text:
        return None
    if _EMAIL_SHAPE.fullmatch(text) is None:
        raise ValueError("email shape is invalid")
    return text


def email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return registered_domain(email.split("@", 1)[1])


def normalize_linkedin(value: str | None) -> str | None:
    """Return the lower-case /in/ slug, or None when the field is blank.

    A non-blank value that is not a personal profile is an error.
    www, trailing slash, and letter case do not make a second person.
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "linkedin.com":
        raise ValueError("linkedin url is invalid")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0].lower() != "in":
        raise ValueError("linkedin url is invalid")
    slug = parts[1].strip().lower()
    if not slug:
        raise ValueError("linkedin url is invalid")
    return slug


def registered_domain(host: str | None) -> str | None:
    """Lower-case registrable domain. www and other subdomains are removed.

    Multi-part suffixes such as .co.uk, .com.sg, and .co.il stay on the domain.
    """
    if host is None:
        return None
    text = host.strip().lower()
    if not text:
        return None
    if "://" in text:
        text = urlparse(text).hostname or ""
    text = text.strip(".")
    if text.startswith("www."):
        text = text[4:]
    extracted = _EXTRACTOR(text)
    if not extracted.domain or not extracted.suffix:
        return None
    return f"{extracted.domain}.{extracted.suffix}"


def is_free_mail(domain: str | None) -> bool:
    return domain in FREE_MAIL_DOMAINS


def company_domain_from_email(email: str | None) -> str | None:
    """Corporate mailbox domain. Free-mail domains do not name a company."""
    domain = email_domain(email)
    if domain is None or is_free_mail(domain):
        return None
    return domain
