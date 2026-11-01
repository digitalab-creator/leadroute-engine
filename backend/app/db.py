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
    connection.commit()
