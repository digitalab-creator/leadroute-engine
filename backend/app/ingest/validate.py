"""The same checks for a seed row and a paste. Seed skips; paste returns 400."""

from app.clock import parse_timestamp
from app.constants import CHANNELS, KNOWN_FEEDS
from app.ingest.identity import normalize_email, normalize_linkedin
from app.ingest.records import InboundRecord


def validate_inbound(record: InboundRecord) -> list[str]:
    """Return human-readable problems. An empty list means the row can be stored."""
    errors: list[str] = []
    if not record.channel or not str(record.channel).strip():
        errors.append("channel is required")
    elif record.channel not in CHANNELS:
        errors.append("channel is not a known channel")

    body = "" if record.body is None else record.body.strip()
    if not body:
        errors.append("message text is empty")

    if record.from_email is not None and record.from_email.strip():
        try:
            normalize_email(record.from_email)
        except ValueError:
            errors.append("email shape is invalid")

    if record.linkedin_url is not None and record.linkedin_url.strip():
        try:
            normalize_linkedin(record.linkedin_url)
        except ValueError:
            errors.append("linkedin url is invalid")

    if record.received_at is not None and str(record.received_at).strip():
        try:
            parse_timestamp(record.received_at)
        except ValueError:
            errors.append("received_at is not a timestamp")

    if record.source is not None and str(record.source).strip():
        if record.source not in KNOWN_FEEDS:
            errors.append("source is not a known source")
    return errors
