"""Closed sets shared by the gate, the score, and the week pack.

One list per idea. Callers do not grow their own copies.
"""

import os
from enum import StrEnum

# README, the Vite proxy, and logo links in drafts all use this port.
LOCAL_API_PORT = 8000
DEFAULT_SITE_ORIGIN = f"http://127.0.0.1:{LOCAL_API_PORT}"

# Reporting week from ql_standard.md section 6. Sun 4 Oct through Thu 8 Oct 2026.
WEEK_START_DATE = (2026, 10, 4)
WEEK_END_DATE = (2026, 10, 8)
REPORTING_TIMEZONE = "Asia/Jerusalem"

NURTURE_SCORE_BELOW = 40
BAND_A_FROM = 70

ICP_POINTS = 25
BUYER_POINTS = 20
PROBLEM_POINTS = 25
INTENT_POINTS = 20
WARMTH_POINTS_MAX = 10

TARGETS = {
    "qls": 25,
    "meetings_booked": 15,
    "meetings_held": 12,
    "opportunities": 5,
}

# A blank source is a bucket, not a feed that can be "not received".
SOURCE_NOT_RECORDED = "source not recorded"


def configured_site_origin() -> str:
    """Logo links in an unsent draft. Blank env falls back to the local API."""
    raw = os.environ.get("LEADROUTE_SITE_ORIGIN", DEFAULT_SITE_ORIGIN).strip()
    return raw or DEFAULT_SITE_ORIGIN


KNOWN_FEEDS = (
    "event-email",
    "paid",
    "historical-reactivation",
    "new-connection",
    "warm-network",
    "organic/referral",
)

# Points out of WARMTH_POINTS_MAX. A source that is missing scores 0.
SOURCE_WARMTH = {
    "warm-network": 10,
    "event-email": 8,
    "organic/referral": 6,
    "historical-reactivation": 6,
    "new-connection": 4,
    "paid": 2,
}

CHANNELS = ("form_fill", "email_reply", "linkedin_dm")

FREE_MAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "outlook.com",
        "hotmail.com",
        "yahoo.com",
        "icloud.com",
        "proton.me",
        "protonmail.com",
    }
)

ICP_REGIONS = frozenset(
    {"benelux", "nordics", "uk", "dach", "singapore", "united_states", "israel"}
)

REGION_OWNERS = {
    "benelux": "Dana",
    "nordics": "Dana",
    "uk": "Leo",
    "dach": "Leo",
    "singapore": "Mei",
    "united_states": "Sam",
    "israel": "Noa",
}

APAC_OWNER = "Mei"
TRIAGE_OWNER = "Triage queue"
FOUNDERS_OWNER = "Founders"

# Countries we can name. Unknown text stays unknown.
# APAC entries that are not Singapore fail ICP and still route to Mei.
COUNTRY_TO_REGION = {
    "nl": "benelux",
    "netherlands": "benelux",
    "be": "benelux",
    "belgium": "benelux",
    "lu": "benelux",
    "luxembourg": "benelux",
    "se": "nordics",
    "sweden": "nordics",
    "no": "nordics",
    "norway": "nordics",
    "dk": "nordics",
    "denmark": "nordics",
    "fi": "nordics",
    "finland": "nordics",
    "is": "nordics",
    "iceland": "nordics",
    "uk": "uk",
    "gb": "uk",
    "united kingdom": "uk",
    "de": "dach",
    "germany": "dach",
    "at": "dach",
    "austria": "dach",
    "ch": "dach",
    "switzerland": "dach",
    "sg": "singapore",
    "singapore": "singapore",
    "us": "united_states",
    "usa": "united_states",
    "united states": "united_states",
    "il": "israel",
    "israel": "israel",
    "au": "apac",
    "australia": "apac",
    "nz": "apac",
    "new zealand": "apac",
    "jp": "apac",
    "japan": "apac",
    "kr": "apac",
    "south korea": "apac",
    "cn": "apac",
    "china": "apac",
    "hk": "apac",
    "hong kong": "apac",
    "my": "apac",
    "malaysia": "apac",
    "th": "apac",
    "thailand": "apac",
    "id": "apac",
    "indonesia": "apac",
    "ph": "apac",
    "philippines": "apac",
    "vn": "apac",
    "vietnam": "apac",
    "in": "apac",
    "india": "apac",
    "tw": "apac",
    "taiwan": "apac",
}

MIN_EMPLOYEES = 20
OWNER_EMPLOYEES_UNDER = 200

FEED_RECEIVED = "received"
FEED_NOT_RECEIVED = "not_received"


