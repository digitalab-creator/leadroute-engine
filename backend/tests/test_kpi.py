"""The week pack. Asia/Jerusalem, once per person, unknown is not zero."""

from datetime import datetime
from pathlib import Path

from app.clock import JERUSALEM, in_reporting_week, parse_timestamp
from app.constants import Status
from app.db import apply_schema, connect
from app.kpi.pack import PackEvent, PackPerson, build_pack
from app.logging_config import configure_logging
from app.service import load_seed, pack_from_connection, record_sales_decision
from tests.conftest import DATA_DIR


def _person(
    person_id: str,
    *,
    status: str = Status.QL,
    accepted_at: datetime | None = None,
    source: str | None = "paid",
    is_customer: bool = False,
    deal_created: datetime | None = None,
    first_inbound_at: datetime | None = None,
    inbound_in_week: bool = True,
) -> PackPerson:
    return PackPerson(
        person_id=person_id,
        status=status,
        accepted_at=accepted_at,
        source=source,
        is_customer=is_customer,
        deal_created=deal_created,
        first_inbound_at=first_inbound_at,
        inbound_in_week=inbound_in_week,
    )


def test_reporting_window_converts_z_and_offsets() -> None:
    assert in_reporting_week(parse_timestamp("2026-10-04T00:00:00+03:00")) is True
    assert in_reporting_week(parse_timestamp("2026-10-03T21:00:00Z")) is True
    assert in_reporting_week(parse_timestamp("2026-10-03T20:59:59Z")) is False
    # Thursday evening in UTC is still Thursday in Jerusalem.
    priya = parse_timestamp("2026-10-08T20:30:00Z")
    assert priya.astimezone(JERUSALEM).day == 8
    assert in_reporting_week(priya) is True
    # One hour later is Friday morning in Jerusalem, so it stays Friday.
    marcus = parse_timestamp("2026-10-08T21:30:00Z")
    assert marcus.astimezone(JERUSALEM).day == 9
    assert in_reporting_week(marcus) is False
    friday_before = parse_timestamp("2026-10-02T16:40:00+03:00")
    assert in_reporting_week(friday_before) is False


def test_a_ql_counts_on_decided_at_once_and_not_on_a_friday_inbound() -> None:
    inside = datetime(2026, 10, 6, 12, tzinfo=JERUSALEM)
    outside = datetime(2026, 10, 11, 9, tzinfo=JERUSALEM)
    pack = build_pack(
        [
            _person("in-week", accepted_at=inside),
            _person("after-week", accepted_at=outside),
            _person("candidate", status=Status.QL_CANDIDATE, accepted_at=None),
        ],
        [],
        {"paid": "received"},
    )
    assert pack.qls.actual == 1
    assert pack.qls.ids == ("in-week",)
    assert pack.qls.target == 25
    assert pack.qls.shortfall == 24


def test_blank_source_and_a_missing_feed_are_not_zero() -> None:
    inside = datetime(2026, 10, 6, 12, tzinfo=JERUSALEM)
    pack = build_pack(
        [
            _person("blank", accepted_at=inside, source=None),
            _person("paid-one", accepted_at=inside, source="paid"),
        ],
        [],
        {"paid": "received", "historical-reactivation": "not_received"},
    )
    assert pack.by_source["source not recorded"].actual == 1
    assert pack.by_source["paid"].actual == 1
    assert pack.by_source["historical-reactivation"].actual is None
    assert pack.by_source["event-email"].actual is None
    assert pack.by_source["event-email"].actual != 0


def test_a_received_feed_with_no_qls_is_zero() -> None:
    pack = build_pack([], [], {"paid": "received"})
    assert pack.by_source["paid"].actual == 0


def test_expansion_events_are_a_separate_line() -> None:
    inside = datetime(2026, 10, 6, 12, tzinfo=JERUSALEM)
    customer = _person("customer", status=Status.EXCLUDED, is_customer=True, accepted_at=inside)
    fresh = _person("fresh", accepted_at=inside)
    pack = build_pack(
        [customer, fresh],
        [
            PackEvent("booked-customer", "customer", "meeting_booked", inside),
            PackEvent("booked-fresh", "fresh", "meeting_booked", inside),
            PackEvent("held-old", "fresh", "meeting_held", inside),
            PackEvent("opp", "fresh", "opportunity_created", inside),
            PackEvent("too-late", "fresh", "meeting_booked", datetime(2026, 10, 9, tzinfo=JERUSALEM)),
        ],
        {"paid": "received"},
    )
    assert pack.meetings_booked.ids == ("booked-fresh",)
    assert pack.expansion_meetings_booked.ids == ("booked-customer",)
    assert pack.meetings_held.actual == 1
    assert pack.opportunities.actual == 1
    assert "too-late" not in pack.meetings_booked.ids
    assert pack.meetings_booked.target == 15
    assert pack.meetings_held.target == 12
    assert pack.opportunities.target == 5


