

# ---------------------------------------------------------------- per-call variables, webhook binding, recovery


def call_variables(student_id: str, session_id: str | None = None) -> dict:
    """Prompt variables for one Bolna call: the spoken opening (greeting -> language question for a new student,
    else a link to the last call + what to improve) and Guru's memory of the student, so the call is personal
    from the first second even if a tool call is slow or fails."""
    st = db.student(student_id)
    if not st:
        return {}
    st = {**st, "id": student_id}
    memory_txt = coach.coach_memory(st).replace("{", "(").replace("}", ")")
    return {"student_id": student_id, "first_name": st["first_name"], "session_id": session_id or "",
            "greeting": coach.opening_line(st).replace("{", "(").replace("}", ")"), "memory": memory_txt}


def _student_from_payload(payload: dict) -> str | None:
    ctx = payload.get("context_details") or {}
    data = ctx.get("recipient_data") or payload.get("user_data") or {}
    sid = data.get("student_id") if isinstance(data, dict) else None
    if not sid:
        num = ctx.get("recipient_phone_number") or payload.get("user_number")
        st = db.student_by_phone(num) if num else None
        sid = st["id"] if st else None
    return sid if sid and db.student(sid) else None


def session_for_call(payload: dict) -> dict | None:
    """Find (or make) the session for a Bolna execution: by call id, else the session id we passed in, else the
    student's fresh phone session without an id, else a new one, so a call is never lost."""
    call_id = str(payload.get("id") or "").strip()
    if not call_id:
        return None
    sess = db.session_by_call_id(call_id)
    if sess:
        return sess
    student_id = _student_from_payload(payload)
    if not student_id:
        return None
    data = (payload.get("context_details") or {}).get("recipient_data") or {}
    passed = data.get("session_id") if isinstance(data, dict) else None
    cand = db.get_session(passed) if passed else None
    if not (cand and cand["student_id"] == student_id and not cand.get("bolna_call_id")):
        cand = db.open_phone_session(student_id)
    if cand:
        db.bind_call(cand["id"], call_id)
    else:
        if not payload.get("transcript"):
            return None           # nothing to keep yet (e.g. "ringing")
        new = db.create_session(student_id, call_id, "phone", None, "open")
        if payload.get("created_at"):
            db.set_session_started(new["id"], payload["created_at"])
    return db.session_by_call_id(call_id)


ENDED = ("completed", "call-disconnected", "failed", "no-answer", "busy", "canceled", "stopped", "error")


def handle_webhook(payload: dict, transcript_fn) -> dict:
    """Post-call webhook (sent on every status change). Saves the transcript, closes the session, then runs the
    review + learner-profile update in the background. Idempotent."""
    status = str(payload.get("status", "")).lower()
    sess = session_for_call(payload)
    if not sess:
        return {"ok": True, "ignored": "no student for this call"}
    if payload.get("transcript"):
        db.set_transcript(sess["id"], transcript_fn(sess, str(payload["transcript"])))
    if status in ENDED:
        full = db.get_session(sess["id"])
        if full["mode"] == "open":   # never picked a topic: it was an open coaching chat
            db.run("update sessions set mode='coach' where id::text=%s", (sess["id"],))
        first_close = not full["ended_at"]
        end(sess["id"])
        if first_close or not db.learner_profile_from(sess["id"]):
            coach._background(coach.after_call, sess["id"])
        events.emit(sess["student_id"], "session_saved", {"session_id": sess["id"], "channel": "phone"})
    return {"ok": True, "session_id": sess["id"]}


def sync_recent_calls(transcript_fn, limit: int = 20) -> dict:
    """Pull recent finished calls from Bolna and save any the webhook missed (tunnel down, older bug)."""
    import bolna
    saved = []
    for ex in bolna.recent_executions(limit):
        if str(ex.get("status", "")).lower() not in ENDED or not ex.get("transcript"):
            continue
        known = db.session_by_call_id(str(ex.get("id")))
        if known and db.get_session(known["id"]).get("transcript"):
            continue
        r = handle_webhook(ex, transcript_fn)
        if r.get("session_id"):
            saved.append(r["session_id"])
    return {"saved": saved}
