"""Open SQLite and apply the one schema file."""

import sqlite3
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(_SCHEMA.read_text(encoding="utf-8"))
    _ensure_feedback_comment_columns(connection)
    connection.commit()


def _ensure_feedback_comment_columns(connection: sqlite3.Connection) -> None:
    for table in ("draft_feedback", "visibility_feedback"):
        columns = {
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if "comment" not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN comment TEXT NOT NULL DEFAULT ''"
            )
