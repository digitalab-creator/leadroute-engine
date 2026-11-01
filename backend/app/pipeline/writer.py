"""Draft words. The status, score, and owner never come from here."""

from app.logging_config import get_logger
from app.pipeline.extract import CompletionClient
from app.pipeline.schemas import WriterOutput

logger = get_logger()


def template_draft(problem_quote: str | None) -> str:
    if problem_quote:
        clipped = problem_quote if len(problem_quote) <= 180 else problem_quote[:177] + "..."
        return (
            "Thanks for writing. We can look at this with you: "
            f"\"{clipped}\". A person on our team sends the reply."
        )
    return "Thanks for writing. A person on our team will follow up. Nothing is sent automatically."


def writer_draft(
    client: CompletionClient | None,
    *,
    allowed: bool,
    problem_quote: str | None,
    inbound_id: str,
) -> tuple[str | None, str]:
    """Return the draft text and a label: template, writer, unavailable, or not_applicable."""
    if not allowed:
        return None, "not_applicable"
    if client is None:
        return template_draft(problem_quote), "template"
    try:
        raw = client.complete_json(
            role="writer",
            user_payload={
                "inbound_id": inbound_id,
                "task": "Write a short unsent reply. Do not decide status, score, or owner.",
            },
        )
        parsed = WriterOutput.model_validate_json(raw)
    except Exception as exc:
        logger.warning(
            "writer_failed inbound_id=%s error_type=%s",
            inbound_id,
            type(exc).__name__,
        )
        return None, "unavailable"
    return parsed.draft, "writer"
