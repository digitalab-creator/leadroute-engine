"""Once per calendar week: visibility brief thumbs → extra GEO rules."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import sqlite3

from app.brand_docs import read_brand_context
from app.clock import JERUSALEM, calendar_week_key
from app.logging_config import get_logger
from app.pipeline.draft_learning import LearningOutput
from app.pipeline.extract import CompletionClient
from app import repo

logger = get_logger()


def brief_fingerprint(prompt_id: str, snapshot_json: str) -> str:
    digest = hashlib.sha256(f"{prompt_id}\n{snapshot_json}".encode("utf-8")).hexdigest()
    return digest[:20]


def maybe_run_weekly_visibility_learning(
    connection: sqlite3.Connection,
    data_dir: Path,
    client: CompletionClient | None,
) -> None:
    week = calendar_week_key(datetime.now(JERUSALEM))
    state = repo.get_visibility_learning_state(connection)
    if state is not None and str(state["last_week_key"]) == week:
        return
    rows = repo.list_visibility_feedback(connection)
    if not rows:
        repo.save_visibility_learning_state(
            connection,
            week_key=week,
            addendum="" if state is None else str(state["addendum"]),
            summary_json=str(state["summary_json"]) if state else "{}",
            analyzed_at=datetime.now(JERUSALEM).isoformat(timespec="seconds"),
        )
        connection.commit()
        return
    if client is None:
        logger.info("visibility_learning_skipped reason=no_llm week=%s", week)
        return
    brand = read_brand_context(data_dir)
    prior = "" if state is None else str(state["addendum"])
    samples: list[dict[str, str]] = []
    for row in rows[-40:]:
        note = row["comment"]
        comment = "" if note is None else str(note).strip()
        sample: dict[str, str] = {
            "rating": str(row["rating"]),
            "prompt_id": str(row["prompt_id"]),
            "brief_snapshot_json": str(row["brief_snapshot_json"])[:2000],
        }
        if comment:
            sample["comment"] = comment[:500]
        samples.append(sample)
    try:
        raw = client.complete_json(
            role="visibility_learning",
            user_payload={
                "calendar_week": week,
                "prior_addendum": prior,
                "brand_context": brand[:8000] if brand else "",
                "feedback_samples": json.dumps(samples, ensure_ascii=False),
                "task": (
                    "Return JSON with addendum and summary. "
                    "The addendum is extra rules for AI visibility GEO briefs learned from "
                    "thumbs-up vs thumbs-down briefs. Every factual sentence must still end "
                    "with a real [BC-*] or [PP-*] id. direct_answer stays 40 to 60 words. "
                    "When feedback_samples include comment, use those notes from readers. "
                    "Under 400 words."
                ),
            },
        )
        parsed = LearningOutput.model_validate_json(raw)
    except Exception as exc:
        logger.warning(
            "visibility_learning_failed week=%s error_type=%s",
            week,
            type(exc).__name__,
        )
        return
    repo.save_visibility_learning_state(
        connection,
        week_key=week,
        addendum=parsed.addendum,
        summary_json=json.dumps({"summary": parsed.summary, "sample_count": len(samples)}),
        analyzed_at=datetime.now(JERUSALEM).isoformat(timespec="seconds"),
    )
    connection.commit()
    logger.info("visibility_learning_saved week=%s samples=%s", week, len(samples))


def visibility_addendum(connection: sqlite3.Connection) -> str:
    state = repo.get_visibility_learning_state(connection)
    if state is None:
        return ""
    return str(state["addendum"]).strip()
