# Data pack (v2)

All people, companies, domains, engine answers and figures are **synthetic demo data**. Any resemblance to real organizations is coincidental.

| File | What it is |
|---|---|
| `crm_export.csv` | HubSpot-style contact export, 19 rows. Messy values (casing, domain variants, duplicate company names, stale statuses) on purpose. |
| `gtm_events.json` | `inbound` (21 replies, forms and LinkedIn DMs), `sales_decisions` (11), `pipeline_events` (12 meetings and opportunities), `feed_status` per source, and `meta`. Timestamps carry their own offsets (some `Z`, some `+03:00`). |
| `ai_answers.json` | 24 synthetic answer-engine captures: 8 buyer prompts × 3 engines, with priority, cluster and cited URLs. `meta.own_domains` lists the demo brand’s domain. |
| `ql_standard.md` | QL definition, exclusions, statuses, hygiene, routing and KPI counting rules — the spec LeadRoute implements. |
| `brand_context.md` | Approved marketing claims for the demo brand; use for visibility and content features. |

Some records are edge cases (duplicate identity signals, injection attempts, ambiguous CRM fields). The engine should follow **rules in `ql_standard.md`**, not hard-coded row IDs.
