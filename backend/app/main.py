"""HTTP entry. Screens arrive in the next phase. This slice serves health and paste."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.db import apply_schema, connect
from app.logging_config import configure_logging, get_logger
from app.pipeline.gemini import GeminiClient
from app.service import InboundRejected, load_seed, paste_inbound

logger = get_logger()

_ALLOWED_ENV = {
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "LEADROUTE_DB_PATH",
    "LEADROUTE_DATA_DIR",
    "LEADROUTE_LOG_DIR",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_local_env(path: Path) -> None:
    """Read an allowlist from .env. Values already in the process win. Nothing is logged."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        if key in _ALLOWED_ENV and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _client_from_env() -> GeminiClient | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    return GeminiClient(key, model)


class PasteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_name: str = ""
    from_email: str | None = None
    linkedin_url: str | None = None
    channel: str | None = None
    text: str | None = None
    received_at: str | None = None
    source: str | None = None


def create_app(
    db_path: Path | None = None,
    data_dir: Path | None = None,
    log_dir: Path | None = None,
    *,
    load_env: bool = True,
) -> FastAPI:
    root = repo_root()
    if load_env:
        load_local_env(root / ".env")
    database = db_path or Path(os.environ.get("LEADROUTE_DB_PATH", root / "var" / "revops.sqlite"))
    pack = data_dir or Path(os.environ.get("LEADROUTE_DATA_DIR", root / "data"))
    logs = log_dir or Path(os.environ.get("LEADROUTE_LOG_DIR", root / "logs"))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(logs)
        app.state.conn = connect(database)
        apply_schema(app.state.conn)
        app.state.client = _client_from_env()
        if app.state.conn.execute("SELECT COUNT(*) AS n FROM persons").fetchone()["n"] == 0:
            load_seed(app.state.conn, pack, None)
        logger.info("app_started")
        yield
        app.state.conn.close()

    app = FastAPI(title="LeadRoute", lifespan=lifespan)

    @app.exception_handler(InboundRejected)
    async def rejected(_request: object, exc: InboundRejected) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.errors})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/inbound")
    def post_inbound(body: PasteBody) -> dict[str, object]:
        try:
            saved = paste_inbound(
                app.state.conn,
                from_name=body.from_name,
                channel=body.channel,
                text=body.text,
                from_email=body.from_email,
                linkedin_url=body.linkedin_url,
                received_at=body.received_at,
                source=body.source,
                client=app.state.client,
            )
        except InboundRejected as exc:
            raise HTTPException(status_code=400, detail=exc.errors) from exc
        return {
            "person_id": saved["person_id"],
            "status": saved["status"],
            "owner": saved["owner"],
            "score": saved["score"],
            "band": saved["band"],
            "analysis_mode": saved["analysis_mode"],
        }

    return app


app = create_app()
