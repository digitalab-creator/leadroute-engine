"""Visibility brief thumbs and fingerprint validation."""

import json

from app.main import create_app
from app.pipeline.visibility_learning import brief_fingerprint, maybe_run_weekly_visibility_learning
from app.service import record_visibility_feedback
from app.visibility.brief import brief_payload, open_visibility
from app import repo
from tests.conftest import DATA_DIR


def test_visibility_feedback_validates_fingerprint(tmp_path) -> None:
    app = create_app(
        db_path=tmp_path / "revops.sqlite",
        data_dir=DATA_DIR,
        log_dir=tmp_path / "logs",
        load_env=False,
    )

    async def _run() -> None:
        async with app.router.lifespan_context(app):
            conn = app.state.conn
            _, checked = open_visibility(DATA_DIR, None)
            payload = brief_payload(checked)
            prompt_id = str(payload["prompt_id"])
            fp = str(payload["brief_fingerprint"])
            clean = {
                key: value
                for key, value in payload.items()
                if key not in {"brief_fingerprint", "feedback_rating"}
            }
            snapshot_json = json.dumps(clean, ensure_ascii=False, sort_keys=True)
            assert fp == brief_fingerprint(prompt_id, snapshot_json)
            result = record_visibility_feedback(
                conn,
                prompt_id=prompt_id,
                brief_fingerprint=fp,
                brief_snapshot=clean,
                rating="up",
            )
            assert result["rating"] == "up"
            again = record_visibility_feedback(
                conn,
                prompt_id=prompt_id,
                brief_fingerprint=fp,
                brief_snapshot=clean,
                rating="down",
                comment="Missing Laneframe comparison",
            )
            assert again["rating"] == "down"
            rows = repo.list_visibility_feedback(conn)
            matching = [row for row in rows if row["prompt_id"] == prompt_id]
            assert len(matching) == 1
            assert matching[0]["rating"] == "down"
            assert matching[0]["comment"] == "Missing Laneframe comparison"

    import asyncio

    asyncio.run(_run())


def test_weekly_visibility_learning_marks_week_without_llm(tmp_path) -> None:
    app = create_app(
        db_path=tmp_path / "revops.sqlite",
        data_dir=DATA_DIR,
        log_dir=tmp_path / "logs",
        load_env=False,
    )

    async def _run() -> None:
        async with app.router.lifespan_context(app):
            conn = app.state.conn
            repo.upsert_visibility_feedback(
                conn,
                feedback_id="VF-1",
                prompt_id="P-001",
                brief_fingerprint="abc",
                brief_snapshot_json='{"title":"x"}',
                rating="down",
                created_at="2026-11-01T10:00:00+02:00",
            )
            conn.commit()
            maybe_run_weekly_visibility_learning(conn, DATA_DIR, None)
            state = repo.get_visibility_learning_state(conn)
            assert state is not None
            assert state["last_week_key"]

    import asyncio

    asyncio.run(_run())
