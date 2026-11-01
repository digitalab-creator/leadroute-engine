# LeadRoute

LeadRoute turns the synthetic GTM pack into a routed lead queue, a weekly KPI pack, and an AI-visibility gap list.

Python owns identity, the five QL conditions, status, owner, score, and counting. Gemini may propose evidence. It does not decide.

## Install

Python 3.13 and Node 22. From this folder. Leave `GEMINI_API_KEY` empty for the first run.

Windows (PowerShell):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
copy .env.example .env
cd frontend
npm install
cd ..
```

macOS or Linux:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp .env.example .env
cd frontend && npm install && cd ..
```

## Run with no key

The API listens on port **8000**. The dev screen proxies `/api` to that same port.

Windows, terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Windows, terminal 2:

```powershell
cd frontend
npm run dev
```

macOS or Linux, terminal 1:

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

macOS or Linux, terminal 2:

```bash
cd frontend && npm run dev
```

Open http://127.0.0.1:5173 .

Or build the screens and open one process.

Windows:

```powershell
cd frontend
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000
```

macOS or Linux:

```bash
cd frontend && npm run build && cd ..
.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8000
```

Then open http://127.0.0.1:8000 .

Seed messages use reviewed JSON fixtures (`analysis_mode = fixture`). A pasted message the fixture set does not know uses a rules fallback that only fills a condition when it can quote the message. Otherwise the status is `needs review` and the mode is `rules`.

Health: `GET http://127.0.0.1:8000/health`

## Run with a Gemini key

Put the key in `.env` (this file stays gitignored):

```
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.8-flash
```

Restart the API. Pasted messages and the visibility brief call Gemini (`provider=gemini`, role `extract`, `writer`, or `brief`). The request asks for JSON with low thinking and does not send `temperature`, which Gemini 3.8 Flash rejects. The seed file still uses fixtures, so a cold start does not spend the free tier on the demo pack. If the call fails, times out, or returns garbage, qualification becomes `needs review` and a failed brief is marked unavailable. A fixture is not shown as if the model had written it.

## What to click

- **Queue** (`/`) — name, company, channel, Israel time, score, status, owner. Paste a new message at the bottom.
- **Lead** (`/leads/:id`) — the message, the extraction, the score breakdown, the five conditions, the unsent draft. Accept or Reject with an editable time.
- **KPI pack** (`/kpi`) — actual vs target, by source, with the records under each number. A missing feed says unknown.
- **AI visibility** (`/visibility`) — ranked gaps and the brief for the top one.

Export the same week to `KPI_PACK.md`:

Windows:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.export_kpi
```

macOS or Linux:

```bash
PYTHONPATH=backend .venv/bin/python -m app.export_kpi
```

HubSpot dry-run (bonus): exact CRM v3 contact PATCH payloads, no API call:

Windows:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.export_hubspot
```

macOS or Linux:

```bash
PYTHONPATH=backend .venv/bin/python -m app.export_hubspot
```

Writes `var/hubspot_dry_run.json`. Same JSON at `GET /api/integrations/hubspot/dry-run`.

Labelled qualifier eval (second bonus):

