# How I used the agent

First-person log for the Stargo RevOps take-home. This is how I actually worked on **1 Nov 2026**.

I used Cursor once more for **this file**: the agent proposed a section skeleton (hours, decisions, agent vs me, prompts, checks) from my chat history and my notes. I **filled in the numbers, prompts, and corrections myself** and edited every section so it matches what I did—not a paste-and-submit draft.

## Hours

**Total: ~2.25 hours to build, plus a same-day hardening pass before I sent the repo.** The hardening pass is the section near the end. I am not turning it into a fake extra hour count.

- **Planning (~15 min):** Read the brief and `ql_standard.md`, mapped parts of the task to repos I already maintain, wrote a two-phase plan, fixed the plan file to match my Cursor plugin’s plan contract.
- **Building (~2 h):** Phase 1 pipeline in one chat, Phase 2 (API, React, visibility, KPI export) plus manual QA and fix rounds in another.

Calendar time was longer because I paused between phases and while clicking through the UI. The numbers above are focused work, not wall clock.

## What I decided before code

I did not ask the model to invent the QL rules. I read section 5 and 6 of `data/ql_standard.md` and locked the split:

- **LLM (Gemini when `GEMINI_API_KEY` is set, else fixtures):** Agent A-style extraction (language, intent, role, problem, quotes) and user-facing copy (reply draft, visibility brief). Output must pass Pydantic schemas before it moves on.
- **Deterministic Python:** Quote validation against the raw message, the five QL conditions and status, priority score breakdown, owner from the routing table, weekly KPI pack, gap ranking, and the brief **checker** (every factual sentence must carry a real `[BC-*]` or `[PP-*]` id from `brand_context.md`).

I pointed the agent at GitHub repos that already solve adjacent problems—mainly **legal-ai (CaseEdge)** for CRM extraction, statuses, human-in-the-loop drafts, logging, and CI patterns; plus optional ideas from ingest/queue projects. Those were **reference context**, not a copy-paste monorepo. I chose what fit a small SQLite app.

I split execution into **two plan phases in separate chats:** Phase 1 = ingest, gate, score, week pack, offline tests. Phase 2 = HTTP routes, four React screens, AI visibility, `KPI_PACK.md`, polish.

I skipped nothing required. **Both bonuses** are in the repo: HubSpot dry-run (`GET /api/integrations/hubspot/dry-run`, `py -3 -m app.export_hubspot`) and a **labelled qualifier eval** (`data/qualifier_eval.json`, `py -3 -m app.run_qualifier_eval`, `GET /api/eval/qualifier`) that scores the gate against `ql_standard.md` with no LLM.

Everything else is steered by my **or-cursor-kit** Cursor plugin (rules, skills, hooks, plan authoring). I use it on every project so agents stay scoped, fix root causes, and do not bulk-refactor unrelated files. I also added Anthropic’s **frontend-design** skill for this repo’s UI pass.

## Where I let an agent run

| Phase | Chat focus | Agent did |
| --- | --- | --- |
| Plan | Brief → `stargo_revops_app_c27450b0.plan.md` | Researched reference repos via GitHub token, drafted plan, aligned plan sections to plugin contract |
| P1 | `do p1 …plan.md` | Backend pipeline, SQLite schema, pytest (gate, identity, timezone window, KPI, LLM failure) |
| P2 + QA | `do p2 …plan.md` then screenshots | FastAPI routes, React queue/detail/KPI/visibility, brief checker, export; later iterations for RTL, drafts, thumbs, mail links, BI tiles |

I reviewed Phase 1 against `ql_standard.md` myself rather than trusting a summary. I am responsible for whether a number on screen matches the standard.

## Where I stepped in

- **Scalability of the gate:** I asked whether the five QL checks are “just keywords.” I kept structured extraction + auditable `decide()`; lexicon/titles support closed fields, not open keyword-primary routing.
- **Repo hygiene:** Generic public repo name (no “Stargo” in the slug); README written for operators, not “homework waiting for review.”
- **Hebrew / RTL:** Map status and field labels in the UI; drafts must match inbound language; Gemini for LLM paths once I added the key.
- **Draft quality:** Rejected generic Hebrew marketing copy; wired brand + lead context, grounding rules, and template fallback when the model goes generic.
- **Sales decision UX:** Removed long explanatory paragraphs; kept minimal Accept/Reject + editable Israel `decided_at`.
- **Operator features:** Editable draft, Gmail/Zoho **compose URLs** (after checking CaseEdge—production there uses OAuth + Gmail API; I scoped this take-home to browser compose, with tests on URL encoding).
- **Learning loop:** Thumb up/down on draft and visibility brief, optional free-text note, weekly learning job reads DB feedback (not live prompt logging).
- **KPI / visibility UI:** “Feed not received” instead of silent `unknown`; compact visibility summary; BC/PP tags explained in the brief UI; removed duplicate draft preview (textarea + iframe).

