CREATE TABLE IF NOT EXISTS persons (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    email TEXT,
    linkedin_slug TEXT,
    company_name TEXT,
    company_domain TEXT,
    industry TEXT,
    employees INTEGER,
    country TEXT,
    account_kind TEXT NOT NULL DEFAULT 'unknown',
    title TEXT,
    is_customer INTEGER,
    crm_owner TEXT,
    open_deal_id TEXT,
    open_deal_created TEXT,
    deal_unreadable INTEGER NOT NULL DEFAULT 0,
    lead_status TEXT,
    crm_record_id TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_persons_email
    ON persons(email) WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_persons_linkedin
    ON persons(linkedin_slug) WHERE linkedin_slug IS NOT NULL;

CREATE TABLE IF NOT EXISTS inbounds (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id),
    channel TEXT NOT NULL,
    source TEXT,
    received_at TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    from_name TEXT
);

CREATE TABLE IF NOT EXISTS extractions (
    inbound_id TEXT PRIMARY KEY REFERENCES inbounds(id),
    mode TEXT NOT NULL,
    failed INTEGER NOT NULL,
    injection INTEGER NOT NULL,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS sales_decisions (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(id),
    decision TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    person_id TEXT PRIMARY KEY REFERENCES persons(id),
    status TEXT NOT NULL,
    owner TEXT,
    score INTEGER NOT NULL,
    band TEXT NOT NULL,
    breakdown_json TEXT NOT NULL,
    conditions_json TEXT NOT NULL,
    rationale TEXT NOT NULL,
    draft TEXT,
    draft_state TEXT NOT NULL,
    analysis_mode TEXT NOT NULL,
    expansion INTEGER NOT NULL,
    qualified INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_events (
    id TEXT PRIMARY KEY,
    person_id TEXT REFERENCES persons(id),
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feed_status (
    source TEXT PRIMARY KEY,
    status TEXT NOT NULL
);
