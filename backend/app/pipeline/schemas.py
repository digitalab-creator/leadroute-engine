"""Shapes the model is allowed to return. Extra fields are rejected."""

from pydantic import BaseModel, ConfigDict, Field

from app.constants import Industry, Intent, Pain, RoleLevel


class Extraction(BaseModel):
    """Agent A. Evidence only. No status, score, or owner."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(min_length=2, max_length=12)
    intent: Intent
    stated_role: RoleLevel | None = None
    stated_role_quote: str | None = None
    stated_problem: Pain | None = None
    stated_problem_quote: str | None = None
    stated_industry: Industry | None = None
    stated_employees: int | None = Field(default=None, ge=0)
    stated_country: str | None = None
    stated_company_quote: str | None = None
    quotes: list[str] = Field(default_factory=list)
    instruction_override_attempt: bool


class WriterOutput(BaseModel):
    """Words only. A status smuggled in here is invalid."""

    model_config = ConfigDict(extra="forbid")

    rationale: str = Field(min_length=1)
    draft: str | None = None
