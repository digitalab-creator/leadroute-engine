"""The paths the React screens call. One module, so a missing route fails here."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError

from app import repo
from app.logging_config import get_logger
from app.labels import label_status
from app.present import (
    decision_note,
    kpi_payload,
    lead_payload,
    now_israel,
    options_payload,
    queue_payload,
)
from app.service import (
    InboundRejected,
    paste_inbound,
    record_draft_feedback,
    record_sales_decision,
    record_visibility_feedback,
    refresh_draft_on_view,
    save_draft_edit,
)
from app.visibility.brief import build_visibility
from app.integrations.hubspot_dry_run import build_hubspot_dry_run
from app.eval.qualifier_eval import run_qualifier_eval

logger = get_logger()


class PasteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_name: str = ""
    from_email: str | None = None
    linkedin_url: str | None = None
    channel: str | None = None
    text: str | None = None
    received_at: str | None = None
    source: str | None = None


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    decided_at: str | None = None


class DraftFeedbackBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: str
    comment: str | None = None


class DraftEditBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: str


class VisibilityFeedbackBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_id: str
    brief_fingerprint: str
    brief_snapshot: dict[str, object]
    rating: str
    comment: str | None = None


def register_routes(app: FastAPI) -> None:
    @app.get("/health")
    def health() -> dict[str, str]:
        client = getattr(app.state, "client", None)
        return {"status": "ok", "llm": "gemini" if client is not None else "off"}

    @app.get("/api/options")
    def options() -> dict[str, object]:
        return options_payload()

    @app.get("/api/leads")
    def leads() -> dict[str, object]:
        return queue_payload(app.state.conn)

    @app.get("/api/leads/{person_id}")
    def lead(person_id: str) -> dict[str, object]:
        refresh_draft_on_view(
            app.state.conn,
            person_id,
            app.state.client,
            data_dir=app.state.data_dir,
        )
        payload = lead_payload(
            app.state.conn, person_id, data_dir=app.state.data_dir
        )
        if payload is None:
            raise HTTPException(status_code=404, detail=["lead not found"])
        return payload

    @app.post("/api/leads/{person_id}/decision")
    def decide(person_id: str, body: DecisionBody) -> dict[str, object]:
        if repo.get_person(app.state.conn, person_id) is None:
            raise HTTPException(status_code=404, detail=["lead not found"])
        decided_at = body.decided_at.strip() if body.decided_at else now_israel()
        if not decided_at:
            raise InboundRejected(["decided_at is not a timestamp"])
        try:
            saved = record_sales_decision(
                app.state.conn,
                person_id=person_id,
                decision=body.decision,
                decided_at=decided_at,
                replace=True,
                client=app.state.client,
                data_dir=app.state.data_dir,
            )
        except InboundRejected as exc:
            raise HTTPException(status_code=400, detail=exc.errors) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=["decided_at is not a timestamp"]
            ) from exc
        owner = saved["owner"]
        status = str(saved["status"])
        return {
            "person_id": person_id,
            "status": status,
            "status_label": label_status(status),
            "owner": None if owner is None else str(owner),
            "score": int(saved["score"]),
            "band": str(saved["band"]),
            "decided_at": decided_at,
            "decision": body.decision.strip().casefold(),
            "note": decision_note(
                decision=body.decision.strip().casefold(),
                decided_at=decided_at,
                status=status,
            ),
        }

    @app.post("/api/leads/{person_id}/draft-feedback")
    def draft_feedback(person_id: str, body: DraftFeedbackBody) -> dict[str, object]:
        if repo.get_person(app.state.conn, person_id) is None:
            raise HTTPException(status_code=404, detail=["lead not found"])
        try:
            saved = record_draft_feedback(
                app.state.conn,
                person_id=person_id,
                rating=body.rating,
                comment=body.comment,
            )
        except InboundRejected as exc:
            raise HTTPException(status_code=400, detail=exc.errors) from exc
        return {
            "person_id": person_id,
            "rating": saved["rating"],
            "recorded_at": saved["recorded_at"],
        }

    @app.put("/api/leads/{person_id}/draft")
    def save_draft(person_id: str, body: DraftEditBody) -> dict[str, object]:
        if repo.get_person(app.state.conn, person_id) is None:
            raise HTTPException(status_code=404, detail=["lead not found"])
        try:
            saved = save_draft_edit(
                app.state.conn,
                person_id=person_id,
                draft_text=body.draft,
                data_dir=app.state.data_dir,
            )
        except InboundRejected as exc:
            raise HTTPException(status_code=400, detail=exc.errors) from exc
        from app.labels import label_draft_state

        return {
            **saved,
            "draft_state_label": label_draft_state(str(saved["draft_state"])),
        }

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
                data_dir=app.state.data_dir,
            )
        except InboundRejected as exc:
            raise HTTPException(status_code=400, detail=exc.errors) from exc
        owner = saved["owner"]
        status = str(saved["status"])
        return {
            "person_id": str(saved["person_id"]),
            "status": status,
            "status_label": label_status(status),
            "owner": None if owner is None else str(owner),
            "score": int(saved["score"]),
            "band": str(saved["band"]),
            "analysis_mode": str(saved["analysis_mode"]),
        }

    @app.get("/api/kpi")
    def kpi() -> dict[str, object]:
        return kpi_payload(app.state.conn)

    @app.get("/api/integrations/hubspot/dry-run")
    def hubspot_dry_run() -> dict[str, object]:
        """CRM v3 PATCH payloads for contact lead status and owner. No portal call."""
        return build_hubspot_dry_run(app.state.conn)

    @app.get("/api/eval/qualifier")
    def qualifier_eval() -> dict[str, object]:
        """Labelled QL gate eval set vs ql_standard.md. No LLM."""
        try:
            return run_qualifier_eval(app.state.data_dir)
        except FileNotFoundError:
            raise HTTPException(
                status_code=500, detail=["qualifier_eval.json is missing"]
            ) from None
        except ValidationError:
            raise HTTPException(
                status_code=500,
                detail=["qualifier_eval.json does not match the schema"],
            ) from None

    @app.get("/api/visibility")
    def visibility() -> dict[str, object]:
        try:
            return build_visibility(
                app.state.data_dir, app.state.client, app.state.conn
            )
        except FileNotFoundError:
            logger.error("visibility_source_missing")
            raise HTTPException(
                status_code=500, detail=["visibility source file is missing"]
            ) from None
        except (ValidationError, ValueError):
            logger.error("visibility_file_invalid")
            raise HTTPException(
                status_code=500,
                detail=["visibility file does not match the schema"],
            ) from None

    @app.post("/api/visibility/feedback")
    def visibility_feedback(body: VisibilityFeedbackBody) -> dict[str, object]:
        try:
            saved = record_visibility_feedback(
                app.state.conn,
                prompt_id=body.prompt_id,
                brief_fingerprint=body.brief_fingerprint,
                brief_snapshot=body.brief_snapshot,
                rating=body.rating,
                comment=body.comment,
            )
        except InboundRejected as exc:
            raise HTTPException(status_code=400, detail=exc.errors) from exc
        return dict(saved)


def mount_screens(app: FastAPI, dist: Path) -> None:
    """Serve the built React app when frontend/dist exists. Dev uses Vite instead."""
    index = dist / "index.html"
    if not index.is_file():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def screens(full_path: str) -> FileResponse:
        if full_path:
            candidate = (dist / full_path).resolve()
            root = dist.resolve()
            if candidate.is_file() and root in candidate.parents:
                return FileResponse(candidate)
        return FileResponse(index)
