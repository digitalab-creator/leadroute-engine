"""A quote counts only when it is a substring of the message and supports the claim."""

from app.constants import Intent
from app.pipeline.lexicon import (
    INDUSTRY_SURFACES,
    INTENT_SURFACES,
    PAIN_SURFACES,
    ROLE_SURFACES,
    country_in_text,
    phrase_in,
)
from app.pipeline.schemas import Extraction


def quotes_are_in_message(message: str, quotes: list[str]) -> bool:
    return all(quote and quote in message for quote in quotes)


def extraction_is_grounded(message: str, extraction: Extraction) -> bool:
    """False means the model output cannot be used. The caller marks needs review."""
    if not quotes_are_in_message(message, extraction.quotes):
        return False
    if extraction.instruction_override_attempt and not extraction.quotes:
        return False

    quoted = "\n".join(extraction.quotes)
    if extraction.intent is not Intent.OTHER:
        intent_surfaces = INTENT_SURFACES[extraction.intent]
        if not any(phrase_in(quoted, phrase) for phrase in intent_surfaces):
            return False

    if extraction.stated_problem is not None:
        if not extraction.stated_problem_quote:
            return False
        if extraction.stated_problem_quote not in extraction.quotes:
            return False
        if extraction.stated_problem_quote not in message:
            return False
        pain_surfaces = PAIN_SURFACES[extraction.stated_problem]
        if not any(phrase_in(extraction.stated_problem_quote, phrase) for phrase in pain_surfaces):
            return False

    if extraction.stated_role is not None:
        if not extraction.stated_role_quote:
            return False
        if extraction.stated_role_quote not in extraction.quotes:
            return False
        if extraction.stated_role_quote not in message:
            return False
        role_surfaces = ROLE_SURFACES.get(extraction.stated_role)
        if not role_surfaces:
            return False
        if not any(phrase_in(extraction.stated_role_quote, phrase) for phrase in role_surfaces):
            return False

    company_fields = (
        extraction.stated_industry is not None
        or extraction.stated_employees is not None
        or extraction.stated_country is not None
    )
    if company_fields:
        quote = extraction.stated_company_quote
        if not quote or quote not in extraction.quotes or quote not in message:
            return False
        if extraction.stated_industry is not None:
            industry_surfaces = INDUSTRY_SURFACES[extraction.stated_industry]
            if not any(phrase_in(quote, phrase) for phrase in industry_surfaces):
                return False
        if extraction.stated_employees is not None and str(extraction.stated_employees) not in quote:
            return False
        if extraction.stated_country is not None:
            found = country_in_text(quote)
            if found is None or found.casefold() != extraction.stated_country.strip().casefold():
                return False
    return True
