"""HTTP entry. Builds the app, tags each request, and serves the screens if built.

The routes live in app.api.routes. This file owns startup: env, database, seed, logs.
"""

import os
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import mount_screens, register_routes
from app.db import apply_schema, connect
from app.logging_config import configure_logging, get_logger, request_id_var
from app.pipeline.gemini import GeminiClient
from app import repo
from app.service import InboundRejected, load_seed, repair_template_language
from app.pipeline.draft_learning import maybe_run_weekly_draft_learning
from app.pipeline.visibility_learning import maybe_run_weekly_visibility_learning

logger = get_logger()

_ALLOWED_ENV = {
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "LEADROUTE_DB_PATH",
    "LEADROUTE_DATA_DIR",
    "LEADROUTE_LOG_DIR",
    "LEADROUTE_SITE_ORIGIN",
}

_LOCAL_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


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


def client_from_env() -> GeminiClient | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
    return GeminiClient(key, model)


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
        app.state.data_dir = pack
        apply_schema(app.state.conn)
        app.state.client = client_from_env()
        if app.state.conn.execute("SELECT COUNT(*) AS n FROM persons").fetchone()["n"] == 0:
            load_seed(app.state.conn, pack, None)
        repo.rearm_unavailable_drafts(app.state.conn)
        if app.state.client is None:
            repair_template_language(app.state.conn)
        maybe_run_weekly_draft_learning(
            app.state.conn, pack, app.state.client
        )
        maybe_run_weekly_visibility_learning(
            app.state.conn, pack, app.state.client
        )
        app.state.conn.commit()
        logger.info("app_started llm=%s", "gemini" if app.state.client is not None else "off")
        yield
        app.state.conn.close()

    app = FastAPI(title="LeadRoute", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_LOCAL_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        token = request_id_var.set(uuid.uuid4().hex[:12])
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        logger.info(
            "request method=%s path=%s status=%s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    @app.exception_handler(InboundRejected)
    async def rejected(_request: object, exc: InboundRejected) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.errors})

    register_routes(app)
    mount_screens(app, root / "frontend" / "dist")
    return app


_CLI_THAT_MUST_NOT_BOOT = frozenset(
    {"export_kpi.py", "export_hubspot.py", "run_qualifier_eval.py"}
)


def _asgi_app() -> FastAPI:
    """Uvicorn needs a live app. Tests and the export commands must not boot one on import.

    A boot reads `.env`, opens the product database, and may call Gemini.
    """
    invoked = Path(sys.argv[0]).name if sys.argv else ""
    skip = "pytest" in sys.modules or invoked in _CLI_THAT_MUST_NOT_BOOT
    if skip:
        return FastAPI(title="LeadRoute")
    return create_app()


app = _asgi_app()
