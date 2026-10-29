"""Guru Line API: Bolna tools, Sarvam web-call fallback, simulator, dashboard feeds."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import coach
import db
import graph
import phone
import service
import voice_router
import webcall
from bolna import BOLNA_IPS
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = FastAPI(title="Guru Line API")


@app.on_event("startup")
def _warm_llm_schemas() -> None:
    """Claude compiles each structured-output schema on first use (measured ~10 s, then cached). Send each coach
    schema once in the background at startup so no student's first turn pays for it."""
    if not settings.anthropic_api_key:
        return
    import threading

    def warm():
        import coach
        from llm import chat
        msgs = [{"role": "user", "content": "(warm-up: reply with minimal valid values)"}]
        for schema, purpose in ((coach.TURN_SCHEMA, "chat"), (coach.PLAN_SCHEMA, "eval"),
                                (coach._review_schema("coach"), "eval"), (coach._review_schema("english"), "eval"),
                                (coach._review_schema("topic"), "eval"), (coach.PROFILE_SCHEMA, "eval")):
            chat("Warm-up request. Keep every value very short.", msgs, schema, max_tokens=2000, timeout=60,
                 purpose=purpose)
    threading.Thread(target=warm, daemon=True, name="schema-warmup").start()

    def recover():
        try:
            import learning_graph
            for r in db.all_rows("select distinct student_id::text as id from session_reviews"):
                learning_graph.sync_safely(r["id"])
        except Exception as e:
            logging.getLogger("bolna").warning("learning graph backfill skipped: %s", e)
        try:
            out = phone.sync_recent_calls(phone_transcript, 20)
            if out["saved"]:
                logging.getLogger("bolna").info("recovered %d phone call(s) from Bolna history", len(out["saved"]))
        except Exception as e:
            logging.getLogger("bolna").warning("bolna call recovery skipped: %s", e)
    if settings.bolna_api_key:
        threading.Thread(target=recover, daemon=True, name="bolna-recover").start()
STATIC = Path(__file__).resolve().parent / "static"


@app.exception_handler(service.ServiceError)
async def _service_error(_: Request, e: service.ServiceError):
    return JSONResponse({"error": e.message}, status_code=e.status)


@app.exception_handler(voice_router.VoiceError)
async def _voice_error(_: Request, e: voice_router.VoiceError):
    return JSONResponse({"error": e.message}, status_code=e.status)


# ---------------------------------------------------------------- auth


def verify_webhook(request: Request, x_webhook_secret: str = Header(default=""),
                   authorization: str = Header(default="")):
    """Bolna has no HMAC: shared secret header (or Bearer api_token, or ?key= for the post-call webhook,
    whose custom headers can only be set in the dashboard) + optional egress-IP allowlist."""
    ok = (x_webhook_secret == settings.webhook_secret or authorization == f"Bearer {settings.webhook_secret}"
          or request.query_params.get("key") == settings.webhook_secret)
    if not ok:
        raise HTTPException(401, "bad secret")
    if settings.bolna_ip_allowlist:
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")) \
            .split(",")[0].strip()
        if ip not in BOLNA_IPS:
            raise HTTPException(403, "ip not allowed")


def verify_admin(x_admin_key: str = Header(default="")):
    if x_admin_key != settings.admin_key:
        raise HTTPException(401, "admin key required")


# ---------------------------------------------------------------- health


@app.get("/health")
def health():
    checks: dict[str, str] = {}
    for name, fn in (("postgres", db.ping), ("falkordb", graph.ping)):
        try:
            fn()
            checks[name] = "ok"
        except Exception as e:  # report, don't crash
            checks[name] = f"error: {type(e).__name__}: {e}"[:200]
    ok = all(v == "ok" for v in checks.values())
    voice = voice_router.status()
    return JSONResponse({"ok": ok, **checks, "voice": {"active": voice["active"], "mode": voice["mode"]}},
                        status_code=200 if ok else 503)


# ---------------------------------------------------------------- Bolna tools (agent.md §4.3)


class CtxIn(BaseModel):
    student_id: str
    call_id: str | None = None


class AnsIn(BaseModel):
    session_id: str
    question_id: str
    student_answer_text: str = ""


