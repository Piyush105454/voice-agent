from pathlib import Path
p = Path("db.py"); s = p.read_text(encoding="utf-8")
old = '''    """Idempotent per call_id: Bolna may call get_session_context more than once on a call."""
    if call_id:'''
new = '''    """Idempotent per call_id: Bolna may call get_session_context more than once on a call."""
    call_id = (call_id or "").strip() or None      # an unfilled prompt variable arrives as "" -> treat as unknown
    if call_id and call_id.startswith("{"):
        call_id = None
    if call_id:'''
assert old in s; s = s.replace(old, new)
old2 = '''def append_transcript('''
new2 = '''def bind_call(session_id: str, call_id: str) -> None:
    """Attach Bolna's execution id to a session created before/without it (so the post-call webhook finds it)."""
    run("update sessions set bolna_call_id=%s where id::text=%s and bolna_call_id is null", (call_id, session_id))


def open_phone_session(student_id: str, minutes: int = 20) -> dict | None:
    """The student's latest phone session that has no Bolna id yet (created moments ago for this call)."""
    return one("""select id::text, student_id::text, status from sessions where student_id::text=%s and channel='phone'
                  and bolna_call_id is null and started_at > now() - make_interval(mins => %s)
                  order by started_at desc limit 1""", (student_id, minutes))


def set_session_started(session_id: str, started_at) -> None:
    run("update sessions set started_at=%s where id::text=%s", (started_at, session_id))


def learner_profile(student_id: str) -> dict | None:
    """Guru's running picture of the student (rewritten after every call; latest wins)."""
    r = one("""select content, created_at from memory_facts where student_id::text=%s and kind='note'
               and content->>'type'='profile' and superseded_by is null order by created_at desc limit 1""",
            (student_id,))
    return {**r["content"], "updated_at": r["created_at"]} if r else None


def save_learner_profile(student_id: str, profile: dict, session_id: str | None) -> None:
    with tx() as conn:
        new_id = conn.execute("""insert into memory_facts(student_id, kind, content, confidence, source_session)
                                 values (%s,'note',%s,0.8,%s) returning id::text""",
                              (student_id, json({**profile, "type": "profile"}), session_id)).fetchone()["id"]
        conn.execute("""update memory_facts set superseded_by=%s where student_id::text=%s and kind='note'
                        and content->>'type'='profile' and superseded_by is null and id::text<>%s""",
                     (new_id, student_id, new_id))


def append_transcript('''
assert old2 in s; s = s.replace(old2, new2, 1)
p.write_text(s, encoding="utf-8"); print("ok")
