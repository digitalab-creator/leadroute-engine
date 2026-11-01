"""The week pack as the markdown file a reviewer reads.

Unknown stays the word unknown. The closing note is for the CRO and stays
under 150 words because the brief asks for that limit.
"""

from app.kpi.pack import CountLine, KpiPack

CRO_WORD_LIMIT = 150


def _cell(line: CountLine) -> str:
    if line.actual is None:
        return "unknown"
    return str(line.actual)


def _shortfall(line: CountLine) -> str:
    if line.shortfall is None:
        return ""
    return str(line.shortfall)


def _ids(line: CountLine) -> str:
    if not line.ids:
        return ""
    return ", ".join(line.ids)


def _metric_row(label: str, line: CountLine) -> str:
    target = "" if line.target is None else str(line.target)
    return f"| {label} | {_cell(line)} | {target} | {_shortfall(line)} | {_ids(line)} |"


def _pace(pack: KpiPack) -> str:
    lines = (pack.qls, pack.meetings_booked, pack.meetings_held, pack.opportunities)
    comparable = [
        line
        for line in lines
        if line.actual is not None and line.target is not None
    ]
    if comparable and all(
        line.actual is not None and line.target is not None and line.actual < line.target
        for line in comparable
    ):
        return "Every acquisition line is short of its target."
    if comparable and all(
        line.actual is not None and line.target is not None and line.actual >= line.target
        for line in comparable
    ):
        return "Every acquisition line meets or beats its target."
    return "Some acquisition lines are short of target and some are not."


def _count(line: CountLine) -> str:
    if line.actual is None:
        return "unknown"
    return str(line.actual)


def cro_note(
    pack: KpiPack,
    *,
    prompt: str,
    engines_missing: int,
    engine_count: int,
) -> str:
    """Plain-language week, the top visibility leak, and one next action."""
    reactivation = pack.by_source.get("historical-reactivation")
    if reactivation is not None and reactivation.actual is None:
        unknown_line = (
            "The historical-reactivation feed was not received, "
            "so that source is unknown, not zero."
        )
    else:
        unknown_line = "Every tracked source feed was received, so none of those rows are unknown."
    note = (
        f"This week produced {_count(pack.qls)} qualified leads against a target of "
        f"{pack.qls.target}, {_count(pack.meetings_booked)} meetings booked against "
        f"{pack.meetings_booked.target}, {_count(pack.meetings_held)} meetings held against "
        f"{pack.meetings_held.target}, and {_count(pack.opportunities)} opportunities against "
        f"{pack.opportunities.target}. {_pace(pack)} {unknown_line} "
        f'The largest AI-visibility leak is the buyer question "{prompt}": '
        f"Stargo is missing from {engines_missing} of {engine_count} engines while a competitor "
        "is named. Those buyers never enter the pipeline. Next week I would publish one short "
        "page that answers that question in the buyer's words, cite only approved Stargo facts, "
        "and point the engines at stargo.co."
    )
    words = note.split()
    if len(words) > CRO_WORD_LIMIT:
        raise ValueError(f"CRO note is {len(words)} words")
    return note


def render_pack(pack: KpiPack, note: str) -> str:
    source_rows = "\n".join(
        f"| {source} | {_cell(line)} | {_ids(line)} |"
        for source, line in pack.by_source.items()
    )
    body = f"""# Weekly KPI pack

Reporting window: {pack.week_start} through {pack.week_end} (Asia/Jerusalem).

Recomputed from stored decisions. A missing feed is unknown, not zero.

## Acquisition

| Metric | Actual | Target | Shortfall | Records |
| --- | --- | --- | --- | --- |
{_metric_row("Qualified leads", pack.qls)}
{_metric_row("Meetings booked", pack.meetings_booked)}
{_metric_row("Meetings held", pack.meetings_held)}
{_metric_row("Opportunities", pack.opportunities)}

## Qualified leads by first-touch source

| Source | Actual | Records |
| --- | --- | --- |
{source_rows}

## Expansion

Existing customers and pre-existing deals. Not part of the acquisition targets.

| Metric | Actual | Records |
| --- | --- | --- |
| Meetings booked | {_cell(pack.expansion_meetings_booked)} | {_ids(pack.expansion_meetings_booked)} |
| Meetings held | {_cell(pack.expansion_meetings_held)} | {_ids(pack.expansion_meetings_held)} |
| Opportunities | {_cell(pack.expansion_opportunities)} | {_ids(pack.expansion_opportunities)} |

People: {", ".join(pack.expansion_people) if pack.expansion_people else "none"}

## Note to the CRO

{note}
"""
    return body