class ConfIn(BaseModel):
    session_id: str
    topic: str | None = None
    phase: str
    value: int = Field(ge=1, le=10)


class EndIn(BaseModel):
    session_id: str
    safety_flag: bool = False


@app.post("/bolna/get_session_context", dependencies=[Depends(verify_webhook)])
def bolna_ctx(b: CtxIn):
    """Opens the call's session and returns what Guru remembers (last call, goals, confidence, weekly trend)."""
    return phone.open_session(b.student_id, b.call_id)


class LangIn(BaseModel):
    session_id: str
    language: str


class TopicIn(BaseModel):
    session_id: str
    mode: str
    topic: str | None = None


class GoalSetIn(BaseModel):
    session_id: str
    aim: str = Field(min_length=3, max_length=200)


@app.post("/bolna/set_language", dependencies=[Depends(verify_webhook)])
def bolna_language(b: LangIn):
    return phone.set_language(b.session_id, b.language)


@app.post("/bolna/choose_topic", dependencies=[Depends(verify_webhook)])
def bolna_topic(b: TopicIn):
    return phone.choose_topic(b.session_id, b.mode, b.topic)


class SuggestionIn(BaseModel):
    session_id: str
    kind: str = "method"
    title: str = Field(min_length=2, max_length=160)
    by: str | None = None
    why: str = ""


@app.post("/bolna/save_suggestion", dependencies=[Depends(verify_webhook)])
def bolna_suggestion(b: SuggestionIn):
    return phone.save_suggestion(b.session_id, b.kind, b.title, b.by, b.why)


@app.get("/students/{sid}/journal", dependencies=[Depends(verify_admin)])
def student_journal(sid: str):
    """Day-by-day learning journal + the books, quotes and methods Guru suggested."""
    return {"days": db.journal(sid), "resources": db.recent_resources(sid, 12), "profile": db.learner_profile(sid)}


@app.post("/bolna/set_goal", dependencies=[Depends(verify_webhook)])
def bolna_goal(b: GoalSetIn):
    return phone.set_goal(b.session_id, b.aim)


@app.post("/bolna/submit_answer", dependencies=[Depends(verify_webhook)])
def bolna_submit(b: AnsIn):
    return service.submit_answer(b.session_id, b.question_id, b.student_answer_text)


@app.post("/bolna/log_confidence", dependencies=[Depends(verify_webhook)])
def bolna_conf(b: ConfIn):
    return service.log_confidence(b.session_id, b.topic, b.phase, b.value)


@app.post("/bolna/end_session", dependencies=[Depends(verify_webhook)])
def bolna_end(b: EndIn):
    return phone.end(b.session_id, b.safety_flag)


@app.post("/bolna/webhook", dependencies=[Depends(verify_webhook)])
def bolna_post_call(payload: dict):
    """Post-call webhook: sent on every status change (same id repeated). Store the full transcript and
    close the session if the agent never called end_session. Idempotent."""
    return phone.handle_webhook(payload, phone_transcript)


@app.post("/bolna/sync", dependencies=[Depends(verify_admin)])
def bolna_sync(limit: int = 20):
    """Recover calls whose webhook never arrived (tunnel down etc.) from Bolna's call history."""
    return phone.sync_recent_calls(phone_transcript, limit)


def phone_transcript(sess: dict, raw: str) -> str:
    """Bolna sends "assistant: ..."/"user: ..." lines; store them as "Guru: ..."/"<name>: ..." like browser calls.
    Phone STT writes English speech in Devanagari ("यस, मैं ठीक हूँ"): for English/Hinglish speakers those student
    lines are transliterated to Latin script so the chat view and the evaluation read naturally."""
    import sarvam
    st = db.student(sess["student_id"]) or {}
    name = st.get("first_name") or "Student"
    roman = st.get("language") in ("en", "hi-en") and sarvam.enabled()
    out = []
    for line in raw.splitlines():
        who, sep, text = line.partition(":")
        role = who.strip().lower()
        if not sep or role not in ("assistant", "user", "agent", "bot", "human"):
            out.append(line)
            continue
        text = text.strip()
        if role in ("user", "human"):
            if roman and sarvam.has_devanagari(text):
                try:
                    text = sarvam.transliterate(text)
                except Exception:
                    pass
            out.append(f"{name}: {text}")
        else:
            out.append(f"Guru: {text}")
    return "\n".join(out)


