"""One-off patch: student-led phone coach routes + webhook transcript cleanup/evaluation + coach confidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        assert a in s, f"{rel} MISSING: {a[:80]}"
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")


patch("api/main.py", [
    ('''@app.post("/bolna/get_session_context", dependencies=[Depends(verify_webhook)])
def bolna_ctx(b: CtxIn):
    return service.get_context(b.student_id, b.call_id, channel="phone")
''', '''@app.post("/bolna/get_session_context", dependencies=[Depends(verify_webhook)])
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


@app.post("/bolna/set_goal", dependencies=[Depends(verify_webhook)])
def bolna_goal(b: GoalSetIn):
    return phone.set_goal(b.session_id, b.aim)
'''),
    ('''def bolna_end(b: EndIn):
    return service.end_session(b.session_id, b.safety_flag)''', '''def bolna_end(b: EndIn):
    return phone.end(b.session_id, b.safety_flag)'''),
    ('''    if payload.get("transcript"):
        db.set_transcript(sess["id"], str(payload["transcript"]))
    if status in ("completed", "call-disconnected", "failed", "no-answer", "busy", "canceled", "stopped"):
        service.end_session(sess["id"])
    return {"ok": True}''', '''    if payload.get("transcript"):
        db.set_transcript(sess["id"], phone_transcript(sess, str(payload["transcript"])))
    if status in ("completed", "call-disconnected", "failed", "no-answer", "busy", "canceled", "stopped"):
        phone.end(sess["id"])
        full = db.get_session(sess["id"])
        # coach modes are evaluated once Bolna's full transcript is in (end_session ran mid-call, before it)
        if full["mode"] in coach.MODES and full["transcript"] and not db.session_review(sess["id"]):
            coach._background(coach._evaluate_safely, sess["id"])
    return {"ok": True}


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
    return "\\n".join(out)'''),
    ('''import db
import graph
import service''', '''import coach
import db
import graph
import phone
import service'''),
])

# Self-reported confidence in coach modes becomes a skill score (it is what the progress chart shows).
patch("api/service.py", [(
    '''    db.log_confidence(session_id, topic_id, phase, value)''',
    '''    db.log_confidence(session_id, topic_id, phase, value)
    if sess.get("mode") in ("english", "topic"):
        db.add_skill_scores(sess["student_id"], session_id, sess.get("goal_id"), {f"{sess['mode']}.confidence": value},
                            "self_report")''')])
print("patched")
