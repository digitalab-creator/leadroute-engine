"""Priority score. It explains the lead. It never changes the status."""

from dataclasses import dataclass

from app.constants import (
    BAND_A_FROM,
    BUYER_POINTS,
    ICP_POINTS,
    INTENT_POINTS,
    NURTURE_SCORE_BELOW,
    PROBLEM_POINTS,
    SOURCE_WARMTH,
)
from app.pipeline.evaluate import Conditions


@dataclass(frozen=True)
class Score:
    icp: int
    buyer: int
    problem: int
    intent: int
    source_warmth: int
    total: int
    band: str

    def as_dict(self) -> dict[str, int | str]:
        return {
            "icp": self.icp,
            "buyer": self.buyer,
            "problem": self.problem,
            "intent": self.intent,
            "source_warmth": self.source_warmth,
            "total": self.total,
            "band": self.band,
        }


def band_for(total: int) -> str:
    if total >= BAND_A_FROM:
        return "A"
    if total >= NURTURE_SCORE_BELOW:
        return "B"
    return "nurture"


def score_lead(conditions: Conditions, source: str | None) -> Score:
    icp = ICP_POINTS if conditions.icp.passed else 0
    buyer = BUYER_POINTS if conditions.buyer.passed else 0
    problem = PROBLEM_POINTS if conditions.problem.passed else 0
    intent = INTENT_POINTS if conditions.interest.passed else 0
    warmth = SOURCE_WARMTH.get(source or "", 0)
    total = icp + buyer + problem + intent + warmth
    return Score(
        icp=icp,
        buyer=buyer,
        problem=problem,
        intent=intent,
        source_warmth=warmth,
        total=total,
        band=band_for(total),
    )