@app.get("/bolna/inbound_lookup", dependencies=[Depends(verify_webhook)])
def bolna_inbound(contact_number: str):
    """Caller identification for inbound calls (must answer < 3 s). Keys become prompt variables."""
    st = db.student_by_phone(contact_number)
    if not st:
        return {"student_id": "", "first_name": "", "known_caller": "false", "session_id": "",
                "greeting": coach.UNKNOWN_CALLER,
                "memory": "This caller has not signed up yet, so you know nothing about them. Be warm and respectful: "
                          "learn their name, ask what they study or want to get better at, help with one small thing, "
                          "and tell them that signing up on the Guru Line website lets you remember them next time. "
                          "Do not call any tools."}
    if not db.has_consent(st["id"]):
        return {"student_id": st["id"], "first_name": st["first_name"], "known_caller": "true", "session_id": "",
                "greeting": f"Namaste {coach.spoken_name(st['first_name'])}! Guru bol raha hoon. Hum baat shuru "
                            "karein, usse pehle aapke parent ki permission chahiye. Dhanyavaad, jaldi milte hain!",
                "memory": "No consent on file: end the call politely."}
    sess = db.create_session(st["id"], None, "phone", None, "open")
    return {**phone.call_variables(st["id"], sess["id"]), "language": st["language"], "known_caller": "true"}


@app.api_route("/missed_call", methods=["GET", "POST"])
async def missed_call(request: Request, key: str = "", From: str = "", phone: str = ""):
    """Telephony missed-call hook (Exotel/Plivo can't always set headers -> ?key=WEBHOOK_SECRET)."""
    if key != settings.webhook_secret and request.headers.get("x-webhook-secret") != settings.webhook_secret:
        raise HTTPException(401, "bad secret")
    if request.method == "POST" and not (From or phone):
        try:
            form = await request.form()
            From = str(form.get("From") or form.get("from") or "")
        except Exception:
            body = await request.json()
            From = str(body.get("From") or body.get("phone") or "")
    number = From or phone
    st = db.student_by_phone(number)
    if not st:
        return {"ok": False, "reason": "unknown number"}
    return {"ok": True, **voice_router.start_call(st["id"])}


# ---------------------------------------------------------------- voice routing (admin)


class CallIn(BaseModel):
    student_id: str
    provider: str | None = None   # auto | bolna | sarvam (override)


@app.post("/voice/call", dependencies=[Depends(verify_admin)])
def voice_call(b: CallIn):
    """Start a tutoring call: Bolna phone call, or a Sarvam web-call link if Bolna is out of credit."""
    return voice_router.start_call(b.student_id, b.provider)


@app.get("/voice/status", dependencies=[Depends(verify_admin)])
def voice_status():
    return voice_router.status()


@app.post("/voice/reset_bolna", dependencies=[Depends(verify_admin)])
def voice_reset():
    """Call after topping up Bolna credit to stop routing to Sarvam before the cooldown ends."""
    voice_router.reset_bolna()
    return voice_router.status()


# ---------------------------------------------------------------- Sarvam web call (student-facing, signed link)


class TokenIn(BaseModel):
    token: str


class StartIn(TokenIn):
    mode: str = "coach"   # coach (open, default) | maths | english | topic


@app.get("/call")
def call_page():
    return FileResponse(STATIC / "call.html", headers={"Cache-Control": "no-store"})


@app.post("/web-call/start")
def web_start(b: StartIn):
    student_id = voice_router.read_token(b.token)
    out = webcall.start(b.token, student_id, b.mode)
    return {**out, "first_name": db.student(student_id)["first_name"]}


@app.post("/web-call/turn")
def web_turn(token: str = Form(...), text: str | None = Form(default=None),
             audio: UploadFile | None = File(default=None)):
    voice_router.read_token(token)
    data = audio.file.read() if audio else None
    if data and len(data) > 5_000_000:
        raise HTTPException(413, "utterance too long")
    return webcall.turn(token, text=text, audio=data or None, filename=(audio.filename if audio else None)
                        or "audio.webm", content_type=(audio.content_type if audio else None) or "audio/webm")


