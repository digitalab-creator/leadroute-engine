"""The week pack. It counts stored decisions. It does not re-qualify anyone."""

from dataclasses import dataclass
from datetime import datetime

from app.clock import WEEK_END, WEEK_START, in_reporting_week
from app.constants import (
    EVENT_MEETING_BOOKED,
    EVENT_MEETING_HELD,
    EVENT_OPPORTUNITY,
    FEED_RECEIVED,
    KNOWN_FEEDS,
    SOURCE_NOT_RECORDED,
    TARGETS,
    Status,
)
from app.pipeline.gate import is_preexisting_deal


@dataclass(frozen=True)
class PackPerson:
    person_id: str
    status: str
    accepted_at: datetime | None
    source: str | None
    is_customer: bool
    deal_created: datetime | None
    first_inbound_at: datetime | None
    inbound_in_week: bool


@dataclass(frozen=True)
class PackEvent:
    event_id: str
    person_id: str
    event_type: str
    occurred_at: datetime


@dataclass(frozen=True)
class CountLine:
    actual: int | None
    target: int | None
    ids: tuple[str, ...]

    @property
    def shortfall(self) -> int | None:
        if self.actual is None or self.target is None:
            return None
        return self.target - self.actual


@dataclass(frozen=True)
class KpiPack:
    week_start: str
    week_end: str
    qls: CountLine
    meetings_booked: CountLine
    meetings_held: CountLine
    opportunities: CountLine
    by_source: dict[str, CountLine]
    expansion_meetings_booked: CountLine
    expansion_meetings_held: CountLine
    expansion_opportunities: CountLine
    expansion_people: tuple[str, ...]


def _line(actual: int | None, target: int | None, ids: list[str]) -> CountLine:
    return CountLine(actual=actual, target=target, ids=tuple(sorted(ids)))


def _is_expansion(person: PackPerson) -> bool:
    return person.is_customer or is_preexisting_deal(
        person.deal_created, person.first_inbound_at, person.accepted_at
    )


def build_pack(
    people: list[PackPerson],
    events: list[PackEvent],
    feed_status: dict[str, str],
) -> KpiPack:
    by_id = {person.person_id: person for person in people}
    ql_ids = [
        person.person_id
        for person in people
        if person.status == Status.QL
        and person.accepted_at is not None
        and in_reporting_week(person.accepted_at)
    ]
    source_ids: dict[str, list[str]] = {source: [] for source in KNOWN_FEEDS}
    source_ids[SOURCE_NOT_RECORDED] = []
    for person_id in ql_ids:
        person = by_id[person_id]
        label = person.source or SOURCE_NOT_RECORDED
        if label not in source_ids:
            label = SOURCE_NOT_RECORDED
        source_ids[label].append(person_id)

    by_source: dict[str, CountLine] = {}
    for source in KNOWN_FEEDS:
        if feed_status.get(source) != FEED_RECEIVED:
            by_source[source] = _line(None, None, source_ids[source])
        else:
            by_source[source] = _line(len(source_ids[source]), None, source_ids[source])
    by_source[SOURCE_NOT_RECORDED] = _line(
        len(source_ids[SOURCE_NOT_RECORDED]), None, source_ids[SOURCE_NOT_RECORDED]
    )

    buckets: dict[str, dict[str, list[str]]] = {
        "acquisition": {
            EVENT_MEETING_BOOKED: [],
            EVENT_MEETING_HELD: [],
            EVENT_OPPORTUNITY: [],
        },
        "expansion": {
            EVENT_MEETING_BOOKED: [],
            EVENT_MEETING_HELD: [],
            EVENT_OPPORTUNITY: [],
        },
    }
    expansion_people: set[str] = set()
    for person in people:
        if not _is_expansion(person):
            continue
        active = person.inbound_in_week or (
            person.accepted_at is not None and in_reporting_week(person.accepted_at)
        )
        if active:
            expansion_people.add(person.person_id)

    for event in events:
        matched = by_id.get(event.person_id)
        if matched is None or not in_reporting_week(event.occurred_at):
            continue
        if event.event_type not in buckets["acquisition"]:
            continue
        side = "expansion" if _is_expansion(matched) else "acquisition"
        buckets[side][event.event_type].append(event.event_id)
        if side == "expansion":
            expansion_people.add(matched.person_id)

    return KpiPack(
        week_start=WEEK_START.isoformat(),
        week_end=WEEK_END.isoformat(),
        qls=_line(len(ql_ids), TARGETS["qls"], ql_ids),
        meetings_booked=_line(
            len(buckets["acquisition"][EVENT_MEETING_BOOKED]),
            TARGETS["meetings_booked"],
            buckets["acquisition"][EVENT_MEETING_BOOKED],
        ),
        meetings_held=_line(
            len(buckets["acquisition"][EVENT_MEETING_HELD]),
            TARGETS["meetings_held"],
            buckets["acquisition"][EVENT_MEETING_HELD],
        ),
        opportunities=_line(
            len(buckets["acquisition"][EVENT_OPPORTUNITY]),
            TARGETS["opportunities"],
            buckets["acquisition"][EVENT_OPPORTUNITY],
        ),
        by_source=by_source,
        expansion_meetings_booked=_line(
            len(buckets["expansion"][EVENT_MEETING_BOOKED]),
            None,
            buckets["expansion"][EVENT_MEETING_BOOKED],
        ),
        expansion_meetings_held=_line(
            len(buckets["expansion"][EVENT_MEETING_HELD]),
            None,
            buckets["expansion"][EVENT_MEETING_HELD],
        ),
        expansion_opportunities=_line(
            len(buckets["expansion"][EVENT_OPPORTUNITY]),
            None,
            buckets["expansion"][EVENT_OPPORTUNITY],
        ),
        expansion_people=tuple(sorted(expansion_people)),
    )
