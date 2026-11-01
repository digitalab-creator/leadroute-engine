"""Once per calendar week: read thumb feedback and update writer rules."""

import json
from datetime import datetime
from pathlib import Path

import sqlite3
from pydantic import BaseModel, ConfigDict, Field

from app.brand_docs import read_brand_context
from app.clock import JERUSALEM, calendar_week_key
from app.logging_config import get_logger
from app.pipeline.extract import CompletionClient
from app import repo

logger = get_logger()


class LearningOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    addendum: str = Field(min_length=1)
    summary: str = Field(min_length=1)


def _feedback_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return repo.list_draft_feedback(connection)


def maybe_run_weekly_draft_learning(
    connection: sqlite3.Connection,
    data_dir: Path,
    client: CompletionClient | None,
) -> None:
    """Run at most once per ISO week when there is feedback to learn from."""
    week = calendar_week_key(datetime.now(JERUSALEM))
    state = repo.get_writer_learning_state(connection)
    if state is not None and str(state["last_week_key"]) == week:
        return
    rows = _feedback_rows(connection)
    if not rows:
        repo.save_writer_learning_state(
            connection,
            week_key=week,
            addendum="" if state is None else str(state["addendum"]),
            summary_json=str(state["summary_json"]) if state else "{}",
            analyzed_at=datetime.now(JERUSALEM).isoformat(timespec="seconds"),
        )
        connection.commit()
        return
    if client is None:
        logger.info("draft_learning_skipped reason=no_llm week=%s", week)
        return
    brand = read_brand_context(data_dir)
    prior = "" if state is None else str(state["addendum"])
    samples: list[dict[str, str]] = []
    for row in rows[-40:]:
        note = row["comment"]
        comment = "" if note is None else str(note).strip()
        sample: dict[str, str] = {
            "rating": str(row["rating"]),
            "draft_text": str(row["draft_text"])[:800],
            "client_context_json": str(row["client_context_json"])[:1200],
        }
        if comment:
            sample["comment"] = comment[:500]
        samples.append(sample)
    try:
        raw = client.complete_json(
            role="draft_learning",
            user_payload={
                "calendar_week": week,
                "prior_addendum": prior,
                "brand_context": brand[:8000] if brand else "",
                "feedback_samples": json.dumps(samples, ensure_ascii=False),
                "task": (
                    "Return JSON with addendum and summary. "
                    "The addendum is extra writer rules learned from thumbs-up vs thumbs-down "
                    "drafts. Keep BC-5 and BC-6. Do not contradict forbidden claims. "
                    "Be specific: what to mirror, what to avoid, how to open and close. "
                    "When feedback_samples include comment, use those notes from reps. "
                    "Under 400 words."
                ),
            },
        )
        parsed = LearningOutput.model_validate_json(raw)
    except Exception as exc:
        logger.warning(
            "draft_learning_failed week=%s error_type=%s",
            week,
            type(exc).__name__,
        )
        return
    repo.save_writer_learning_state(
        connection,
        week_key=week,
        addendum=parsed.addendum,
        summary_json=json.dumps({"summary": parsed.summary, "sample_count": len(samples)}),
        analyzed_at=datetime.now(JERUSALEM).isoformat(timespec="seconds"),
    )
    connection.commit()
    logger.info("draft_learning_saved week=%s samples=%s", week, len(samples))


def writer_addendum(connection: sqlite3.Connection) -> str:
    state = repo.get_writer_learning_state(connection)
    if state is None:
        return ""
    return str(state["addendum"]).strip()
