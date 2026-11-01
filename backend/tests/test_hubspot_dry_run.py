"""HubSpot dry-run payloads — shape and mapping, no network."""

import json

from app.integrations.hubspot_dry_run import build_hubspot_dry_run
from app.main import create_app
from tests.conftest import DATA_DIR


def test_hubspot_dry_run_after_seed(tmp_path) -> None:
    app = create_app(
        db_path=tmp_path / "revops.sqlite",
        data_dir=DATA_DIR,
        log_dir=tmp_path / "logs",
        load_env=False,
    )

    async def _run() -> None:
        async with app.router.lifespan_context(app):
            conn = app.state.conn
            payload = build_hubspot_dry_run(conn)
            assert payload["dry_run"] is True
            assert payload["portal_calls"] == 0
            assert len(payload["requests"]) > 0
            sample = payload["requests"][0]
            assert sample["method"] == "PATCH"
            assert "/crm/v3/objects/contacts/" in sample["url"]
            props = sample["body"]["properties"]
            assert "lead_status" in props
            assert "stargo_priority_score" in props
            assert "hubspot_owner_id" in props or sample["meta"]["engine_owner_name"] is None
            encoded = json.dumps(payload)
            assert "api.hubapi.com" in encoded

    import asyncio

    asyncio.run(_run())
