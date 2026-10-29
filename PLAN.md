# Guru Line — Build Plan

Source of truth: `agent.md`, `database-design.md`, `ui-design.md`. This file records *how* we build it,
in what order, and what can go wrong. Deadline: **31 Oct 2026**.

## Architecture decisions (and why)

| Decision | Why |
|---|---|
| Repo root = this folder (`api/`, `web/`, `sql/`, `tests/`, `scripts/`) | agent.md §2 layout, minus the extra `guruline/` wrapper. |
| API talks to Postgres via **psycopg 3 + `DATABASE_URL`** (Supabase's Postgres connection string in prod, local `postgres:16` container in dev) | Real SQL, transactions, `LISTEN/NOTIFY`; no REST round-trips. Service credentials stay server-side only. |
| `schema.sql` = database-design.md §2 verbatim **+ guarded Supabase-only bits** (`supabase_realtime` publication, `auth.uid()` RLS) **+ 1 additive table `learning_snapshots`** | Same file runs on plain Postgres and Supabase. Snapshots feed "mastery / misconception strength over time" charts (the spec's schema has no history table). |
| Realtime: **Supabase Realtime on `live_events`** when `NEXT_PUBLIC_SUPABASE_*` is set; otherwise **SSE** from the API (`/events/stream`, backed by a Postgres `NOTIFY` trigger on `live_events`) | ui-design.md requires Supabase Realtime; the SSE fallback makes the demo work with zero accounts. Both well under 1 s. |
| Browser never calls privileged API directly: Next.js route handler `/api/gl/*` proxies to FastAPI and injects `X-Admin-Key` server-side | Keeps admin key + service creds out of the browser; delete-memory/simulate are not world-callable. |
| Grading = deterministic first (spoken-number normaliser for Hinglish/English + `wrong_answer_map`), LLM (`judge_answer.md`) only for unmatched answers | Fast, free, testable; LLM handles STT noise. Works with no Anthropic key. |
| Hints = per-misconception template ladder, optional LLM rewrite (`hint_writer.md`), **post-filter rejects any level 1–2 hint containing the answer** | Hard guarantee for "never reveals before level 3". |
| `llm()` single wrapper, provider swappable; every LLM call has a deterministic fallback | Demo never dies because of an API key/timeout. |
| Bolna routes accept `X-Webhook-Secret` header (and the documented Bolna auth mechanism if it differs — verified in Phase 4) | agent.md §4.1, without inventing Bolna details. |
| `submit_answer` response adds `next_question` (additive to the §4.3 contract) | The voice agent needs the next question text after `praise_next` / `reveal`. |
| Windows-friendly: `Makefile` **and** `scripts/guru.ps1` with identical targets | `make` is not installed on this machine. |

## Phases

### Phase 1 — Infra + data
- `docker-compose.yml`: `postgres` (profile `local`), `falkordb`, `api`, `web`, `caddy` (profile `prod`), health checks on all.
- `docker-compose.override` not used; `make dev` = infra in Docker + API (uvicorn --reload) + web (next dev) on host.
- `sql/schema.sql`, `sql/seed.sql` (5 topics, prereqs, 6 misconceptions, **40 questions with `wrong_answer_map`**, teacher, class, 5 consented demo students + 1 un-consented student for the refusal demo, Rahul "before" arc + history for others).
- `api/config.py`, `api/db.py` (pool + base helpers), `api/graph.py`, `api/graph_seed.py` (`rebuild_graph()` < 5 s), `GET /health` (pg + falkordb).
- `scripts/reset_demo.py` → schema + seed + graph rebuild.
- Tests: seed integrity (40 Qs, every wrong-answer maps to a known misconception, answers parse), graph rebuild + root-cause query.

### Phase 2 — Backend
- All routes from agent.md §5.7 + export memory, teacher/parent/proof/privacy feeds, `/missed_call`, SSE stream.
- `tutor_judge`, `tutor_hint`, `safety.scan`, `summaries` (teacher EN + parent HI), `events.emit`, plan generation, `memory` extract/retrieve (+ forbidden-memory post-filter), nightly job (APScheduler).
- Tests: grading, BKT update/decay, hint ladder (no reveal < 3), consent refusal, graph root-cause, delete-memory (PG rows + graph node), full simulator flow, safety stop.

### Phase 3 — Web
- Next.js 14 App Router + Tailwind + framer-motion + react-force-graph-2d + Recharts.
- 7 pages: `/`, `/live`, `/students/[id]`, `/teacher`, `/parent/[id]`, `/proof`, `/privacy` (+ `/simulate` text simulator).
- Demo Mode, "Replay Rahul session", loading/empty/error states, reduced motion, keyboard/focus, mobile.

### Phase 4 — Voice
- Bolna agent config JSON + prompt (§4.2) + 4 tool definitions, exactly per current Bolna docs.
- Outbound trigger, missed-call hook, post-call webhook. `SETUP_NEEDED.md` click-list + manual test script.

### Phase 5 — Evals + proof
- `api/evals/run_eval.py`: 30 synthetic students (target misconception × noise × language), LLM student simulator with deterministic fallback, through the real `/simulate` path; `eval_report.json` + `eval_runs/eval_cases`; Proof page "X / 30 (synthetic)" + real-pilot cards.

### Phase 6 — Polish
- Perf pass (lazy graph, LCP), visual QA vs ui-design.md, README, 2-minute demo script, backup-demo checklist.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bolna tool/webhook format differs from agent.md sketch | Read current docs before Phase 4; anything unverifiable goes in `SETUP_NEEDED.md`. |
| Live call latency (LLM inside `submit_answer`) | Deterministic path first; LLM calls time-boxed (≈2.5 s) with fallback. |
| STT turns "saat" / "seventeen" / "minus paanch" into text | Hinglish + English number-word normaliser, unit-tested. |
| Supabase Realtime needs RLS read on `live_events` for the anon key | Payloads carry IDs + learning tags only (no names/phones); policy scoped to `live_events` select. Documented. |
| Docker on Windows / no `make` | `scripts/guru.ps1` mirrors every Makefile target. |
| Rahul demo numbers must land on 0.30 → 0.62, 3 → 6, 0.8 → 0.35 | Scripted replay tuned and covered by a test. |
| Over-claiming | UI copy reviewed: "self-reported confidence + quiz accuracy", synthetic labelled synthetic. |
| No dashboard auth beyond admin-key proxy | Optional `DASHBOARD_PASSWORD` basic-auth in Next middleware; teacher-per-class RLS policy shipped for Supabase. |
