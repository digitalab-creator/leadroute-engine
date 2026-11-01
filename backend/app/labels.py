"""English words for the closed codes the screens show.

The queue and the lead read these labels. They do not show `positive_reply`
or `rate_quoting`. Add a code here when the enum grows. Do not grow a second map
in the React app.
"""

import re

from app.constants import (
    CHANNELS,
    ICP_REGIONS,
    Industry,
    Intent,
    Pain,
    RoleFunction,
    RoleLevel,
    Status,
)

_HEBREW = re.compile(r"[\u0590-\u05FF]")
_LATIN = re.compile(r"[A-Za-z]")

STATUS_LABELS: dict[str, str] = {
    Status.QL.value: "Qualified lead",
    Status.QL_CANDIDATE.value: "Qualified-lead candidate",
    Status.EXCLUDED.value: "Excluded",
    Status.DISQUALIFIED.value: "Disqualified",
    Status.NURTURE.value: "Nurture",
    Status.SUPPRESSED.value: "Suppressed",
    Status.NEEDS_REVIEW.value: "Needs review",
}

INTENT_LABELS: dict[str, str] = {
    Intent.DEMO.value: "Asked for a demo",
    Intent.PRICING.value: "Asked about pricing",
    Intent.PILOT.value: "Asked for a pilot",
    Intent.POSITIVE_REPLY.value: "Wants to talk",
    Intent.NOT_INTERESTED.value: "Not interested",
    Intent.UNSUBSCRIBE.value: "Unsubscribe",
    Intent.AUTO_REPLY.value: "Automatic reply",
    Intent.PARTNERSHIP.value: "Partnership",
    Intent.INVESTOR.value: "Investor",
    Intent.JOB_SEEKER.value: "Job seeker",
    Intent.OTHER.value: "Other",
}

PAIN_LABELS: dict[str, str] = {
    Pain.RATE_QUOTING.value: "Rate quoting",
    Pain.DOCUMENT_EXTRACTION.value: "Document extraction",
    Pain.INVOICE_RECONCILIATION.value: "Invoice reconciliation",
    Pain.TRADE_DOCUMENT_CHECKING.value: "Trade document checking",
}

INDUSTRY_LABELS: dict[str, str] = {
    Industry.FREIGHT_FORWARDER.value: "Freight forwarder",
    Industry.CARRIER.value: "Carrier",
    Industry.THIRD_PARTY_LOGISTICS.value: "Third-party logistics",
    Industry.TRUCKING.value: "Trucking",
    Industry.AIR_CARGO.value: "Air cargo",
    Industry.GROUND_HANDLING.value: "Ground handling",
    Industry.CUSTOMS_BROKER.value: "Customs broker",
    Industry.SHIPPER.value: "Shipper",
    Industry.TRADE_FINANCE.value: "Trade finance",
}

ROLE_LABELS: dict[str, str] = {
    RoleLevel.OWNER_FOUNDER.value: "Owner or founder",
    RoleLevel.C_LEVEL.value: "C-level",
    RoleLevel.VP.value: "VP",
    RoleLevel.DIRECTOR.value: "Director",
    RoleLevel.HEAD.value: "Head",
    RoleLevel.MANAGER.value: "Manager",
    RoleLevel.TEAM_LEAD.value: "Team lead",
    RoleLevel.IC.value: "Individual contributor",
    RoleLevel.STUDENT.value: "Student",
}

FUNCTION_LABELS: dict[str, str] = {
    RoleFunction.PRICING.value: "Pricing",
    RoleFunction.OPERATIONS.value: "Operations",
    RoleFunction.PROCUREMENT.value: "Procurement",
    RoleFunction.COMMERCIAL.value: "Commercial",
    RoleFunction.FINANCE.value: "Finance",
    RoleFunction.DIGITAL.value: "Digital",
    RoleFunction.GENERAL_MANAGEMENT.value: "General management",
    RoleFunction.OTHER.value: "Other",
}

REGION_LABELS: dict[str, str] = {
    "benelux": "Benelux",
    "nordics": "Nordics",
    "uk": "United Kingdom",
    "dach": "DACH",
    "singapore": "Singapore",
    "united_states": "United States",
    "israel": "Israel",
    "apac": "Asia-Pacific",
}

CHANNEL_LABELS: dict[str, str] = {
    "form_fill": "Form",
    "email_reply": "Email",
    "linkedin_dm": "LinkedIn",
}

LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "he": "Hebrew",
    "nl": "Dutch",
    "und": "Not detected",
}

DRAFT_STATE_LABELS: dict[str, str] = {
    "template": "Local template, no model",
    "writer": "Written by Gemini",
    "edited": "Edited by you",
    "unavailable": "Not available",
    "not_applicable": "Not written for this status",
}