def _email_index(connection) -> dict[str, str]:
    rows = connection.execute("SELECT id, email FROM persons WHERE email IS NOT NULL")
    return {str(row["email"]): str(row["id"]) for row in rows}


def test_seed_week_matches_the_standard(tmp_path: Path) -> None:
    configure_logging(tmp_path / "logs")
    connection = connect(tmp_path / "revops.sqlite")
    apply_schema(connection)
    load_seed(connection, DATA_DIR)
    pack = pack_from_connection(connection)
    people = _email_index(connection)

    ql_emails = {
        "p.claes@balticacargo.eu",
        "anouk.devries@nordhavenfreight.com",
        "rachel.lim@lionport.com.sg",
        "tom.becker@kestrelsc.com",
        "yossi.mizrahi@gmail.com",
        "noam@ashdodbay.co.il",
    }
    assert pack.qls.actual == 6
    assert set(pack.qls.ids) == {people[email] for email in ql_emails}
    assert people["priya.nair@cedargroveretail.com"] not in pack.qls.ids
    assert people["mark.fenwick@tidewateraircargo.com"] not in pack.qls.ids
    assert people["felix.wagner@halden-fwd.de"] not in pack.qls.ids

    priya = connection.execute(
        "SELECT status FROM decisions WHERE person_id = ?",
        (people["priya.nair@cedargroveretail.com"],),
    ).fetchone()
    felix = connection.execute(
        "SELECT status FROM decisions WHERE person_id = ?",
        (people["felix.wagner@halden-fwd.de"],),
    ).fetchone()
    lukas = connection.execute(
        "SELECT status FROM decisions WHERE person_id = ?",
        (people["lukas.weber@kestrelsc.com"],),
    ).fetchone()
    assert priya["status"] == "QL"
    assert felix["status"] != "QL"
    assert lukas["status"] != "QL"

    assert pack.meetings_booked.actual == 4
    assert set(pack.meetings_booked.ids) == {"PE-003", "PE-004", "PE-007", "PE-010"}
    assert pack.meetings_held.actual == 3
    assert set(pack.meetings_held.ids) == {"PE-002", "PE-005", "PE-008"}
    assert pack.opportunities.actual == 2
    assert set(pack.opportunities.ids) == {"PE-009", "PE-011"}
    assert pack.expansion_meetings_booked.ids == ("PE-006",)

    assert pack.by_source["event-email"].actual == 2
    assert pack.by_source["paid"].actual == 1
    assert pack.by_source["new-connection"].actual == 1
    assert pack.by_source["organic/referral"].actual == 1
    assert pack.by_source["warm-network"].actual == 1
    assert pack.by_source["historical-reactivation"].actual is None
    assert pack.by_source["source not recorded"].actual == 0

    # Pieter's earliest inbound is the Friday email, not the later LinkedIn note.
    pieter_id = people["p.claes@balticacargo.eu"]
    assert pieter_id in pack.by_source["event-email"].ids
    assert pieter_id not in pack.by_source["new-connection"].ids
    connection.close()


def test_moving_decided_at_changes_only_the_week_it_lands_in(tmp_path: Path) -> None:
    configure_logging(tmp_path / "logs")
    first = connect(tmp_path / "revops.sqlite")
    apply_schema(first)
    load_seed(first, DATA_DIR)
    people = _email_index(first)
    person_id = people["anouk.devries@nordhavenfreight.com"]
    record_sales_decision(
        first,
        person_id=person_id,
        decision="accepted",
        decided_at="2026-10-12T09:00:00+03:00",
        replace=True,
    )
    moved = pack_from_connection(first)
    assert person_id not in moved.qls.ids
    first.close()

    reopened = connect(tmp_path / "revops.sqlite")
    still = pack_from_connection(reopened)
    assert person_id not in still.qls.ids
    record_sales_decision(
        reopened,
        person_id=person_id,
        decision="accepted",
        decided_at="2026-10-05T09:40:00+03:00",
        replace=True,
    )
    restored = pack_from_connection(reopened)
    assert person_id in restored.qls.ids
    reopened.close()
