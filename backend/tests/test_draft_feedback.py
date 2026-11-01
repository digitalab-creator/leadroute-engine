"""Draft thumbs and weekly learning state."""

from app.main import create_app
from app.pipeline.draft_learning import maybe_run_weekly_draft_learning
from app.service import record_draft_feedback
from app import repo
from tests.conftest import DATA_DIR


def test_draft_feedback_upserts_for_same_draft(tmp_path) -> None:
    app = create_app(
        db_path=tmp_path / "revops.sqlite",
        data_dir=DATA_DIR,
        log_dir=tmp_path / "logs",
        load_env=False,
    )

    async def _run() -> None:
        async with app.router.lifespan_context(app):
            conn = app.state.conn
            qual = repo.get_qualification(conn, "HS-1017")
            assert qual is not None
            draft = str(qual["draft"] or "seed draft")
            repo.save_qualification(
                conn,
                person_id="HS-1017",
                status=str(qual["status"]),
                owner=qual["owner"],
                score=int(qual["score"]),
                band=str(qual["band"]),
                breakdown_json=str(qual["breakdown_json"]),
                conditions_json=str(qual["conditions_json"]),
                rationale=str(qual["rationale"]),
                draft=draft,
                draft_state=str(qual["draft_state"]),
                analysis_mode=str(qual["analysis_mode"]),
                expansion=bool(qual["expansion"]),
                qualified=bool(qual["qualified"]),
            )
            conn.commit()
            first = record_draft_feedback(conn, person_id="HS-1017", rating="up")
            assert first["rating"] == "up"
            second = record_draft_feedback(
                conn, person_id="HS-1017", rating="down", comment="Too generic opening"
            )
            assert second["rating"] == "down"
            rows = repo.list_draft_feedback(conn)
            matching = [row for row in rows if row["person_id"] == "HS-1017"]
            assert len(matching) == 1
            assert matching[0]["rating"] == "down"
            assert matching[0]["comment"] == "Too generic opening"
            assert "person" in str(matching[0]["client_context_json"])

    import asyncio

    asyncio.run(_run())


def test_weekly_learning_marks_week_without_llm(tmp_path) -> None:
    app = create_app(
        db_path=tmp_path / "revops.sqlite",
        data_dir=DATA_DIR,
        log_dir=tmp_path / "logs",
        load_env=False,
    )

    async def _run() -> None:
        async with app.router.lifespan_context(app):
            conn = app.state.conn
            repo.upsert_draft_feedback(
                conn,
                feedback_id="DF-1",
                person_id="HS-1017",
                draft_text="x",
                rating="down",
                created_at="2026-11-01T10:00:00+02:00",
                inbound_id="IN-012",
                client_context_json='{"person":{}}',
            )
            conn.commit()
            maybe_run_weekly_draft_learning(conn, DATA_DIR, None)
            state = repo.get_writer_learning_state(conn)
            assert state is not None
            assert state["last_week_key"]

    import asyncio

    asyncio.run(_run())


def test_writer_payload_includes_full_context(tmp_path) -> None:
    from app.brand_docs import read_brand_context
    from app.pipeline.writer_brief import WriterInput, build_writer_payload

    brand = read_brand_context(DATA_DIR)
    payload = build_writer_payload(
        WriterInput(
            inbound_id="IN-012",
            language="he",
            message_body="test",
            problem_quote="q",
            intent="positive_reply",
            stated_problem="rate_quoting",
            client_context_json='{"person":{"company_name":"Ashdod"}}',
            brand_context_markdown=brand,
            learned_addendum="Mirror WhatsApp volume.",
        )
    )
    assert "BC-1" in payload["brand_context_markdown"]
    assert "Ashdod" in payload["client_context_json"]
    assert "WhatsApp" in payload["goals"]