Windows:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.run_qualifier_eval
```

macOS or Linux:

```bash
PYTHONPATH=backend .venv/bin/python -m app.run_qualifier_eval
```

Runs `data/qualifier_eval.json` through the gate (no LLM). Report: `var/qualifier_eval_report.json` and `GET /api/eval/qualifier`.

## Code vs model

| Step | Who |
| --- | --- |
| Identity (email or LinkedIn only), domain, free-mail | Code |
| Language, intent, role, pain, quotes | Gemini, or a fixture, or the rules fallback |
| Quote must be a substring of the message | Code |
| Five QL conditions, exclusions, status, owner | Code, one function: `decide` |
| Score 0–100 | Code. It never changes the status |
| One-line rationale and the unsent draft | Gemini or a template. No status fields in that schema |
| Week pack | Code, one function: `build_pack` |
| Gap table | Code over `data/ai_answers.json` |
| Top-gap brief | Gemini when a key is set, then a checker. No key: a reviewed fixture |

A failed or injected analysis is `needs review`. It is never QL and never disqualified. Nothing is emailed or written to a CRM.

## Formulas

**Priority score** (does not override the gate): ICP 25, buyer 20, problem specificity 25, intent 20, source warmth up to 10. Bands: 70+ A, 40–69 B, under 40 nurture. Warmth points live in `SOURCE_WARMTH`. A blank source scores 0 warmth and is reported as `source not recorded`.

**Gap score**, highest first:

`priority × engines that miss the Stargo token + priority × engines that name a competitor and do not cite stargo.co + 5 × engines with a wrong claim`

The weight 5 surfaces a false claim about Stargo without letting it outrank a priority-3 buyer question where Stargo is absent and a competitor is named. That question is the pipeline leak: the buyer never hears of Stargo, so no lead starts.

`Stargo` is matched as its own token. `StarGo` is a look-alike, not a mention. A citation counts as owned only when the host is `stargo.co`. A wrong claim is a Stargo sentence with a number other than 2, 3, 15, or 97 (the digits in PP-1, PP-2, and PP-3), or a closed BC-5 identity Stargo does not have (carrier, broker, forwarder, travel).

The brief checker keeps a factual sentence only when it carries a `BC-*` or `PP-*` id that `data/brand_context.md` actually lists. Unknown ids and untagged sentences are removed. If the direct answer is no longer 40–60 words, the brief is marked blocked.

## Assumptions

- One person matches on normalized email or LinkedIn URL only. Name and company do not merge people.
- The UI Accept replaces the current acceptance time, so you can move a decision into or out of the week. Reject records a rejection and does not delete an earlier acceptance.
- The checker enforces citation tags. It does not prove the sentence means the same thing as the brand paragraph. A human still reads the brief.
- Week is Sun 4 Oct 2026 00:00 through Thu 8 Oct 2026 23:59:59.999, Asia/Jerusalem, after every timestamp is converted.
- Logs are `logs/app.log` (one readable line) and `logs/error.log` (JSON). The formatter redacts email addresses, LinkedIn URLs, and `prompt=` / `body=` values. Call sites do not log message text.

## What I cut

Nothing required for the core brief. Both optional bonuses are implemented (HubSpot dry-run + labelled qualifier eval).

## Bonus: HubSpot dry-run

After qualification, each lead maps to a `PATCH /crm/v3/objects/contacts/{id}` with `lead_status`, `hubspot_owner_id`, and custom `stargo_*` properties from the engine. Rep names map to synthetic owner ids in the JSON `owner_id_map`. Nothing is sent to HubSpot.

## Bonus: Qualifier eval set

`data/qualifier_eval.json` holds **15 labelled rows** tied to `ql_standard.md` sections. Each row supplies CRM profile + merged signal + acceptance and expects status, `qualified`, and owner. `run_qualifier_eval` runs `build_gate_input` → `decide` only (no model). CI and local checks expect **100% pass** on the bundled set.

## Tests

No network in unit tests. The backend model client is replaced in pytest. The UI uses Vitest with mocked `fetch`, plus Playwright smoke tests that boot the API with an empty key and hit the built screens.

**Backend**

Windows:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tests
.\.venv\Scripts\python.exe -m mypy -p app
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

macOS or Linux:

```bash
.venv/bin/python -m ruff check backend/app backend/tests
.venv/bin/python -m mypy -p app
.venv/bin/python -m pytest backend/tests -q
```

**Frontend unit and smoke (offline)**

From `frontend/`:

```powershell
npm run test
```

Covers API response parsing (bad shapes throw `ApiError`), `BriefProse` cite tags, and the app shell nav.

**Frontend e2e (Playwright)**

Build the UI first, then run smoke tests. Playwright starts uvicorn on port **8765** (override with `E2E_PORT`) with a temp SQLite file and no Gemini key, so it does not clash with a dev server on 8000.

Windows (repo root on `PATH` for `python`):

```powershell
cd frontend
npm run build
npm run test:e2e
```

macOS or Linux:

```bash
cd frontend && npm run build && npm run test:e2e
```

**Lint and production build**

```powershell
cd frontend
npm run lint
npm run build
```

**CI** (`.github/workflows/ci.yml`): backend job (ruff, mypy, pytest), frontend job (Vitest, lint, build), e2e job (build + Playwright smoke on Ubuntu).

## Layout

```
backend/app/ingest/       identity, validation, CRM and events
backend/app/pipeline/     extraction, gate, score, writer, Gemini client
backend/app/eval/             labelled QL gate eval set
backend/app/integrations/  HubSpot CRM v3 dry-run payloads
backend/app/kpi/          week pack and the markdown export
backend/app/visibility/   gap score and the brief checker
backend/app/api/          HTTP routes
frontend/src/             four screens, one CSS file
```

Styling is one mobile-first CSS file and no component library. Four screens do not need one. The layout stacks from 390px upward.
