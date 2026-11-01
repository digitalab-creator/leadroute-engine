"""The unsent reply stays in the inbound language and follows writer_brief."""

import json

from app.constants import Pain
from app.pipeline.writer import writer_draft
from app.pipeline.writer_brief import WriterInput, build_writer_payload


class _Capture:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.payload: dict[str, str] | None = None

    def complete_json(self, *, role: str, user_payload: dict[str, str]) -> str:
        self.payload = user_payload
        assert role == "writer"
        return self.raw


def _noam_fields() -> WriterInput:
    return WriterInput(
        inbound_id="IN-012",
        language="he",
        message_body=(
            "שלום, ראינו את הפוסט שלכם. אנחנו מקבלים עשרות בקשות להצעות מחיר ביום "
            "בוואטסאפ ובמייל ומתמחרים הכול ידנית. אשמח לשיחה השבוע."
        ),
        problem_quote="עשרות בקשות להצעות מחיר ביום",
        intent="positive_reply",
        stated_problem=Pain.RATE_QUOTING.value,
    )


def test_hebrew_template_does_not_mix_in_english() -> None:
    fields = _noam_fields()
    text, state = writer_draft(None, allowed=True, fields=fields)
    assert state == "template"
    assert text is not None
    assert "Thanks" not in text
    assert "עשרות" in text


def test_writer_payload_includes_message_brand_and_product() -> None:
    from app.brand_docs import read_brand_context
    from tests.conftest import DATA_DIR

    fields = WriterInput(
        inbound_id="IN-012",
        language="he",
        message_body="עשרות בקשות",
        problem_quote="עשרות בקשות להצעות מחיר ביום",
        intent="positive_reply",
        stated_problem=Pain.RATE_QUOTING.value,
        client_context_json='{"person":{"display_name":"Noam"}}',
        brand_context_markdown=read_brand_context(DATA_DIR),
    )
    payload = build_writer_payload(fields)
    assert "עשרות בקשות" in payload["message_body"]
    assert "BC-3a" in payload["product_focus"]
    assert "BC-1" in payload["brand_context_markdown"]
    assert "Noam" in payload["client_context_json"]
    assert "operator" in payload["brand_voice"].casefold()
    assert "problem_quote" in payload["goals"]
    assert payload["intent_next_step"]


def test_writer_is_told_the_language_and_a_mixed_draft_is_dropped() -> None:
    client = _Capture(
        json.dumps(
            {
                "rationale": "Thanks for writing",
                "draft": 'Thanks for writing. We can look at this: "עשרות בקשות להצעות מחיר ביום".',
            }
        )
    )
    text, state = writer_draft(client, allowed=True, fields=_noam_fields())
    assert state == "template"
    assert text is not None
    assert "Thanks" not in text
    assert client.payload is not None
    assert client.payload["language"] == "he"
    assert "עשרות" in client.payload["message_body"]


def test_writer_keeps_a_hebrew_draft() -> None:
    client = _Capture(
        json.dumps(
            {
                "rationale": "משקף את הציטוט ומציע שיחה",
                "draft": (
                    "שלום, תודה על הפנייה. עשרות בקשות להצעות מחיר ביום בוואטסאפ ובמייל "
                    "זה בדיוק מה שסוכן תמחור שלנו עוזר לטיוט—אדם מהצוות מאשר לפני שליחה. "
                    "אשמח לשיחה קצרה השבוע—מתאים יום רביעי או חמישי?"
                ),
            }
        )
    )
    text, state = writer_draft(client, allowed=True, fields=_noam_fields())
    assert state == "writer"
    assert text is not None
    assert "Thanks" not in text


def test_writer_rejects_hype_words() -> None:
    client = _Capture(
        json.dumps(
            {
                "rationale": "bad",
                "draft": "פתרון מהפכני לתמחור.",
            }
        )
    )
    text, state = writer_draft(client, allowed=True, fields=_noam_fields())
    assert state == "template"
    assert text is not None
    assert "עשרות" in text


def test_writer_rejects_generic_hebrew_marketing_pitch() -> None:
    generic = (
        "שלום, קראנו על היקף הבקשות להצעות מחיר שאתם מקבלים מדי יום. "
        "המערכת שלנו יכולה לסייע לכם לייעל את תהליך הפקת ההצעות, לחסוך זמן יקר "
        "ולוודא שאף לקוח לא ימתין זמן רב. נשמח לתאם שיחה קצרה ולהציג כיצד נוכל לעזור."
    )
    client = _Capture(json.dumps({"rationale": "generic", "draft": generic}))
    text, state = writer_draft(client, allowed=True, fields=_noam_fields())
    assert state == "template"
    assert text is not None
    assert "קראנו על היקף" not in text
    assert "עשרות" in text or "הצעות מחיר" in text
