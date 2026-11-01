# LeadRoute

LeadRoute is a RevOps engine that turns inbound GTM messages into routed leads, auditable qualification decisions, and a weekly KPI pack. A language model may propose structured evidence from each message; **Python owns identity, the five QL conditions, status, owner, score, and counting.**

## What it does

- **Ingest** — Load CRM export and GTM events from `data/`, or paste a new inbound via the API.
- **Qualify** — Apply a fixed gate (ICP, buyer, problem, interest, sales acceptance) plus exclusions and hygiene rules.
- **Route** — Assign an owner from region or CRM; never auto-send mail (drafts are human-reviewed).
- **Report** — Build the week pack from stored rows (QLs, meetings, opportunities, expansion) using `data/ql_standard.md`.

## Quick start

Requires Python 3.11+ (tested on 3.13).

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
copy .env.example .env
# Optional: set GEMINI_API_KEY for live extraction on pasted messages (seed uses fixtures offline)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Health check: `GET http://127.0.0.1:8000/health`  
Paste inbound: `POST http://127.0.0.1:8000/api/inbound` (JSON body: channel, text, from_email or linkedin_url, optional source and received_at).

Optional env (see `.env.example`):

| Variable | Default |
|----------|---------|
| `GEMINI_API_KEY` | empty (fixtures + rules fallback) |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `LEADROUTE_DB_PATH` | `var/revops.sqlite` |
| `LEADROUTE_DATA_DIR` | `data/` |
| `LEADROUTE_LOG_DIR` | `logs/` |

## Tests

Offline suite (no network):

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_identity.py backend/tests/test_ql_gate.py backend/tests/test_kpi.py backend/tests/test_llm_failure.py -q
```

## Layout

```
backend/app/ingest/     Identity, validation, CRM + events load
backend/app/pipeline/   Extraction, gate, score, writer
backend/app/kpi/        Weekly pack (pure function over SQLite)
data/                   Demo CRM + GTM pack and QL standard
```

## Design notes

- One pipeline for seed and paste; one `decide()` for status; one `build_pack()` for KPIs.
- Failed or injected analysis → `needs review`, never QL or disqualified.
- Score bands (A/B/nurture) do not override the gate.
- Logs redact emails and LinkedIn URLs; message bodies are not written to disk.
