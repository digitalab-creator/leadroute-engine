"""Rank buyer questions by how often answer engines miss Stargo.

The brand token is case-sensitive on purpose: StarGo is a different word.
Competitor names come only from the file's known_competitors list.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict

# Enough to surface a false Stargo claim. Not enough to outrank a priority-3
# buyer question where Stargo is absent and a competitor is named.
WRONG_CLAIM_WEIGHT = 5

# Digits that appear in PP-1, PP-2, and PP-3. Any other digit on a Stargo
# sentence is a claim the brand file does not allow.
APPROVED_CLAIM_NUMBERS = frozenset({2, 3, 15, 97})

# Exact tokens. Case-folded "stargo" would hide StarGo inside the real brand.
LOOKALIKE_TOKENS = ("StarGo",)

# Closed phrases from brand_context.md BC-5. "carrier" alone is too wide:
# a sentence that says Stargo serves carriers is not a wrong claim.
FORBIDDEN_IDENTITY_PHRASES = (
    "ocean carrier",
    "is a carrier",
    "is a broker",
    "is a forwarder",
    "travel company",
    "holiday booking",
)

FORMULA = (
    "priority × engines that miss the Stargo token"
    " + priority × engines that name a competitor and do not cite stargo.co"
    " + 5 × engines with a wrong claim"
)

_BRAND_TOKEN = re.compile(r"\bStargo\b")
_NUMBER = re.compile(r"\d+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class AnswerMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str
    own_domains: list[str]
    brand: str
    known_competitors: list[str]


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: str
    prompt_id: str
    prompt: str
    cluster: str
    priority: int
    engine: str
    captured_at: str
    answer_text: str
    citations: list[str]


class AnswersFile(BaseModel):
    """The shape of data/ai_answers.json. Extra keys are a bad file, not a gap."""

    model_config = ConfigDict(extra="forbid")

    meta: AnswerMeta
    answers: list[Answer]


@dataclass(frozen=True)
class EngineView:
    engine: str
    answer_id: str
    mentioned: bool
    cited_owned: bool
    competitors: tuple[str, ...]
    lookalikes: tuple[str, ...]
    wrong_claim: bool


@dataclass(frozen=True)
class Gap:
    prompt_id: str
    prompt: str
    cluster: str
    priority: int
    score: int
    miss_count: int
    competitor_without_owned_count: int
    wrong_claim_count: int
    engines: tuple[EngineView, ...]


def citation_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def is_owned_host(host: str, owned_domains: tuple[str, ...]) -> bool:
    for domain in owned_domains:
        if host == domain or host.endswith("." + domain):
            return True
    return False


def _phrase_in(text: str, phrase: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)"
    return re.search(pattern, text.casefold()) is not None


def _lookalike_tokens(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for token in LOOKALIKE_TOKENS:
        if re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", text):
            found.append(token)
    return tuple(found)


def _wrong_claim(text: str) -> bool:
    """True when a sentence that names Stargo states a forbidden identity or number."""
    for sentence in _SENTENCE_SPLIT.split(text.strip()):
        if _BRAND_TOKEN.search(sentence) is None:
            continue
        folded = sentence.casefold()
        if any(phrase in folded for phrase in FORBIDDEN_IDENTITY_PHRASES):
            return True
        for raw in _NUMBER.findall(sentence):
            if int(raw) not in APPROVED_CLAIM_NUMBERS:
                return True
    return False


def _engine_view(
    answer: Answer,
    competitors: tuple[str, ...],
    owned_domains: tuple[str, ...],
) -> EngineView:
    hosts = tuple(citation_host(url) for url in answer.citations if citation_host(url))
    named = tuple(name for name in competitors if _phrase_in(answer.answer_text, name))
    in_hosts = tuple(
        name
        for name in competitors
        if any(name.casefold().split()[0] in host for host in hosts)
    )
    present = tuple(dict.fromkeys((*named, *in_hosts)))
    lookalike_hosts = tuple(
        host for host in hosts if "stargo" in host and not is_owned_host(host, owned_domains)
    )
    cited_owned = any(is_owned_host(host, owned_domains) for host in hosts)
    return EngineView(
        engine=answer.engine,
        answer_id=answer.answer_id,
        mentioned=_BRAND_TOKEN.search(answer.answer_text) is not None,
        cited_owned=cited_owned,
        competitors=present,
        lookalikes=_lookalike_tokens(answer.answer_text) + lookalike_hosts,
        wrong_claim=_wrong_claim(answer.answer_text),
    )


def rank_gaps(document: AnswersFile) -> list[Gap]:
    """Highest score first. A tie breaks on priority, then prompt id."""
    owned = tuple(domain.lower() for domain in document.meta.own_domains)
    competitors = tuple(document.meta.known_competitors)
    grouped: dict[str, list[Answer]] = {}
    for answer in document.answers:
        bucket = grouped.setdefault(answer.prompt_id, [])
        if bucket and (bucket[0].prompt != answer.prompt or bucket[0].priority != answer.priority):
            raise ValueError(f"prompt {answer.prompt_id} is not one question")
        bucket.append(answer)

    gaps: list[Gap] = []
    for prompt_id, answers in grouped.items():
        engines = tuple(_engine_view(answer, competitors, owned) for answer in answers)
        miss_count = sum(1 for engine in engines if not engine.mentioned)
        competitor_without_owned_count = sum(
            1
            for engine in engines
            if engine.competitors and not engine.cited_owned
        )
        wrong_claim_count = sum(1 for engine in engines if engine.wrong_claim)
        priority = answers[0].priority
        score = (
            priority * miss_count
            + priority * competitor_without_owned_count
            + WRONG_CLAIM_WEIGHT * wrong_claim_count
        )
        gaps.append(
            Gap(
                prompt_id=prompt_id,
                prompt=answers[0].prompt,
                cluster=answers[0].cluster,
                priority=priority,
                score=score,
                miss_count=miss_count,
                competitor_without_owned_count=competitor_without_owned_count,
                wrong_claim_count=wrong_claim_count,
                engines=engines,
            )
        )
    gaps.sort(key=lambda gap: (-gap.score, -gap.priority, gap.prompt_id))
    if not gaps:
        raise ValueError("ai answers file has no prompts")
    return gaps


def visibility_overview(gaps: list[Gap]) -> dict[str, object]:
    engines: set[str] = set()
    for gap in gaps:
        for engine in gap.engines:
            engines.add(engine.engine)
    top = gaps[0]
    mentioned = sum(1 for gap in gaps for engine in gap.engines if engine.mentioned)
    cited_owned = sum(1 for gap in gaps for engine in gap.engines if engine.cited_owned)
    engine_rows = sum(len(gap.engines) for gap in gaps)
    return {
        "prompt_count": len(gaps),
        "engine_count": len(engines),
        "answer_rows": engine_rows,
        "top_gap_score": top.score,
        "top_prompt_id": top.prompt_id,
        "top_prompt": top.prompt,
        "stargo_miss_total": sum(gap.miss_count for gap in gaps),
        "competitor_gap_total": sum(gap.competitor_without_owned_count for gap in gaps),
        "wrong_claim_total": sum(gap.wrong_claim_count for gap in gaps),
        "mention_rate_pct": round(100 * mentioned / engine_rows) if engine_rows else 0,
        "owned_cite_rate_pct": round(100 * cited_owned / engine_rows) if engine_rows else 0,
    }
