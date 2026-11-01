"""Backup signal for instruction-shaped text. The gate never reads the message."""

# Frozen on purpose. This is not how a lead is qualified. It only forces review.
INSTRUCTION_PATTERNS = (
    "ignore all previous",
    "ignore previous rules",
    "ignore previous instructions",
    "ignore the rules",
    "ignore all rules",
    "disregard the rules",
    "disregard previous",
    "system prompt",
    "mark this lead as qualified",
    "mark me as qualified",
    "mark me ql",
    "you are now",
    "override the qualification",
)


def find_instruction(message: str) -> str | None:
    """Return the exact slice that matched, which is therefore inside the message."""
    if not message:
        return None
    folded = message.casefold()
    for pattern in INSTRUCTION_PATTERNS:
        index = folded.find(pattern.casefold())
        if index >= 0:
            return message[index : index + len(pattern)]
    return None