@app.post("/web-call/end")
def web_end(b: TokenIn):
    voice_router.read_token(b.token)
    return webcall.hang_up(b.token)


# ---------------------------------------------------------------- simulator (same core, zero voice credits)


class SimIn(BaseModel):
    student_id: str
    message: str = ""
    session_id: str | None = None
    question_id: str | None = None


@app.post("/simulate", dependencies=[Depends(verify_admin)])
def simulate(b: SimIn):
    if not b.session_id:
        return service.get_context(b.student_id, channel="simulator")
    if not b.question_id:
        raise HTTPException(422, "question_id required")
    return service.submit_answer(b.session_id, b.question_id, b.message)


@app.post("/simulate/confidence", dependencies=[Depends(verify_admin)])
def simulate_conf(b: ConfIn):
    return service.log_confidence(b.session_id, b.topic, b.phase, b.value)


@app.post("/simulate/end", dependencies=[Depends(verify_admin)])
def simulate_end(b: EndIn):
    return service.end_session(b.session_id, b.safety_flag)


# ---------------------------------------------------------------- dashboard feeds (admin, via the web proxy)


@app.get("/students", dependencies=[Depends(verify_admin)])
def students():
    return db.list_students()


class SignUpIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=40)
    grade: int | None = Field(default=None, ge=1, le=12)   # only for school students; Guru is for anyone
    about: str | None = Field(default=None, max_length=120)  # "college student", "working in sales", "job seeker"…
    language: str | None = None        # hi | en | hi-en | None (Guru asks on the first call)
    is_minor: bool = True
    phone: str | None = None           # E.164, optional ("Call my phone")
    consent: bool = False              # recording + sharing with teacher/parent, agreed once here


@app.post("/students", dependencies=[Depends(verify_admin)])
def sign_up(b: SignUpIn):
    """New student joins: profile + consent captured once (calls never read a recording notice)."""
    if not b.consent:
        raise HTTPException(422, "consent is required to start practising")
    if b.language not in (None, "hi", "en", "hi-en"):
        raise HTTPException(422, "language must be hi, en or hi-en")
    phone = (b.phone or "").replace(" ", "") or None
    if phone and not (phone.startswith("+") and phone[1:].isdigit() and 8 <= len(phone) <= 16):
        raise HTTPException(422, "phone must look like +919876543210")
    sid = db.create_student(b.first_name, b.grade, b.language, b.is_minor, phone,
                            "guardian" if b.is_minor else "student_adult", b.about)
    if b.language:
        db.remember_language(sid, b.language, None)   # chosen at sign-up: Guru won't ask again
    try:
        graph.upsert_student(sid, b.first_name.strip(), b.grade)
    except Exception:
        pass  # graph is derived; rebuild_graph() repairs it
    db.audit("student", "sign_up", "student", sid)
    return {"student_id": sid}


@app.get("/students/{sid}", dependencies=[Depends(verify_admin)])
def student_detail(sid: str):
    st = db.student(sid)
    if not st:
        raise HTTPException(404, "unknown student")
    st.pop("phone_e164", None)  # never sent to the browser
    return {**st, "consented": db.has_consent(sid), "sessions": db.recent_sessions(sid)}


@app.get("/students/{sid}/graph", dependencies=[Depends(verify_admin)])
def student_graph(sid: str):
    import learning_graph
    g = graph.neighbourhood(sid, 80)
    if not g["nodes"]:
        return g
    try:
        nodes, links = learning_graph.nodes_for(sid)
    except Exception:
        nodes, links = [], []
    have = {n["id"] for n in g["nodes"]}
    g["nodes"] += [n for n in nodes if n["id"] not in have]
    g["links"] += links
    return g


