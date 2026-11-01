"""One logger. The formatter strips email, LinkedIn, and keyed prompt or body values."""

import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

LOGGER_NAME = "revops"
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_LINKEDIN = re.compile(r"https?://(?:www\.)?linkedin\.com/\S+", re.IGNORECASE)
_BARE_LINKEDIN = re.compile(r"(?:www\.)?linkedin\.com/\S+", re.IGNORECASE)
_KEYED_SECRET = re.compile(r"(?i)\b(body|prompt|prompts)=(\S+)")

_logger = logging.getLogger(LOGGER_NAME)
if not _logger.handlers:
    _logger.addHandler(logging.NullHandler())


def redact(text: str) -> str:
    """Backstop for a call site that logs a payload. Prefer not logging it at all."""
    cleaned = _KEYED_SECRET.sub(lambda match: f"{match.group(1)}=[redacted]", text)
    cleaned = _EMAIL.sub("[redacted-email]", cleaned)
    cleaned = _LINKEDIN.sub("[redacted-linkedin]", cleaned)
    cleaned = _BARE_LINKEDIN.sub("[redacted-linkedin]", cleaned)
    return cleaned


def _request_id(record: logging.LogRecord) -> str:
    explicit = getattr(record, "request_id", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    return request_id_var.get()


class ReadableFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        moment = datetime.fromtimestamp(record.created, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        message = redact(record.getMessage())
        return f"{moment} {record.levelname} {message} request_id={_request_id(record)}"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "level": record.levelname,
            "message": redact(record.getMessage()),
            "request_id": _request_id(record),
        }
        return json.dumps(payload, ensure_ascii=True)


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging(log_dir: Path) -> None:
    """Attach the two log files. Safe to call again: old handlers are replaced."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = get_logger()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    app_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    app_handler.setFormatter(ReadableFormatter())
    error_handler = logging.FileHandler(log_dir / "error.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JsonFormatter())
    logger.addHandler(app_handler)
    logger.addHandler(error_handler)
