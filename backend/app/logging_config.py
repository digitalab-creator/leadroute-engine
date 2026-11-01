"""One logger. The formatter strips email addresses and LinkedIn URLs."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

LOGGER_NAME = "revops"

_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_LINKEDIN = re.compile(r"https?://(?:www\.)?linkedin\.com/\S+", re.IGNORECASE)
_BARE_LINKEDIN = re.compile(r"(?:www\.)?linkedin\.com/\S+", re.IGNORECASE)

_logger = logging.getLogger(LOGGER_NAME)
if not _logger.handlers:
    _logger.addHandler(logging.NullHandler())


def redact(text: str) -> str:
    cleaned = _EMAIL.sub("[redacted-email]", text)
    cleaned = _LINKEDIN.sub("[redacted-linkedin]", cleaned)
    cleaned = _BARE_LINKEDIN.sub("[redacted-linkedin]", cleaned)
    return cleaned


class ReadableFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        moment = datetime.fromtimestamp(record.created, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        message = redact(record.getMessage())
        request_id = getattr(record, "request_id", "-")
        return f"{moment} {record.levelname} {message} request_id={request_id}"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "level": record.levelname,
            "message": redact(record.getMessage()),
            "request_id": getattr(record, "request_id", "-"),
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