@app.get("/students/{sid}/progress", dependencies=[Depends(verify_admin)])
def progress(sid: str):
    """Maths series + the coaching view: skills, self-reported confidence, research-ranked next steps, and
    per-call points (AI-judged skill average vs self-reported confidence) for the confidence chart."""
    import learning_graph
    out = db.progress_series(sid)
    coach_pts = db.all_rows("""select s.id::text as session_id, s.started_at, s.topic_id,
                                 (select avg(score)/10.0 from skill_scores k where k.session_id=s.id and k.source='llm')
                                   as accuracy,
                                 null::int as conf_before,
                                 (select round(score)::int from skill_scores k where k.session_id=s.id
                                   and k.source='self_report' limit 1) as conf_after
                               from sessions s where s.student_id::text=%s and s.mode in ('coach','english','topic')
                               order by s.started_at""", (sid,))
    seen = {p["session_id"] for p in out["session_points"] if p["accuracy"] is not None}
    out["session_points"] = sorted([p for p in out["session_points"] if p["session_id"] not in
                                    {c["session_id"] for c in coach_pts}] +
                                   [c for c in coach_pts if c["session_id"] not in seen],
                                   key=lambda p: p["started_at"])
    out["skills"] = [{k: v for k, v in s.items() if k != "last"} for s in learning_graph.skills(sid)]
    out["self_confidence"] = learning_graph.confidence(sid)
    out["next_steps"] = learning_graph.next_steps(sid)
    return out


@app.get("/students/{sid}/memory", dependencies=[Depends(verify_admin)])
def export_memory(sid: str):
    db.audit("guardian_or_teacher", "export_memory", "student", sid)
    return db.export_memory(sid)


@app.delete("/students/{sid}/memory", dependencies=[Depends(verify_admin)])
def delete_memory(sid: str):
    counts = db.delete_student_memory(sid)
    graph.delete_student(sid)
    st = db.student(sid)
    if st:  # keep the bare node so the student can be tutored again from a clean slate
        graph.upsert_student(sid, st["first_name"], st["grade"])
    db.audit("guardian", "delete_memory", "student", sid)
    return {"deleted": True, "rows": counts}


@app.delete("/students/{sid}/memory/{fact_id}", dependencies=[Depends(verify_admin)])
def delete_fact(sid: str, fact_id: str):
    """Forget one remembered fact (and its graph edge for strategies/goals)."""
    fact = db.one("""delete from memory_facts where id::text=%s and student_id::text=%s
                     returning kind, content->>'id' as key""", (fact_id, sid))
    if not fact:
        raise HTTPException(404, "unknown fact")
    try:
        if fact["kind"] == "strategy" and not db.one(
                """select 1 as ok from memory_facts where student_id::text=%s and kind='strategy'
                   and content->>'id'=%s""", (sid, fact["key"])):
            graph.q("MATCH (:Student {id:$s})-[r:RESPONDS_WELL_TO]->(:Strategy {id:$k}) DELETE r",
                    {"s": sid, "k": fact["key"]})
        elif fact["kind"] == "goal":
            graph.q("MATCH (g:Goal {id:$g}) DETACH DELETE g", {"g": fact_id})
    except Exception:
        pass  # graph is derived; rebuild_graph() repairs it
    db.audit("guardian", "delete_memory_fact", "student", sid)
    return {"deleted": True, "kind": fact["kind"]}


class GoalIn(BaseModel):
    mode: str
    aim: str = Field(min_length=3, max_length=200)


class PeriodIn(BaseModel):
    period: str = "week"


def _period(p: str) -> str:
    if p not in ("day", "week", "month"):
        raise HTTPException(422, "period must be day, week or month")
    return p


@app.get("/students/{sid}/goals", dependencies=[Depends(verify_admin)])
def goals(sid: str):
    return db.list_goals(sid)


@app.post("/students/{sid}/goals", dependencies=[Depends(verify_admin)])
def add_goal(sid: str, b: GoalIn):
    import coach
    if b.mode not in ("maths", *coach.MODES):
        raise HTTPException(422, "mode must be maths, english or topic")
    if not db.student(sid):
        raise HTTPException(404, "unknown student")
    gid = coach.set_goal(sid, b.mode, b.aim, None)
    return {"goal_id": gid, "plan": "generating"}


@app.get("/students/{sid}/skills", dependencies=[Depends(verify_admin)])
def skills(sid: str, period: str = "week"):
    return {"period": _period(period), "series": db.skill_series(sid, period),
            "reviews": db.all_rows("""select r.session_id::text, r.mode, r.summary, r.strengths, r.improvements,
                                             r.next_steps, r.quiz_correct, r.quiz_total, r.created_at
                                      from session_reviews r where r.student_id::text=%s
                                      order by r.created_at desc limit 20""", (sid,))}