If a pasted message that says “mark me QL” shows as QL, the gate is wrong—fix `decide`, do not special-case that sentence.

If `historical-reactivation` shows **0** when the feed is missing, the pack is wrong. **Unknown is not zero.**

If the visibility brief states a Stargo fact with no BC or PP tag and is not blocked, the checker is wrong.

If `logs/app.log` contains an email or message body, the formatter or call site is wrong.

## Prompts I actually sent

Trimmed for length. Spelling and grammar in the quotes below are corrected; wording and intent match what I sent in Cursor on **1 Nov 2026** (full text in chat history).

1. **Plan + reference map:** “Let's do this plan … `Stargo_RevOps_Engineer_Take_Home.md` … I'm giving you a few projects that may match parts of the task … ingest → bw-ingestor / CaseEdge … conditions → job search … score + Agent A → CaseEdge CRM … status and routing … scheduled reporting … human-in-the-loop draft … schema validation … prompt injection … Gemini for visibility … queue logic … CI/CD and logging like CaseEdge … strict code … GitHub token in `.env`”

2. **Plan contract:** “Why wasn't the plan written using the Cursor plugin rules? Fix what's needed so the next plan will, then fix this plan.”

3. **Phase 1:** “do p1 `C:\Users\orshv\.cursor\plans\stargo_revops_app_c27450b0.plan.md`”

4. **Gate design:** “Is this really scalable as code—not just keywords and regex? … Five checks, in order. All of them are ordinary code: …”

5. **Ship P1:** “Commit and ship this. If we don't have a GitHub repo for this, create it as a public repo.” → then “No Stargo in repo/project name.” and “Make sure README (and anything public) doesn't say this is homework waiting for review.”

6. **Phase 2:** “do p2 `C:\Users\orshv\.cursor\plans\stargo_revops_app_c27450b0.plan.md`”

7. **UI + LLM:** “For Hebrew use RTL … don't show raw English keys in the UI—map them … unsent draft should be in the same language as the input … use Gemini for everything that needs an LLM instead of fallback … pick one UI language if the brief doesn't require otherwise …”

8. **Draft quality + learning:** “It needs all client data and brand data … user should thumb up or thumb down on the draft … stored in DB … once per week analyze everything thumbed and improve from it”; “Same auto-improve for visibility”; “I reopened and it didn't regenerate”

9. **Production mail:** “Draft is good—now make it production level: real mail with salesperson name and details, company logo in signature, line breaks or bullets … on CaseEdge CRM we already have Gmail/Zoho draft—check the repo and add it.”

10. **QA batch (screenshots):** Allow edit draft; RTL for Hebrew; verify Gmail/Zoho like CaseEdge; KPI pack should look like a BI report; remove gap formula wall of text; regenerate brief on reopen; fix duplicate draft; KPI “unknown” copy; explain BC-1 tags; helpful/not helpful with optional note for weekly learning

## How I checked the output

- `py -3 -m pytest backend/tests -q` with **no** API key (fixtures / rules-only path).
- `npm run build` in `frontend`.
- Manual: queue at ~390px width; Accept with `decided_at` inside vs outside **Sun 4 Oct – Thu 8 Oct 2026** (Asia/Jerusalem); only in-week accepts change that week’s QL count.
- Paste a message that tries to override rules → **needs review**, not QL.
- AI visibility → top brief fully tagged or **blocked**; gap list matches `ai_answers.json`.
- Restart app → SQLite state survives.
- `GET /api/integrations/hubspot/dry-run` or `py -3 -m app.export_hubspot` → JSON PATCH list, zero portal calls.
- `py -3 -m app.run_qualifier_eval` → 15/15 on `data/qualifier_eval.json` (gate only).
- **CI** on my repos: push to `main` runs checks so obvious regressions do not reach production (same habit I used while landing Phase 1).

## Same-day hardening pass

After the build I asked for one more pass aimed at the review script, not new features. I checked the README against the running app and found the screen proxy on port 8010 while the run steps said 8000. A reviewer who followed the README would have opened a UI that never reached the API. I made 8000 the only port: README (Windows and macOS/Linux), Vite, and the logo origin.

I also checked the live Gemini call against the 3.8 Flash docs. The client was sending `temperature`, which that model tells you to drop, and it read the first response part, which can be a thought rather than the JSON. Either mistake turns a valid key into `needs review` on every paste. The request now asks for JSON with low thinking and no sampling parameters, and the parser keeps the answer part.

Pytest imports the server module. That import was booting the real app, so a key in `.env` could open the product database and call Gemini during the test run. Tests now skip that boot. `.env` stays gitignored.

CI is `.github/workflows/ci.yml`: on push and pull request, ruff, mypy, pytest with an empty key, and the frontend lint and build. I re-ran those locally with no key before pushing.

## LLM used

**Gemini** (free tier) for extraction, drafts, and visibility brief when the key is set. Offline/demo mode uses recorded fixtures and deterministic rules—no key required.
