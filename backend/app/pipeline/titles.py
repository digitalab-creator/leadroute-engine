"""Turn a job title into a role level and a function. Unknown titles stay unknown."""

from app.constants import RoleFunction, RoleLevel

# Checked before the prefix and suffix rules, because those rules would
# mis-read "managing director" as an unknown function plus "director".
_EXACT: dict[str, tuple[RoleLevel, RoleFunction | None]] = {
    "managing director": (RoleLevel.DIRECTOR, RoleFunction.GENERAL_MANAGEMENT),
    "customer service team lead": (RoleLevel.TEAM_LEAD, RoleFunction.OTHER),
    "chief executive officer": (RoleLevel.C_LEVEL, RoleFunction.GENERAL_MANAGEMENT),
    "chief financial officer": (RoleLevel.C_LEVEL, RoleFunction.FINANCE),
    "chief operating officer": (RoleLevel.C_LEVEL, RoleFunction.OPERATIONS),
    "general manager": (RoleLevel.MANAGER, RoleFunction.GENERAL_MANAGEMENT),
}

_TOKENS: dict[str, tuple[RoleLevel, RoleFunction | None]] = {
    "ceo": (RoleLevel.C_LEVEL, RoleFunction.GENERAL_MANAGEMENT),
    "cfo": (RoleLevel.C_LEVEL, RoleFunction.FINANCE),
    "coo": (RoleLevel.C_LEVEL, RoleFunction.OPERATIONS),
    "cto": (RoleLevel.C_LEVEL, RoleFunction.DIGITAL),
    "founder": (RoleLevel.OWNER_FOUNDER, RoleFunction.GENERAL_MANAGEMENT),
    "owner": (RoleLevel.OWNER_FOUNDER, RoleFunction.GENERAL_MANAGEMENT),
    "student": (RoleLevel.STUDENT, None),
    "intern": (RoleLevel.STUDENT, None),
}

_PREFIXES: tuple[tuple[str, RoleLevel], ...] = (
    ("vice president of ", RoleLevel.VP),
    ("vice president ", RoleLevel.VP),
    ("head of ", RoleLevel.HEAD),
    ("director of ", RoleLevel.DIRECTOR),
    ("vp ", RoleLevel.VP),
)

_SUFFIXES: tuple[tuple[str, RoleLevel], ...] = (
    (" team lead", RoleLevel.TEAM_LEAD),
    (" manager", RoleLevel.MANAGER),
    (" director", RoleLevel.DIRECTOR),
    (" analyst", RoleLevel.IC),
)

# First hit wins, so a more specific buyer function is listed before a broad one.
_FUNCTIONS: tuple[tuple[str, RoleFunction], ...] = (
    ("customer service", RoleFunction.OTHER),
    ("procurement", RoleFunction.PROCUREMENT),
    ("pricing", RoleFunction.PRICING),
    ("finance", RoleFunction.FINANCE),
    ("financial", RoleFunction.FINANCE),
    ("commercial", RoleFunction.COMMERCIAL),
    ("marketing", RoleFunction.OTHER),
    ("partnerships", RoleFunction.OTHER),
    ("partnership", RoleFunction.OTHER),
    ("operations", RoleFunction.OPERATIONS),
    ("transportation", RoleFunction.OPERATIONS),
    ("logistics", RoleFunction.OPERATIONS),
    ("customs", RoleFunction.OPERATIONS),
    ("station", RoleFunction.OPERATIONS),
    ("digital", RoleFunction.DIGITAL),
    ("it", RoleFunction.DIGITAL),
)


def normalize_title(title: str) -> str:
    cleaned = title.casefold().replace("&", " and ")
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in cleaned)
    return " ".join(cleaned.split())


def _function_in(text: str) -> RoleFunction | None:
    tokens = set(text.split())
    for phrase, function in _FUNCTIONS:
        if " " in phrase:
            if phrase in text:
                return function
        elif phrase in tokens:
            return function
    return None


def resolve_title(title: str | None) -> tuple[RoleLevel | None, RoleFunction | None]:
    if title is None or not title.strip():
        return None, None
    key = normalize_title(title)
    if key in _EXACT:
        return _EXACT[key]
    if key in _TOKENS:
        return _TOKENS[key]
    for prefix, level in _PREFIXES:
        if key.startswith(prefix):
            return level, _function_in(key[len(prefix) :])
    for suffix, level in _SUFFIXES:
        if key.endswith(suffix):
            return level, _function_in(key[: -len(suffix)])
    return None, None