@app.post("/students/{sid}/coach-feedback", dependencies=[Depends(verify_admin)])
def coach_feedback(sid: str, b: PeriodIn):
    import coach
    return coach.progress_feedback(sid, _period(b.period))


@app.get("/teacher/overview", dependencies=[Depends(verify_admin)])
def teacher_overview():
    db.audit("teacher:Ms. Sharma", "view", "class", "overview")
    return {**db.teacher_overview(), "heatmap": db.class_heatmap()}


@app.get("/students/{sid}/overview", dependencies=[Depends(verify_admin)])
def student_overview(sid: str):
    out = db.student_overview(sid)
    if not out:
        raise HTTPException(404, "unknown student")
    try:
        out["weak_prerequisite"] = graph.weakest_prerequisite(sid, out["focus_topic"])
    except Exception:
        out["weak_prerequisite"] = None
    db.audit("teacher:Ms. Sharma", "view", "student", sid)
    return out


@app.get("/parent/{sid}", dependencies=[Depends(verify_admin)])
def parent_view(sid: str):
    out = db.parent_view(sid)
    if not out:
        raise HTTPException(404, "unknown student")
    db.audit("guardian", "view", "parent_update", sid)
    return out


@app.get("/privacy/{sid}", dependencies=[Depends(verify_admin)])
def privacy_view(sid: str):
    out = db.privacy_view(sid)
    if not out:
        raise HTTPException(404, "unknown student")
    return out


@app.get("/proof", dependencies=[Depends(verify_admin)])
def proof():
    return {"eval": db.latest_eval(), "pilot": db.pilot_cards()}


@app.get("/sessions/{session_id}/feed", dependencies=[Depends(verify_admin)])
def session_feed(session_id: str):
    out = db.session_feed(session_id)
    if not out:
        raise HTTPException(404, "unknown session")
    return out


@app.get("/live/current", dependencies=[Depends(verify_admin)])
def live_current(student_id: str | None = None):
    """The session the live console should show: the active one, else the most recent."""
    s = db.latest_session(student_id)
    return {"session": s}


class ReplayIn(BaseModel):
    student_id: str = "11111111-1111-4111-8111-111111111111"
    delay: float = Field(default=2.0, ge=0, le=10)


@app.post("/demo/replay", dependencies=[Depends(verify_admin)])
def demo_replay(b: ReplayIn):
    import demo
    return demo.replay(b.student_id, b.delay)


@app.post("/demo/reset", dependencies=[Depends(verify_admin)])
def demo_reset():
    """Drop + re-seed the demo database and rebuild the graph (back to Rahul's BEFORE state)."""
    from graph_seed import rebuild_graph
    from pg import run_script
    root = Path(__file__).resolve().parent.parent / "sql"
    for f in ("drop.sql", "schema.sql", "seed.sql"):
        run_script((root / f).read_text(encoding="utf-8"))
    if settings.demo_student_phone:
        db.run("update students set phone_e164=%s where first_name='Rahul'", (settings.demo_student_phone,))
    for fn in (db.misconception_descriptions, db.misconception_names, db.topic_names):
        fn.cache_clear()
    return {"ok": True, "graph": rebuild_graph()}


@app.get("/events", dependencies=[Depends(verify_admin)])
def events_poll(student_id: str | None = None, after_id: int = 0):
    return db.recent_events(student_id, after_id)


@app.get("/events/stream", dependencies=[Depends(verify_admin)])
def events_stream(student_id: str | None = None):
    """SSE fallback when Supabase Realtime is not configured (Postgres LISTEN/NOTIFY)."""
    import psycopg

    def gen():
        with psycopg.connect(settings.database_url, autocommit=True) as conn:
            conn.execute("LISTEN live_events")
            yield "retry: 2000\n\n"
            while True:
                got = False
                for n in conn.notifies(timeout=15, stop_after=1):
                    got = True
                    if student_id and f'"student_id":"{student_id}"' not in n.payload.replace(" ", ""):
                        continue
                    yield f"data: {n.payload}\n\n"
                if not got:
                    yield ": keep-alive\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/admin/rebuild_graph", dependencies=[Depends(verify_admin)])
def rebuild():
    from graph_seed import rebuild_graph
    return rebuild_graph()
