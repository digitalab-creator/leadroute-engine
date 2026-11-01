"""Gap score, look-alikes, wrong claims, and the brief checker. No network."""

import json

from pydantic import ValidationError

from app.visibility.brief import (
    BriefDraft,
    BriefFaq,
    BriefSection,
    CheckedBrief,
    citation_ids,
    compose_brief,
    open_visibility,
    prose_words,
)
from app.visibility.gap import AnswersFile, rank_gaps
from tests.conftest import DATA_DIR


def _document(answers: list[dict[str, object]]) -> AnswersFile:
    return AnswersFile.model_validate(
        {
            "meta": {
                "note": "unit",
                "own_domains": ["stargo.co"],
                "brand": "Stargo",
                "known_competitors": ["Laneframe", "QuoteHarbor"],
            },
            "answers": answers,
        }
    )


def _answer(answer_id: str, text: str, citations: list[str] | None = None) -> dict[str, object]:
    return {
        "answer_id": answer_id,
        "prompt_id": "Q1",
        "prompt": "which tool drafts a freight quote from email",
        "cluster": "rate-quoting",
        "priority": 3,
        "engine": "ChatGPT",
        "captured_at": "2026-10-06T07:00:00Z",
        "answer_text": text,
        "citations": citations or [],
    }


def test_real_pack_ranks_the_laneframe_question_first() -> None:
    gaps, brief = open_visibility(DATA_DIR, None)
    top = gaps[0]
    assert top.prompt_id == "P6"
    assert top.score == 18
    assert top.miss_count == 3
    assert top.competitor_without_owned_count == 3
    by_id = {gap.prompt_id: gap for gap in gaps}
    assert by_id["P1"].score == 12
    perplexity = next(engine for engine in by_id["P2"].engines if engine.engine == "Perplexity")
    assert perplexity.mentioned is True
    assert perplexity.cited_owned is False
    assert "stargo-shipping.com" in perplexity.lookalikes
    brand = next(engine for engine in by_id["P5"].engines if engine.engine == "ChatGPT")
    assert brand.mentioned is False
    assert "StarGo" in brand.lookalikes
    gemini = next(engine for engine in by_id["P5"].engines if engine.engine == "Gemini")
    assert gemini.wrong_claim is True
    owned = next(engine for engine in by_id["P7"].engines if engine.engine == "Gemini")
    assert owned.mentioned is True
    assert owned.cited_owned is True
    assert brief.mode == "fixture"
    assert brief.blocked is False
    assert 40 <= brief.direct_answer_words <= 60


def test_a_wrong_number_and_a_lookalike_do_not_count_as_stargo() -> None:
    wrong = rank_gaps(
        _document([_answer("A", "Stargo cut quote time by 90 percent in a pilot.")])
    )[0]
    assert wrong.engines[0].mentioned is True
    assert wrong.engines[0].wrong_claim is True

    lookalike = rank_gaps(
        _document([_answer("B", "StarGo is a holiday booking app with mixed reviews.")])
    )[0]
    assert lookalike.engines[0].mentioned is False
    assert lookalike.engines[0].wrong_claim is False
    assert lookalike.miss_count == 1

    carrier = rank_gaps(
        _document([_answer("C", "Stargo is an ocean carrier headquartered in Rotterdam.")])
    )[0]
    assert carrier.engines[0].wrong_claim is True

    cited = rank_gaps(
        _document(
            [
                _answer(
                    "D",
                    "Laneframe and Stargo both draft quotes.",
                    ["https://www.stargo.co/rate-quoting"],
                )
            ]
        )
    )[0]
    assert cited.engines[0].cited_owned is True
    assert cited.competitor_without_owned_count == 0