class Status(StrEnum):
    QL_CANDIDATE = "QL candidate"
    QL = "QL"
    EXCLUDED = "excluded"
    DISQUALIFIED = "disqualified"
    NURTURE = "nurture"
    SUPPRESSED = "suppressed"
    NEEDS_REVIEW = "needs review"


class Intent(StrEnum):
    DEMO = "demo"
    PRICING = "pricing"
    PILOT = "pilot"
    POSITIVE_REPLY = "positive_reply"
    NOT_INTERESTED = "not interested"
    UNSUBSCRIBE = "unsubscribe"
    AUTO_REPLY = "auto-reply"
    PARTNERSHIP = "partnership"
    INVESTOR = "investor"
    JOB_SEEKER = "job seeker"
    OTHER = "other"


class Pain(StrEnum):
    RATE_QUOTING = "rate_quoting"
    DOCUMENT_EXTRACTION = "document_extraction"
    INVOICE_RECONCILIATION = "invoice_reconciliation"
    TRADE_DOCUMENT_CHECKING = "trade_document_checking"


class Industry(StrEnum):
    FREIGHT_FORWARDER = "freight_forwarder"
    CARRIER = "carrier"
    THIRD_PARTY_LOGISTICS = "3pl"
    TRUCKING = "trucking"
    AIR_CARGO = "air_cargo"
    GROUND_HANDLING = "ground_handling"
    CUSTOMS_BROKER = "customs_broker"
    SHIPPER = "shipper"
    TRADE_FINANCE = "trade_finance"


class AccountKind(StrEnum):
    ICP = "icp"
    SOFTWARE_VENDOR = "software_vendor"
    INVESTOR = "investor"
    UNKNOWN = "unknown"


class RoleLevel(StrEnum):
    OWNER_FOUNDER = "owner_founder"
    C_LEVEL = "c_level"
    VP = "vp"
    DIRECTOR = "director"
    HEAD = "head"
    MANAGER = "manager"
    TEAM_LEAD = "team_lead"
    IC = "individual_contributor"
    STUDENT = "student"


class RoleFunction(StrEnum):
    PRICING = "pricing"
    OPERATIONS = "operations"
    PROCUREMENT = "procurement"
    COMMERCIAL = "commercial"
    FINANCE = "finance"
    DIGITAL = "digital"
    GENERAL_MANAGEMENT = "general_management"
    OTHER = "other"


INTEREST_INTENTS = frozenset(
    {Intent.DEMO, Intent.PRICING, Intent.PILOT, Intent.POSITIVE_REPLY}
)

MANAGER_OR_ABOVE = frozenset(
    {
        RoleLevel.C_LEVEL,
        RoleLevel.VP,
        RoleLevel.DIRECTOR,
        RoleLevel.HEAD,
        RoleLevel.MANAGER,
    }
)

INFLUENCE_FUNCTIONS = frozenset(
    {
        RoleFunction.PRICING,
        RoleFunction.OPERATIONS,
        RoleFunction.PROCUREMENT,
        RoleFunction.COMMERCIAL,
        RoleFunction.FINANCE,
        RoleFunction.DIGITAL,
        RoleFunction.GENERAL_MANAGEMENT,
    }
)

# CRM verticals, after spaces and hyphens are removed.
VERTICAL_MAP: dict[str, tuple[str | None, str]] = {
    "freightforwarder": (Industry.FREIGHT_FORWARDER, AccountKind.ICP),
    "carrier": (Industry.CARRIER, AccountKind.ICP),
    "3pl": (Industry.THIRD_PARTY_LOGISTICS, AccountKind.ICP),
    "trucking": (Industry.TRUCKING, AccountKind.ICP),
    "aircargo": (Industry.AIR_CARGO, AccountKind.ICP),
    "groundhandling": (Industry.GROUND_HANDLING, AccountKind.ICP),
    "customsbroker": (Industry.CUSTOMS_BROKER, AccountKind.ICP),
    "shipper": (Industry.SHIPPER, AccountKind.ICP),
    "tradefinance": (Industry.TRADE_FINANCE, AccountKind.ICP),
    "softwarevendor": (None, AccountKind.SOFTWARE_VENDOR),
    "investor": (None, AccountKind.INVESTOR),
}

NO_DRAFT_STATUSES = frozenset(
    {
        Status.SUPPRESSED,
        Status.DISQUALIFIED,
        Status.EXCLUDED,
        Status.NEEDS_REVIEW,
    }
)

EVENT_MEETING_BOOKED = "meeting_booked"
EVENT_MEETING_HELD = "meeting_held"
EVENT_OPPORTUNITY = "opportunity_created"
PIPELINE_EVENT_TYPES = frozenset(
    {EVENT_MEETING_BOOKED, EVENT_MEETING_HELD, EVENT_OPPORTUNITY}
)
