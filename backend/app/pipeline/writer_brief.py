"""What the reply writer needs: brand rules, goals, and pain-to-product mapping.

One place for sales copy constraints. The visibility brief reads brand_context.md;
the writer uses this compact contract so every draft gets the same guardrails.
"""

import re
from dataclasses import dataclass

from app.constants import Intent, Pain

_MESSAGE_MAX = 2400

# Closed map: stated data problem → approved product line (from BC-3).
PAIN_PRODUCT_FOCUS: dict[str, str] = {
    Pain.RATE_QUOTING.value: (
        "Rate Quoting Agent (BC-3a): reads emailed rate requests, pulls tariffs "
        "and contracts, drafts a quote for a pricing analyst to approve."
    ),
    Pain.DOCUMENT_EXTRACTION.value: (
        "Document Extraction (BC-3b): structured fields from B/L, AWB, invoices "
        "and customs paperwork into TMS/ERP, with validation."
    ),
    Pain.INVOICE_RECONCILIATION.value: (
        "Invoice and Contract Reconciliation (BC-3c): matches carrier invoices to "
        "contracted rates and flags discrepancies for review."
    ),
    Pain.TRADE_DOCUMENT_CHECKING.value: (
        "Trade Document Checking (BC-3d): validates trade documents before funds move."
    ),
}

# Optional proof the draft may mention once, only when relevant (PP-1 fits rate quoting).
APPROVED_PROOF_SNIPPETS: dict[str, str] = {
    Pain.RATE_QUOTING.value: (
        "Illustrative pilot: median spot-quote turnaround from about 3 hours to under "
        "15 minutes (PP-1). Use at most one such line; skip if it feels forced."
    ),
}

# Closed map: buyer intent → next step tone (not open-text keyword matching).
INTENT_NEXT_STEP: dict[str, str] = {
    Intent.POSITIVE_REPLY.value: (
        "They already want to talk. Offer one concrete time window or ask for two slots."
    ),
    Intent.DEMO.value: "They asked for a demo. Offer a short live walkthrough, not a generic pitch.",
    Intent.PRICING.value: (
        "They asked about pricing. Offer a scoped conversation; do not invent price lists."
    ),
    Intent.PILOT.value: "They asked for a pilot. Acknowledge scope and suggest a short discovery call.",
}

WRITER_VOICE = (
    "Voice (BC-6): plain, specific, operator to operator. Short sentences. "
    "No hype words such as revolutionary, game-changing, cutting-edge, or "
    "transformative. Write like one logistics operator replying to another."
)

WRITER_GOALS = (
    "Goals: (1) Open by reflecting their exact pain in your own words—use "
    "problem_quote or a phrase from message_body, not a generic 'we read about your scope'. "
    "(2) Tie one sentence to product_focus—how Stargo helps that workflow. "
    "(3) Humans stay in control: agents draft, people approve; nothing sends automatically. "
    "(4) One clear next step matching intent_next_step. "
    "(5) Keep the draft under 120 words unless the message was very long. "
    "(6) Use blank lines between paragraphs; use a short bullet list (lines starting with -) "
    "when listing two or three concrete points."
)

WRITER_FORBIDDEN = (
    "Never: claim Stargo is a carrier, broker, forwarder, or travel company; "
    "name customers unless provided in message_body; invent ROI or accuracy figures "
    "except the optional approved_proof line; attack competitors; promise automatic "
    "send; use filler such as 'precious time' or 'no customer waits long' without "
    "grounding in their message."
)

# Surface forms the checker rejects (aligned with WRITER_FORBIDDEN / generic Hebrew pitch).
GENERIC_DRAFT_MARKERS: tuple[str, ...] = (
    "precious time",
    "no customer will wait",
    "no customer waits",
    "we read about the scope",
    "our system can help you streamline",
    "קראנו על היקף",
    "זמן יקר",
    "שאף לקוח לא ימתין",
    "לייעל את תהליך הפקת ההצעות",
    "להציג כיצד נוכל לעזור",
)

_TOKEN_SPLIT = re.compile(r"[^\w\u0590-\u05FF]+", re.UNICODE)


@dataclass(frozen=True)
class WriterInput:
    inbound_id: str
    language: str
    message_body: str
    problem_quote: str | None
    intent: str | None
    stated_problem: str | None
    client_context_json: str = "{}"
    brand_context_markdown: str = ""
    learned_addendum: str = ""


def clip_message(body: str) -> str:
    text = body.strip()
    if len(text) <= _MESSAGE_MAX:
        return text
    return text[: _MESSAGE_MAX - 3] + "..."


def _significant_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for piece in _TOKEN_SPLIT.split(text.strip()):
        word = piece.strip()
        if len(word) >= 3:
            tokens.append(word)
    return tokens


def draft_grounds_buyer_words(
    draft: str,
    *,
    problem_quote: str | None,
    message_body: str,
) -> bool:
    """Draft must echo at least one substantive token from quote or message."""
    source = (problem_quote or "").strip() or message_body.strip()
    tokens = _significant_tokens(source)
    if not tokens:
        return True
    for token in tokens:
        if token in draft:
            return True
        if token.casefold() in draft.casefold():
            return True
    return False


def draft_has_generic_filler(draft: str) -> bool:
    lowered = draft.casefold()
    return any(marker.casefold() in lowered for marker in GENERIC_DRAFT_MARKERS)


def build_writer_payload(fields: WriterInput) -> dict[str, str]:
    """Structured context for Gemini. Values are strings only."""
    pain = fields.stated_problem or ""
    product = PAIN_PRODUCT_FOCUS.get(pain, "")
    proof = APPROVED_PROOF_SNIPPETS.get(pain, "")
    intent = fields.intent or Intent.OTHER.value
    next_step = INTENT_NEXT_STEP.get(intent, INTENT_NEXT_STEP[Intent.POSITIVE_REPLY.value])
    learned = fields.learned_addendum.strip()
    goals = WRITER_GOALS
    if learned:
        goals = f"{WRITER_GOALS} Learned from sales thumbs (this week): {learned}"
    return {
        "inbound_id": fields.inbound_id,
        "language": fields.language,
        "message_body": clip_message(fields.message_body),
        "problem_quote": fields.problem_quote or "",
        "intent": intent,
        "stated_problem": pain,
        "product_focus": product,
        "approved_proof_optional": proof,
        "intent_next_step": next_step,
        "client_context_json": fields.client_context_json,
        "brand_context_markdown": fields.brand_context_markdown,
        "brand_voice": WRITER_VOICE,
        "goals": goals,
        "forbidden": WRITER_FORBIDDEN,
        "output": (
            "Return JSON with rationale (why this draft fits the goals) and draft "
            "(the unsent reply text only). Both in the language code. "
            "Use client_context_json for who they are and brand_context_markdown for "
            "approved Stargo claims only. Do not decide status, score, or owner."
        ),
    }
