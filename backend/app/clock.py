"""Timestamps and the reporting week. Every comparison goes through here."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.constants import REPORTING_TIMEZONE, WEEK_END_DATE, WEEK_START_DATE

JERUSALEM = ZoneInfo(REPORTING_TIMEZONE)

WEEK_START = datetime(
    WEEK_START_DATE[0],
    WEEK_START_DATE[1],
    WEEK_START_DATE[2],
    0,
    0,
    0,
    0,
    tzinfo=JERUSALEM,
)
# Thursday 23:59:59.999 in Asia/Jerusalem. Inclusive.
WEEK_END = datetime(
    WEEK_END_DATE[0],
    WEEK_END_DATE[1],
    WEEK_END_DATE[2],
    23,
    59,
    59,
    999000,
    tzinfo=JERUSALEM,
)


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp. A date with no clock is midnight in Jerusalem.

    Naive timestamps are rejected. We do not assume the laptop's timezone.
    """
    text = value.strip()
    if not text:
        raise ValueError("timestamp is empty")
    if "T" not in text:
        try:
            day = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("received_at is not a timestamp") from exc
        if day.tzinfo is not None:
            raise ValueError("received_at is not a timestamp")
        return day.replace(tzinfo=JERUSALEM)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("received_at is not a timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("received_at is not a timestamp")
    return parsed


def to_jerusalem(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("timestamp needs a timezone")
    return moment.astimezone(JERUSALEM)


def in_reporting_week(moment: datetime) -> bool:
    local = to_jerusalem(moment)
    return WEEK_START <= local <= WEEK_END


def calendar_week_key(moment: datetime | None = None) -> str:
    """ISO week in Asia/Jerusalem, for the draft-learning schedule."""
    if moment is None:
        moment = datetime.now(JERUSALEM)
    local = to_jerusalem(moment)
    year, week, _ = local.isocalendar()
    return f"{year}-W{week:02d}"
