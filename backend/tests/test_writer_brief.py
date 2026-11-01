"""Guardrails for the sales reply writer payload."""

from app.constants import Intent, Pain
from app.pipeline.writer_brief import WriterInput, build_writer_payload


def test_rate_quoting_maps_to_bc3a() -> None:
    payload = build_writer_payload(
        WriterInput(
            inbound_id="x",
            language="en",
            message_body="400 RFQs a week",
            problem_quote="400 RFQs a week",
            intent=Intent.DEMO.value,
            stated_problem=Pain.RATE_QUOTING.value,
        )
    )
    assert "BC-3a" in payload["product_focus"]
    assert "demo" in payload["intent_next_step"].casefold() or "walkthrough" in payload["intent_next_step"].casefold()
