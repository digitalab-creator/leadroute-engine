"""Surface forms of the closed intent, pain, industry, and country enums.

A phrase counts only when it appears as its own words inside a quote.
Unknown wording does not get a nearest guess.
"""

import re

from app.constants import COUNTRY_TO_REGION, Industry, Intent, Pain, RoleFunction, RoleLevel

# Longer phrases are listed first inside each tuple so a specific hit wins.
INTENT_SURFACES: dict[Intent, tuple[str, ...]] = {
    Intent.UNSUBSCRIBE: ("remove me from your mailing list", "unsubscribe"),
    Intent.AUTO_REPLY: ("out of the office", "automatic reply", "auto-reply", "autoreply"),
    Intent.JOB_SEEKER: ("internship", "intern", "student"),
    Intent.INVESTOR: ("funding round", "series a", "series b"),
    Intent.PARTNERSHIP: ("white-label", "partnership"),
    Intent.NOT_INTERESTED: ("geen interesse", "not interested", "no interest"),
    Intent.DEMO: ("show us how this works", "demo"),
    Intent.PRICING: ("send pricing", "pricing", "cost us"),
    Intent.PILOT: ("pilot",),
    Intent.POSITIVE_REPLY: (
        "looking forward to our call",
        "open to a 30-minute call",
        "30-minute call",
        "happy to chat",
        "can we talk",
        "yes please",
        "אשמח לשיחה",
    ),
    Intent.OTHER: (),
}

INTENT_PRIORITY = (
    Intent.UNSUBSCRIBE,
    Intent.AUTO_REPLY,
    Intent.JOB_SEEKER,
    Intent.INVESTOR,
    Intent.PARTNERSHIP,
    Intent.NOT_INTERESTED,
    Intent.DEMO,
    Intent.PRICING,
    Intent.PILOT,
    Intent.POSITIVE_REPLY,
)

PAIN_SURFACES: dict[Pain, tuple[str, ...]] = {
    Pain.RATE_QUOTING: (
        "spot rate",
        "rate requests",
        "rate request",
        "rate quoting",
        "rate quote",
        "rate cards",
        "rate card",
        "carrier quotes",
        "rfqs",
        "rfq",
        "בקשות להצעות מחיר",
    ),
    Pain.DOCUMENT_EXTRACTION: (
        "bills of lading",
        "bill of lading",
        "air waybills",
        "air waybill",
        "import declarations",
        "import declaration",
        "packing lists",
        "packing list",
        "booking confirmations",
        "booking confirmation",
        "document extraction",
        "customs paperwork",
    ),
    Pain.INVOICE_RECONCILIATION: (
        "reconciling carrier invoices",
        "invoice reconciliation",
        "invoice and contract",
    ),
    Pain.TRADE_DOCUMENT_CHECKING: ("trade document", "customs paperwork"),
}

INDUSTRY_SURFACES: dict[Industry, tuple[str, ...]] = {
    Industry.FREIGHT_FORWARDER: ("freight forwarder", "freight forwarding", "forwarder"),
    Industry.CARRIER: ("ocean carrier", "carrier"),
    Industry.THIRD_PARTY_LOGISTICS: ("3pl", "third-party logistics"),
    Industry.TRUCKING: ("trucking", "haulage"),
    Industry.AIR_CARGO: ("air cargo",),
    Industry.GROUND_HANDLING: ("ground handling",),
    Industry.CUSTOMS_BROKER: ("customs brokerage", "customs broker"),
    Industry.SHIPPER: ("shipper",),
    Industry.TRADE_FINANCE: ("trade finance",),
}

ROLE_SURFACES: dict[RoleLevel, tuple[str, ...]] = {
    RoleLevel.OWNER_FOUNDER: ("i own", "founder", "owner"),
    RoleLevel.STUDENT: ("student", "intern"),
}

# Place names that are surface forms of a country code. Unknown places stay unknown.
PLACE_TO_COUNTRY = {
    "haifa": "IL",
    "ashdod": "IL",
    "tel aviv": "IL",
    "israel": "IL",
    "rotterdam": "NL",
    "amsterdam": "NL",
    "netherlands": "NL",
    "antwerp": "BE",
    "belgium": "BE",
    "singapore": "SG",
    "london": "GB",
    "united kingdom": "GB",
    "berlin": "DE",
    "germany": "DE",
    "new york": "US",
    "united states": "US",
}


def _pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)


def find_phrase(text: str, phrase: str) -> str | None:
    """Return the original slice when the phrase stands on its own, else None."""
    if not text or not phrase:
        return None
    match = _pattern(phrase).search(text)
    if match is None:
        return None
    return match.group(0)


def find_any(text: str, phrases: tuple[str, ...]) -> str | None:
    """Prefer the longest phrase that is actually in the text."""
    found: str | None = None
    for phrase in sorted(phrases, key=len, reverse=True):
        hit = find_phrase(text, phrase)
        if hit is not None:
            return hit
        if found is None:
            found = None
    return found


def phrase_in(text: str, phrase: str) -> bool:
    return find_phrase(text, phrase) is not None


def country_in_text(text: str) -> str | None:
    """Return an ISO-ish code from the frozen place list, or None."""
    folded_hits: list[tuple[int, str]] = []
    for place, code in PLACE_TO_COUNTRY.items():
        hit = find_phrase(text, place)
        if hit is not None:
            folded_hits.append((len(place), code))
    if not folded_hits:
        return None
    folded_hits.sort(key=lambda item: item[0], reverse=True)
    return folded_hits[0][1]


def region_for_country(country: str | None) -> str | None:
    if country is None:
        return None
    key = country.strip().casefold()
    if not key:
        return None
    if key in COUNTRY_TO_REGION:
        return COUNTRY_TO_REGION[key]
    # "IL" is already in the map. A stated industry country may be the code.
    return COUNTRY_TO_REGION.get(key.lower())


def function_for_role(level: RoleLevel | None) -> RoleFunction | None:
    if level is RoleLevel.OWNER_FOUNDER:
        return RoleFunction.GENERAL_MANAGEMENT
    return None