def test_checker_drops_untagged_facts_and_unknown_ids() -> None:
    known = citation_ids((DATA_DIR / "brand_context.md").read_text(encoding="utf-8"))
    assert "BC-1" in known
    assert "PP-1" in known
    assert "BC-99" not in known

    draft = BriefDraft(
        title="alternatives to Laneframe for freight pricing",
        direct_answer=(
            "Stargo builds agentic AI that turns messy enterprise documents, emails and "
            "datasets into trusted operational transactions across freight, logistics and "
            "trade finance [BC-1]. "
            "This sentence has no tag and must not survive. "
            "Stargo promises 500 percent growth [BC-99]."
        ),
        sections=[
            BriefSection(heading="One", body="Humans stay in control: agents draft, people approve [BC-1]."),
            BriefSection(heading="Two", body="Untagged section fact that should vanish."),
            BriefSection(
                heading="Three",
                body=(
                    "A European forwarder pilot cut median spot-quote turnaround from about "
                    "3 hours to under 15 minutes [PP-1]."
                ),
            ),
        ],
        faq=[
            BriefFaq(question="Who approves?", answer="Humans stay in control: agents draft, people approve [BC-1]."),
            BriefFaq(question="Missing?", answer="No tag here either."),
            BriefFaq(
                question="Proof?",
                answer=(
                    "A European forwarder pilot cut median spot-quote turnaround from about "
                    "3 hours to under 15 minutes [PP-1]."
                ),
            ),
        ],
        schema_org_type="Article",
    )
    checked = compose_brief_from_draft(draft, known)
    assert "no tag" not in checked.direct_answer.casefold()
    assert "BC-99" not in checked.direct_answer
    assert "500" not in checked.direct_answer
    assert checked.blocked is True
    assert checked.removed_sentences >= 2
    assert prose_words(checked.direct_answer) < 40


class _FakeClient:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.roles: list[str] = []

    def complete_json(self, *, role: str, user_payload: dict[str, str]) -> str:
        self.roles.append(role)
        assert "brand_context" in user_payload
        return self.raw


def compose_brief_from_draft(draft: BriefDraft, known: frozenset[str]) -> CheckedBrief:
    from app.visibility.gap import Gap

    top = Gap(
        prompt_id="P6",
        prompt="alternatives to Laneframe for freight pricing",
        cluster="competitive",
        priority=3,
        score=1,
        miss_count=1,
        competitor_without_owned_count=1,
        wrong_claim_count=0,
        engines=(),
    )
    client = _FakeClient(draft.model_dump_json())
    checked = compose_brief(top, "brand", known, client)
    assert client.roles == ["brief"]
    return checked


def test_a_failed_model_call_is_unavailable_not_a_fixture() -> None:
    known = citation_ids((DATA_DIR / "brand_context.md").read_text(encoding="utf-8"))
    from app.visibility.gap import Gap

    top = Gap(
        prompt_id="P6",
        prompt="alternatives to Laneframe for freight pricing",
        cluster="competitive",
        priority=3,
        score=1,
        miss_count=3,
        competitor_without_owned_count=3,
        wrong_claim_count=0,
        engines=(),
    )

    class Boom:
        def complete_json(self, *, role: str, user_payload: dict[str, str]) -> str:
            raise TimeoutError("slow")

    checked = compose_brief(top, "brand", known, Boom())
    assert checked.mode == "unavailable"
    assert checked.blocked is True
    assert checked.direct_answer == ""
    assert "fixture" not in checked.label.casefold() or "no fixture" in checked.label.casefold()


def test_garbage_json_does_not_become_a_finished_brief() -> None:
    known = citation_ids((DATA_DIR / "brand_context.md").read_text(encoding="utf-8"))
    from app.visibility.gap import Gap

    top = Gap(
        prompt_id="P6",
        prompt="alternatives to Laneframe for freight pricing",
        cluster="competitive",
        priority=3,
        score=1,
        miss_count=3,
        competitor_without_owned_count=3,
        wrong_claim_count=0,
        engines=(),
    )
    checked = compose_brief(top, "brand", known, _FakeClient("not-json"))
    assert checked.blocked is True
    assert checked.mode == "unavailable"
    with_status = json.dumps({"title": "x", "status": "QL"})
    try:
        BriefDraft.model_validate_json(with_status)
    except ValidationError:
        pass
    else:
        raise AssertionError("a status field must not be part of the brief")
