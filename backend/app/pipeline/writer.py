"""Draft words. The status, score, and owner never come from here.

The whole reply is in the inbound language. Sales context comes from writer_brief.
"""

from app.labels import draft_matches_language
from app.logging_config import get_logger
from app.pipeline.extract import CompletionClient
from app.pipeline.schemas import WriterOutput
from app.pipeline.writer_brief import (
    WriterInput,
    build_writer_payload,
    draft_grounds_buyer_words,
    draft_has_generic_filler,
)

logger = get_logger()

# Used only when no model client is configured. Each string is one language.
_WITH_QUOTE = {
    "en": (
        'Thanks for writing. On "{quote}"—we help pricing teams draft quotes from '
        "tariffs and contracts, and a person on our team approves before anything sends."
    ),
    "he": (
        'תודה שכתבת. לגבי "{quote}"—אנחנו עוזרים לצוות התמחור לטיוט הצעות מחיר '
        "מתעריפים וחוזים, ואדם מהצוות מאשר לפני שמשהו יוצא."
    ),
    "nl": (
        'Bedankt voor je bericht. Over "{quote}"—we helpen pricingteams offertes '
        "concepten uit tarieven en contracten; iemand uit het team keurt goed voordat "
        "er iets verstuurd wordt."
    ),
}
_PLAIN = {
    "en": "Thanks for writing. A person on our team will follow up. Nothing is sent automatically.",
    "he": "תודה שכתבת. מישהו מהצוות יחזור אליך. שום דבר לא נשלח אוטומטית.",
    "nl": "Bedankt voor je bericht. Iemand uit het team neemt contact op. Er wordt niets automatisch verstuurd.",
}

_HYPE = frozenset(
    {
        "revolutionary",
        "game-changing",
        "game changing",
        "cutting-edge",
        "cutting edge",
        "transformative",
        "מהפכני",
        "פורץ דרך",
    }
)


def template_draft(problem_quote: str | None, language: str) -> str | None:
    """A same-language stand-in. None when we have no template for that language."""
    if problem_quote:
        pattern = _WITH_QUOTE.get(language)
        if pattern is None:
            return None
        clipped = problem_quote if len(problem_quote) <= 180 else problem_quote[:177] + "..."
        return pattern.replace("{quote}", clipped)
    return _PLAIN.get(language)


def draft_passes_guardrails(draft: str) -> bool:
    """Drop obvious BC-6 / voice violations without open-text classification."""
    lowered = draft.casefold()
    if any(token in lowered for token in _HYPE):
        return False
    if draft_has_generic_filler(draft):
        return False
    return True


def _template_fallback(fields: WriterInput) -> tuple[str | None, str]:
    text = template_draft(fields.problem_quote, fields.language)
    if text is None or not draft_matches_language(text, fields.language):
        return None, "unavailable"
    return text, "template"


def writer_draft(
    client: CompletionClient | None,
    *,
    allowed: bool,
    fields: WriterInput,
) -> tuple[str | None, str]:
    """Return the draft text and a label: template, writer, unavailable, or not_applicable."""
    if not allowed:
        return None, "not_applicable"
    if client is None:
        text = template_draft(fields.problem_quote, fields.language)
        if text is None or not draft_matches_language(text, fields.language):
            return None, "unavailable"
        return text, "template"
    try:
        raw = client.complete_json(
            role="writer",
            user_payload=build_writer_payload(fields),
        )
        parsed = WriterOutput.model_validate_json(raw)
    except Exception as exc:
        logger.warning(
            "writer_failed inbound_id=%s error_type=%s",
            fields.inbound_id,
            type(exc).__name__,
        )
        return None, "unavailable"
    if not parsed.draft or not draft_matches_language(parsed.draft, fields.language):
        logger.warning(
            "writer_language_mismatch inbound_id=%s language=%s",
            fields.inbound_id,
            fields.language,
        )
        return _template_fallback(fields)
    if not draft_passes_guardrails(parsed.draft):
        logger.warning(
            "writer_voice_rejected inbound_id=%s reason=generic_or_hype",
            fields.inbound_id,
        )
        return _template_fallback(fields)
    if not draft_grounds_buyer_words(
        parsed.draft,
        problem_quote=fields.problem_quote,
        message_body=fields.message_body,
    ):
        logger.warning(
            "writer_grounding_rejected inbound_id=%s reason=no_buyer_words",
            fields.inbound_id,
        )
        return _template_fallback(fields)
    return parsed.draft, "writer"