ANALYSIS_LABELS: dict[str, str] = {
    "fixture": "Reviewed example",
    "gemini": "Gemini",
    "rules": "Rules, no model",
    "failed": "Failed",
    "none": "None",
    "template": "Local template, no model",
    "writer": "Written by Gemini",
}

DECISION_LABELS: dict[str, str] = {
    "accepted": "Accepted",
    "rejected": "Rejected",
}


def _from_map(table: dict[str, str], code: str) -> str:
    return table.get(code, code)


def label_status(code: str) -> str:
    return _from_map(STATUS_LABELS, code)


def label_intent(code: str) -> str:
    return _from_map(INTENT_LABELS, code)


def label_pain(code: str) -> str:
    return _from_map(PAIN_LABELS, code)


def label_industry(code: str) -> str:
    return _from_map(INDUSTRY_LABELS, code)


def label_role(code: str) -> str:
    return _from_map(ROLE_LABELS, code)


def label_function(code: str) -> str:
    return _from_map(FUNCTION_LABELS, code)


def label_region(code: str) -> str:
    return _from_map(REGION_LABELS, code)


def label_channel(code: str) -> str:
    return _from_map(CHANNEL_LABELS, code)


def label_language(code: str) -> str:
    return _from_map(LANGUAGE_LABELS, code)


def label_draft_state(code: str) -> str:
    return _from_map(DRAFT_STATE_LABELS, code)


def label_analysis(code: str) -> str:
    return _from_map(ANALYSIS_LABELS, code)


def label_decision(code: str) -> str:
    return _from_map(DECISION_LABELS, code)


def letter_counts(text: str) -> tuple[int, int]:
    """Hebrew letters, then Latin letters. Digits and punctuation do not count."""
    return len(_HEBREW.findall(text)), len(_LATIN.findall(text))


def text_direction(language: str, text: str) -> str:
    """Right-to-left when the message language is Hebrew, or the letters are."""
    if language == "he":
        return "rtl"
    hebrew, latin = letter_counts(text)
    if hebrew >= 8 and hebrew > latin:
        return "rtl"
    return "ltr"


def evidence_label(text: str) -> str:
    """Turn the gate's stored evidence into words a person can read."""
    if text.startswith("industry "):
        return _industry_evidence(text)
    if text.startswith("role ") and " / " in text:
        body = text.removeprefix("role ")
        level, function = body.split(" / ", 1)
        return f"Role {label_role(level)} / {label_function(function)}"
    if text.startswith("pain "):
        return f"Problem {label_pain(text.removeprefix('pain '))}"
    if text.startswith("intent "):
        return f"Intent {label_intent(text.removeprefix('intent '))}"
    return text


def _industry_evidence(text: str) -> str:
    chunks: list[str] = []
    for part in text.split(", "):
        key, sep, value = part.partition(" ")
        if key == "industry" and sep:
            chunks.append(f"Industry {label_industry(value)}")
        elif key == "employees" and sep:
            chunks.append(f"Employees {value}")
        elif key == "region" and sep:
            chunks.append(f"Region {label_region(value)}")
        else:
            chunks.append(part)
    return ", ".join(chunks)


def draft_matches_language(draft: str, language: str) -> bool:
    """True when the reply is actually in the inbound language, not a mix.

    Hebrew is a script check. Dutch rejects the English template opener, because
    Dutch and English use the same letters and the script check cannot see that.
    """
    hebrew, latin = letter_counts(draft)
    if language == "he":
        return hebrew >= 8 and hebrew > latin
    if language == "nl":
        return latin >= 8 and hebrew == 0 and not draft.startswith("Thanks for writing")
    if language == "en":
        return latin >= 8 and latin > hebrew
    return hebrew + latin >= 8


# Fail the import if a closed code has no English label. A new enum value
# should not reach the screen as a raw key.
def _require_labels() -> None:
    missing: list[str] = []
    for status in Status:
        if status.value not in STATUS_LABELS:
            missing.append(f"status {status.value}")
    for intent in Intent:
        if intent.value not in INTENT_LABELS:
            missing.append(f"intent {intent.value}")
    for pain in Pain:
        if pain.value not in PAIN_LABELS:
            missing.append(f"pain {pain.value}")
    for industry in Industry:
        if industry.value not in INDUSTRY_LABELS:
            missing.append(f"industry {industry.value}")
    for role in RoleLevel:
        if role.value not in ROLE_LABELS:
            missing.append(f"role {role.value}")
    for function in RoleFunction:
        if function.value not in FUNCTION_LABELS:
            missing.append(f"function {function.value}")
    for region in ICP_REGIONS:
        if region not in REGION_LABELS:
            missing.append(f"region {region}")
    for channel in CHANNELS:
        if channel not in CHANNEL_LABELS:
            missing.append(f"channel {channel}")
    if missing:
        raise RuntimeError("missing display labels: " + ", ".join(missing))


_require_labels()
