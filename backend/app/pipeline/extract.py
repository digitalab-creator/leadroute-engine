"""Turn one message into evidence. A broken model call stops here."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.constants import Intent, Pain
from app.logging_config import get_logger
from app.pipeline.injection import find_instruction
from app.pipeline.lexicon import (
    INDUSTRY_SURFACES,
    INTENT_PRIORITY,
    INTENT_SURFACES,
    PAIN_SURFACES,
    ROLE_SURFACES,
    country_in_text,
    find_phrase,
)
from app.pipeline.quotes import extraction_is_grounded
from app.pipeline.schemas import Extraction

logger = get_logger()

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "extractions.json"
_EMPLOYEES = re.compile(
    r"(\d{1,7})\s*[- ]?\s*(?:person|people|employee|employees)\b",
    re.IGNORECASE,
)
_fixtures: dict[str, dict[str, object]] | None = None


class CompletionClient(Protocol):
    def complete_json(self, *, role: str, user_payload: dict[str, str]) -> str:
        """Return a JSON string. Must not log user_payload."""


@dataclass(frozen=True)
class ExtractOutcome:
    failed: bool
    injection: bool
    mode: str
    extraction: Extraction | None


def load_fixtures() -> dict[str, dict[str, object]]:
    global _fixtures
    if _fixtures is None:
        _fixtures = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return _fixtures


def _language(message: str) -> str:
    letters = [char for char in message if char.isalpha()]
    if not letters:
        return "und"
    hebrew = sum(1 for char in letters if "\u0590" <= char <= "\u05FF")
    if hebrew / len(letters) >= 0.3:
        return "he"
    return "und"


def _failed(mode: str, injection: bool) -> ExtractOutcome:
    return ExtractOutcome(failed=True, injection=injection, mode=mode, extraction=None)


def _from_model_text(message: str, raw: str, mode: str) -> ExtractOutcome:
    detected = find_instruction(message)
    try:
        extraction = Extraction.model_validate_json(raw)
    except Exception as exc:
        logger.warning(
            "extraction_failed mode=%s error_type=%s",
            mode,
            type(exc).__name__,
        )
        return _failed("failed", detected is not None)
    if not extraction_is_grounded(message, extraction):
        logger.warning("extraction_rejected mode=%s reason=ungrounded", mode)
        return _failed("failed", detected is not None or extraction.instruction_override_attempt)
    injection = detected is not None or extraction.instruction_override_attempt
    return ExtractOutcome(False, injection, mode, extraction)


def _best_phrase(text: str, phrases: tuple[str, ...]) -> str | None:
    found: str | None = None
    found_len = -1
    for phrase in phrases:
        hit = find_phrase(text, phrase)
        if hit is not None and len(phrase) > found_len:
            found = hit
            found_len = len(phrase)
    return found


def _company_sentence(message: str) -> tuple[str | None, str | None, int | None, str | None]:
    """Industry, country, employees, and the one sentence that supports them."""
    sentences = re.split(r"(?<=[\.\!\?])\s+", message.strip()) or [message]
    best: tuple[int, str, str | None, str | None, int | None] | None = None
    for sentence in sentences:
        industry: str | None = None
        for pain_industry, surfaces in INDUSTRY_SURFACES.items():
            if _best_phrase(sentence, surfaces):
                industry = pain_industry.value
                break
        country = country_in_text(sentence)
        employees_match = _EMPLOYEES.search(sentence)
        employees = int(employees_match.group(1)) if employees_match else None
        score = sum(item is not None for item in (industry, country, employees))
        if score == 0:
            continue
        if best is None or score > best[0]:
            best = (score, sentence, industry, country, employees)
    if best is None:
        return None, None, None, None
    _, sentence, industry, country, employees = best
    if employees is not None and str(employees) not in sentence:
        employees = None
    return industry, country, employees, sentence


def rules_extract(message: str) -> ExtractOutcome:
    """Fill a field only when the message contains a frozen phrase for that field."""
    detected = find_instruction(message)
    if detected:
        extraction = Extraction(
            language=_language(message),
            intent=Intent.OTHER,
            quotes=[detected],
            instruction_override_attempt=True,
        )
        return ExtractOutcome(False, True, "rules", extraction)

    intent: Intent | None = None
    intent_quote: str | None = None
    for candidate in INTENT_PRIORITY:
        hit = _best_phrase(message, INTENT_SURFACES[candidate])
        if hit is not None:
            intent = candidate
            intent_quote = hit
            break
    if intent is None or intent_quote is None:
        logger.info("rules_unreadable reason=no_intent_phrase")
        return _failed("rules", False)

    quotes = [intent_quote]
    problem: Pain | None = None
    problem_quote: str | None = None
    best_len = -1
    for pain, surfaces in PAIN_SURFACES.items():
        hit = _best_phrase(message, surfaces)
        if hit is not None and len(hit) > best_len:
            problem = pain
            problem_quote = hit
            best_len = len(hit)
    if problem_quote and problem_quote not in quotes:
        quotes.append(problem_quote)

    role_level = None
    role_quote = None
    for level, surfaces in ROLE_SURFACES.items():
        hit = _best_phrase(message, surfaces)
        if hit is not None:
            role_level = level
            role_quote = hit
            break
    if role_quote and role_quote not in quotes:
        quotes.append(role_quote)

    industry, country, employees, company_quote = _company_sentence(message)
    if company_quote and company_quote not in quotes:
        quotes.append(company_quote)
    if company_quote is None:
        industry, country, employees = None, None, None

    extraction = Extraction(
        language=_language(message),
        intent=intent,
        stated_role=role_level,
        stated_role_quote=role_quote,
        stated_problem=problem,
        stated_problem_quote=problem_quote,
        stated_industry=industry,
        stated_employees=employees,
        stated_country=country,
        stated_company_quote=company_quote,
        quotes=quotes,
        instruction_override_attempt=False,
    )
    if not extraction_is_grounded(message, extraction):
        logger.info("rules_unreadable reason=ungrounded")
        return _failed("rules", False)
    return ExtractOutcome(False, False, "rules", extraction)


def extract_message(
    message: str,
    inbound_id: str,
    client: CompletionClient | None,
) -> ExtractOutcome:
    """Known seed ids use fixtures. A live client is never replaced by the rules path."""
    detected = find_instruction(message)
    fixtures = load_fixtures()
    if inbound_id in fixtures:
        try:
            extraction = Extraction.model_validate(fixtures[inbound_id])
        except Exception as exc:
            logger.warning(
                "fixture_invalid inbound_id=%s error_type=%s",
                inbound_id,
                type(exc).__name__,
            )
            return _failed("failed", detected is not None)
        if not extraction_is_grounded(message, extraction):
            logger.warning("fixture_rejected inbound_id=%s reason=ungrounded", inbound_id)
            return _failed("failed", detected is not None)
        injection = detected is not None or extraction.instruction_override_attempt
        return ExtractOutcome(False, injection, "fixture", extraction)

    if client is None:
        return rules_extract(message)

    try:
        raw = client.complete_json(
            role="extract",
            user_payload={"inbound_id": inbound_id, "message": message},
        )
    except Exception as exc:
        logger.warning(
            "extraction_failed inbound_id=%s mode=failed error_type=%s",
            inbound_id,
            type(exc).__name__,
        )
        return _failed("failed", detected is not None)
    outcome = _from_model_text(message, raw, "gemini")
    if detected is not None and not outcome.injection:
        return ExtractOutcome(outcome.failed, True, outcome.mode, outcome.extraction)
    return outcome
