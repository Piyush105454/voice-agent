"""Domain-level Postgres helpers. All SQL lives here; routes stay thin."""
from __future__ import annotations

from functools import lru_cache

from pg import all_rows, json, one, run, tx

# ---------------------------------------------------------------- bulk reads (graph rebuild)


def all_topics() -> list[dict]:
    return all_rows("select id, name, subject from topics order by id")


def all_prereqs() -> list[dict]:
    return all_rows("select prereq_id, topic_id from topic_prereqs")


def all_misconceptions() -> list[dict]:
    return all_rows("select id, name, topic_id, description, example from misconception_types order by id")


def all_students() -> list[dict]:
    return all_rows("select id::text, first_name, grade from students order by first_name")


def all_mastery() -> list[dict]:
    return all_rows("""select student_id::text, topic_id, p_known, stability_days,
                              (extract(epoch from updated_at) * 1000)::bigint as updated_ms
                       from mastery""")


def all_student_misconceptions() -> list[dict]:
    return all_rows("""select student_id::text, misconception_id, strength, evidence_n,
                              (extract(epoch from first_seen) * 1000)::bigint as first_ms,
                              (extract(epoch from last_seen) * 1000)::bigint as last_ms
                       from student_misconceptions""")


def all_strategy_facts() -> list[dict]:
    return all_rows("""select student_id::text, content->>'id' as strategy_id, count(*)::int as n
                       from memory_facts where kind='strategy' and superseded_by is null
                         and confidence >= 0.4
                       group by 1, 2""")


def all_goal_facts() -> list[dict]:
    return all_rows("""select id::text, student_id::text, content->>'text' as text
                       from memory_facts where kind='goal' and superseded_by is null""")


def all_session_topics() -> list[dict]:
    """One row per (session, topic) with confidence before/after and accuracy."""
    return all_rows("""
        with acc as (
          select a.session_id, q.topic_id,
                 avg(case when a.correct then 1.0 else 0.0 end) as accuracy
          from attempts a join questions q on q.id = a.question_id group by 1, 2)
        select s.id::text as session_id, s.student_id::text, acc.topic_id, acc.accuracy,
               (select value from confidence_logs c where c.session_id=s.id and c.topic_id=acc.topic_id
                  and phase='before' order by created_at limit 1) as before_conf,
               (select value from confidence_logs c where c.session_id=s.id and c.topic_id=acc.topic_id
                  and phase='after' order by created_at desc limit 1) as after_conf
        from sessions s join acc on acc.session_id = s.id""")


# ---------------------------------------------------------------- people & consent


def student(student_id: str) -> dict | None:
    return one("""select id::text, first_name, language, grade, about, phone_e164, is_minor, active,
                         class_id::text, call_window_start, call_window_end
                  from students where id::text=%s""", (student_id,))


def student_by_phone(phone: str) -> dict | None:
    return one("select id::text, first_name, language from students where phone_e164=%s and active", (phone,))


def list_students() -> list[dict]:
    return all_rows("""select s.id::text, s.first_name, s.language, s.grade, s.class_id::text,
                              exists(select 1 from consents c where c.student_id=s.id and c.purpose='voice_tutoring'
                                     and c.granted and c.revoked_at is null) as consented
                       from students s where s.active order by s.first_name""")


def create_student(first_name: str, grade: int | None, language: str | None, is_minor: bool,
                   phone: str | None, consent_given_by: str, about: str | None = None) -> str:
    """Sign-up: one profile + the consent captured once (so calls never have to read a recording notice).
    consent_given_by: 'guardian' (minor) or 'student_adult'. All three purposes are recorded with the sign-up."""
    with tx() as conn:
        sid = conn.execute("""insert into students(class_id, first_name, phone_e164, language, grade, is_minor, about)
                              values ((select id from classes order by name limit 1), %s, %s, %s, %s, %s, %s)
                              returning id::text""",
                           (first_name.strip()[:40], phone or None, language or "hi-en", grade, is_minor,
                            (about or "").strip()[:120] or None)).fetchone()["id"]
        for purpose in ("voice_tutoring", "recording", "teacher_sharing"):
            cid = conn.execute("""insert into consents(student_id, given_by, purpose, granted) values (%s,%s,%s,true)
                                  returning id""", (sid, consent_given_by, purpose)).fetchone()["id"]
            if purpose == "voice_tutoring":
                for kind, why in (("call_transcript", "Find what to improve and remember it for the next call"),
                                  ("grading_result", "Track progress over time")):
                    conn.execute("""insert into data_sources(student_id, kind, consent_id, purpose) values (%s,%s,%s,%s)""",
                                 (sid, kind, cid, why))
    return sid


def has_consent(student_id: str, purpose: str = "voice_tutoring") -> bool:
    """Minors need guardian consent; adults may consent themselves."""
    r = one("""select 1 as ok from consents c join students s on s.id=c.student_id
               where c.student_id::text=%s and c.purpose=%s and c.granted and c.revoked_at is null
                 and s.active and (not s.is_minor or c.given_by='guardian')""", (student_id, purpose))
    return r is not None


def audit(actor: str, action: str, entity: str, entity_id: str) -> None:
    run("insert into audit_log(actor, action, entity, entity_id) values (%s,%s,%s,%s)",
        (actor, action, entity, entity_id))


# ---------------------------------------------------------------- curriculum


@lru_cache(maxsize=1)
def misconception_descriptions() -> dict[str, str]:
    return {m["id"]: m["description"] or m["name"] for m in all_misconceptions()}


@lru_cache(maxsize=1)
def misconception_names() -> dict[str, str]:
    return {m["id"]: m["name"] for m in all_misconceptions()}


@lru_cache(maxsize=1)
def topic_names() -> dict[str, str]:
    return {t["id"]: t["name"] for t in all_topics()}


def resolve_topic(topic: str | None) -> str | None:
    """Accepts a topic id or its spoken name ('Linear equations')."""
    if not topic:
        return None
    names = topic_names()
    if topic in names:
        return topic
    low = topic.strip().lower()
    for tid, name in names.items():
        if name.lower() == low or low in name.lower():
            return tid
    return None


def get_question(qid: str) -> dict | None:
    return one("select id, topic_id, text, answer, difficulty, wrong_answer_map from questions where id=%s", (qid,))


def pick_topic(student_id: str) -> str:
    """Recall-first: the topic of the strongest active misconception, else the weakest (decayed) topic."""
    r = one("""select mt.topic_id from student_misconceptions sm
               join misconception_types mt on mt.id=sm.misconception_id
               where sm.student_id::text=%s and sm.strength > 0.4
               order by sm.strength desc, sm.last_seen desc limit 1""", (student_id,))
    if r:
        return r["topic_id"]
    r = one("""select topic_id from mastery where student_id::text=%s
               order by p_known * exp(-extract(epoch from now()-updated_at)/86400.0/greatest(stability_days,0.5))
               limit 1""", (student_id,))
    return r["topic_id"] if r else "alg_linear_eq"


def next_question(session_id: str, student_id: str, topic_id: str, target_mis: list[str]) -> dict | None:
    """Unasked-in-this-session question; prefer ones that probe active misconceptions,
    not solved in the last 2 days, difficulty just above current mastery."""
    p, _, _ = get_mastery(student_id, topic_id)
    return one("""
        select q.id, q.text, q.answer, q.wrong_answer_map, q.topic_id from questions q
        where q.topic_id=%(t)s
          and q.id not in (select question_id from attempts where session_id::text=%(sess)s)
        order by
          (select count(*) from jsonb_each_text(q.wrong_answer_map) w where w.value = any(%(mis)s)) desc,
          exists(select 1 from attempts a join sessions s on s.id=a.session_id
                 where s.student_id::text=%(sid)s and a.question_id=q.id and a.correct
                   and a.created_at > now() - interval '2 days'),
          abs(q.difficulty - (%(p)s + 0.1)), q.id
        limit 1""", {"t": topic_id, "sess": session_id, "sid": student_id, "mis": target_mis or [], "p": p})


# ---------------------------------------------------------------- sessions


def create_session(student_id: str, call_id: str | None, channel: str, topic_id: str | None,
                   mode: str = "maths", goal_id: str | None = None) -> dict:
    """Idempotent per call_id: Bolna may call get_session_context more than once on a call."""
    call_id = (call_id or "").strip() or None      # an unfilled prompt variable arrives as "" -> treat as unknown
    if call_id and call_id.startswith("{"):
        call_id = None
    if call_id:
        r = one("select id::text, student_id::text, topic_id, status from sessions where bolna_call_id=%s",
                (call_id,))
        if r:
            if not r["topic_id"]:
                run("update sessions set topic_id=%s where id::text=%s", (topic_id, r["id"]))
                r["topic_id"] = topic_id
            return {**r, "existing": True}
    r = one("""insert into sessions(student_id, channel, bolna_call_id, topic_id, mode, goal_id)
               values (%s,%s,%s,%s,%s,%s) returning id::text, student_id::text, topic_id, status""",
            (student_id, channel, call_id, topic_id, mode, goal_id))
    return {**r, "existing": False}


def get_session(session_id: str) -> dict | None:
    return one("""select id::text, student_id::text, topic_id, channel, bolna_call_id, status, transcript,
                         started_at, ended_at, mode, goal_id::text from sessions where id::text=%s""", (session_id,))


def session_by_call_id(call_id: str) -> dict | None:
    return one("select id::text, student_id::text, status from sessions where bolna_call_id=%s", (call_id,))


def bind_call(session_id: str, call_id: str) -> None:
    """Attach Bolna's execution id to a session created before/without it (so the post-call webhook finds it)."""
    run("update sessions set bolna_call_id=%s where id::text=%s and bolna_call_id is null", (call_id, session_id))


def open_phone_session(student_id: str, minutes: int = 20, live_only: bool = False) -> dict | None:
    """The student's latest phone session that has no Bolna id yet (created moments ago for this call)."""
    return one(f"""select id::text, student_id::text, status from sessions where student_id::text=%s
                   and channel='phone' and bolna_call_id is null and started_at > now() - make_interval(mins => %s)
                   {"and ended_at is null" if live_only else ""} order by started_at desc limit 1""",
               (student_id, minutes))


def set_session_started(session_id: str, started_at) -> None:
    run("update sessions set started_at=%s where id::text=%s", (started_at, session_id))


def learner_profile(student_id: str) -> dict | None:
    """Guru's running picture of the student (rewritten after every call; latest wins)."""
    r = one("""select content, created_at from memory_facts where student_id::text=%s and kind='note'
               and content->>'type'='profile' and superseded_by is null order by created_at desc limit 1""",
            (student_id,))
    return {**r["content"], "updated_at": r["created_at"]} if r else None


def profile_from_session(session_id: str) -> bool:
    return bool(one("""select 1 as ok from memory_facts where source_session::text=%s and kind='note'
                       and content->>'type'='profile' limit 1""", (session_id,)))


def save_learner_profile(student_id: str, profile: dict, session_id: str | None) -> None:
    with tx() as conn:
        new_id = conn.execute("""insert into memory_facts(student_id, kind, content, confidence, source_session)
                                 values (%s,'note',%s,0.8,%s) returning id::text""",
                              (student_id, json({**profile, "type": "profile"}), session_id)).fetchone()["id"]
        conn.execute("""update memory_facts set superseded_by=%s where student_id::text=%s and kind='note'
                        and content->>'type'='profile' and superseded_by is null and id::text<>%s""",
                     (new_id, student_id, new_id))


def append_transcript(session_id: str, speaker: str, text: str) -> None:
    run("update sessions set transcript = coalesce(transcript || chr(10), '') || %s where id::text=%s",
        (f"{speaker}: {text}", session_id))


def set_transcript(session_id: str, transcript: str) -> None:
    run("update sessions set transcript=%s where id::text=%s", (transcript, session_id))


def get_transcript(session_id: str) -> str:
    s = get_session(session_id)
    if s and s["transcript"]:
        return s["transcript"]
    rows = all_rows("""select q.text, a.student_answer from attempts a join questions q on q.id=a.question_id
                       where a.session_id::text=%s order by a.created_at""", (session_id,))
    return "\n".join(f"Guru: {r['text']}\nStudent: {r['student_answer']}" for r in rows)


def close_session(session_id: str, status: str = "ended") -> bool:
    """Returns False if it was already closed (end_session must be idempotent)."""
    return run("""update sessions set ended_at=now(), status=%s
                  where id::text=%s and ended_at is null""", (status, session_id)) > 0


# ---------------------------------------------------------------- attempts & learning state


def hints_used(session_id: str, qid: str) -> int:
    r = one("""select coalesce(max(hint_level),0) as h from attempts
               where session_id::text=%s and question_id=%s""", (session_id, qid))
    return int(r["h"])


def log_attempt(session_id: str, qid: str, text: str, correct: bool, mis: str | None, hint_level: int) -> None:
    run("""insert into attempts(session_id, question_id, student_answer, correct, misconception_id, hint_level)
           values (%s,%s,%s,%s,%s,%s)""", (session_id, qid, text, correct, mis, hint_level))


def get_mastery(student_id: str, topic_id: str) -> tuple[float, float, object]:
    r = one("select p_known, stability_days, updated_at from mastery where student_id::text=%s and topic_id=%s",
            (student_id, topic_id))
    if not r:
        return 0.3, 3.0, None
    return float(r["p_known"]), float(r["stability_days"]), r["updated_at"]


def set_mastery(student_id: str, topic_id: str, p: float, stability: float) -> None:
    run("""insert into mastery(student_id, topic_id, p_known, stability_days, attempts, updated_at)
           values (%s,%s,%s,%s,1,now())
           on conflict (student_id, topic_id) do update set p_known=excluded.p_known,
             stability_days=excluded.stability_days, attempts=mastery.attempts+1, updated_at=now()""",
        (student_id, topic_id, p, stability))


def get_misconception_strength(student_id: str, mis_id: str) -> float | None:
    r = one("""select strength from student_misconceptions where student_id::text=%s and misconception_id=%s""",
            (student_id, mis_id))
    return float(r["strength"]) if r else None


def set_misconception_strength(student_id: str, mis_id: str, strength: float, is_evidence: bool) -> int:
    """Upsert the strength; is_evidence=True for a new observation of the error (counts + last_seen)."""
    r = one("""insert into student_misconceptions(student_id, misconception_id, strength, evidence_n)
               values (%(s)s, %(m)s, %(v)s, 1)
               on conflict (student_id, misconception_id) do update
                 set strength = %(v)s,
                     evidence_n = student_misconceptions.evidence_n + case when %(e)s then 1 else 0 end,
                     last_seen = case when %(e)s then now() else student_misconceptions.last_seen end
               returning evidence_n""", {"s": student_id, "m": mis_id, "v": strength, "e": is_evidence})
    return int(r["evidence_n"])


def active_misconceptions(student_id: str, topic_id: str | None = None, min_strength: float = 0.3) -> list[dict]:
    return all_rows("""select sm.misconception_id as id, mt.name, sm.strength, mt.topic_id
                       from student_misconceptions sm join misconception_types mt on mt.id=sm.misconception_id
                       where sm.student_id::text=%s and sm.strength > %s
                         and (%s::text is null or mt.topic_id=%s)
                       order by sm.strength desc""", (student_id, min_strength, topic_id, topic_id))


def snapshot(student_id: str, session_id: str | None, kind: str, key: str, value: float) -> None:
    run("""insert into learning_snapshots(student_id, session_id, kind, key, value)
           values (%s,%s,%s,%s,%s)""", (student_id, session_id, kind, key, value))


def log_confidence(session_id: str, topic_id: str, phase: str, value: int) -> None:
    run("insert into confidence_logs(session_id, topic_id, phase, value) values (%s,%s,%s,%s)",
        (session_id, topic_id, phase, value))


def session_confidence(session_id: str) -> dict:
    rows = all_rows("""select phase, value from confidence_logs where session_id::text=%s
                       order by created_at""", (session_id,))
    out: dict = {}
    for r in rows:  # first "before", last "after"
        if r["phase"] == "before":
            out.setdefault("before", r["value"])
        else:
            out["after"] = r["value"]
    return out


def session_stats(session_id: str) -> dict:
    return one("""select count(distinct question_id) as questions,
                         count(*) filter (where correct) as correct_n,
                         count(*) as attempts_n,
                         coalesce(avg(case when correct then 1.0 else 0.0 end), 0)::float as accuracy
                  from attempts where session_id::text=%s""", (session_id,))


def session_misconceptions(session_id: str) -> list[str]:
    return [r["misconception_id"] for r in all_rows(
        """select misconception_id, count(*) from attempts where session_id::text=%s
           and misconception_id is not null group by 1 order by 2 desc""", (session_id,))]


# ---------------------------------------------------------------- safety, memory, plans, summaries


def log_safety_event(student_id: str, session_id: str | None, teacher_notified: bool = True) -> str:
    r = one("""insert into safety_events(student_id, session_id, teacher_notified) values (%s,%s,%s)
               returning id::text""", (student_id, session_id, teacher_notified))
    return r["id"]


def add_fact(student_id: str, kind: str, content: dict, confidence: float, session_id: str | None) -> str:
    """New strategy/goal facts supersede older ones with the same key: never silently delete."""
    key = content.get("id") or content.get("text")
    with tx() as conn:
        new_id = conn.execute("""insert into memory_facts(student_id, kind, content, confidence, source_session)
                                 values (%s,%s,%s,%s,%s) returning id::text""",
                              (student_id, kind, json(content), confidence, session_id)).fetchone()["id"]
        if kind in ("strategy", "goal") and key:
            conn.execute("""update memory_facts set superseded_by=%s
                            where student_id::text=%s and kind=%s and superseded_by is null and id::text<>%s
                              and coalesce(content->>'id', content->>'text')=%s""",
                         (new_id, student_id, kind, new_id, key))
    return new_id


def save_plan(student_id: str, items: list[dict]) -> str:
    with tx() as conn:
        pid = conn.execute("""insert into plans(student_id, valid_from, valid_to)
                              values (%s, current_date + 1, current_date + 3) returning id::text""",
                           (student_id,)).fetchone()["id"]
        for it in items:
            conn.execute("""insert into plan_items(plan_id, day, topic_id, type, n_questions)
                            values (%s,%s,%s,%s,%s)""", (pid, it["day"], it["topic_id"], it["type"], it["n"]))
    return pid


def save_summary(session_id: str, audience: str, language: str, body: str) -> None:
    run("insert into summaries(session_id, audience, language, body) values (%s,%s,%s,%s)",
        (session_id, audience, language, body))


def guardian(student_id: str) -> dict | None:
    return one("select name, phone_e164, preferred_language from guardians where student_id::text=%s limit 1",
               (student_id,))


# ---------------------------------------------------------------- dashboard feeds & privacy


def progress_series(student_id: str) -> dict:
    snaps = all_rows("""select kind, key, value, created_at from learning_snapshots
                        where student_id::text=%s order by created_at""", (student_id,))
    conf = all_rows("""select c.topic_id, c.phase, c.value, c.created_at, c.session_id::text
                       from confidence_logs c join sessions s on s.id=c.session_id
                       where s.student_id::text=%s order by c.created_at""", (student_id,))
    mastery = all_rows("""select topic_id, p_known, stability_days, attempts, updated_at from mastery
                          where student_id::text=%s order by topic_id""", (student_id,))
    mis = all_rows("""select sm.misconception_id as id, mt.name, sm.strength, sm.evidence_n, sm.last_seen
                      from student_misconceptions sm join misconception_types mt on mt.id=sm.misconception_id
                      where sm.student_id::text=%s order by sm.strength desc""", (student_id,))
    points = all_rows("""select s.id::text as session_id, s.started_at, s.topic_id,
                                (select avg(case when a.correct then 1.0 else 0.0 end)::float from attempts a
                                  where a.session_id=s.id) as accuracy,
                                (select value from confidence_logs c where c.session_id=s.id and phase='before'
                                  order by created_at limit 1) as conf_before,
                                (select value from confidence_logs c where c.session_id=s.id and phase='after'
                                  order by created_at desc limit 1) as conf_after
                         from sessions s where s.student_id::text=%s order by s.started_at""", (student_id,))
    return {"snapshots": snaps, "confidence": conf, "mastery": mastery, "misconceptions": mis,
            "session_points": points}


def recent_sessions(student_id: str, limit: int = 10) -> list[dict]:
    return all_rows("""select s.id::text, s.channel, s.topic_id, s.status, s.started_at, s.ended_at,
                              (select json_agg(json_build_object('audience',audience,'language',language,'body',body))
                                 from summaries x where x.session_id=s.id) as summaries
                       from sessions s where s.student_id::text=%s order by s.started_at desc limit %s""",
                    (student_id, limit))


def export_memory(student_id: str) -> dict:
    return {
        "student": one("select id::text, first_name, language, grade from students where id::text=%s",
                       (student_id,)),
        "consents": all_rows("select purpose, given_by, granted, granted_at, revoked_at from consents "
                             "where student_id::text=%s", (student_id,)),
        "memory_facts": all_rows("""select id::text, kind, content, confidence, source_session::text,
                                           source_kind, created_at, superseded_by::text from memory_facts
                                    where student_id::text=%s order by created_at""", (student_id,)),
        **progress_series(student_id),
        "sessions": recent_sessions(student_id, 1000),
        "goals": list_goals(student_id),
        "session_reviews": all_rows("""select session_id::text, mode, summary, strengths, improvements, next_steps,
                                              created_at from session_reviews where student_id::text=%s
                                       order by created_at""", (student_id,)),
        "skill_scores": all_rows("""select skill, score, source, created_at from skill_scores
                                    where student_id::text=%s order by created_at""", (student_id,)),
    }


def delete_student_memory(student_id: str) -> dict:
    """Removes every learning record for the student. Profile + consent rows stay so the guardian can
    still manage consent; anonymised safety_events survive (FK set null)."""
    counts = {}
    with tx() as conn:
        for table in ("memory_facts", "learning_snapshots", "student_misconceptions", "mastery", "plans",
                      "skill_scores", "session_reviews", "sessions", "goals", "live_events"):
            counts[table] = conn.execute(f"delete from {table} where student_id::text=%s",
                                         (student_id,)).rowcount
    return counts


def recent_events(student_id: str | None, after_id: int = 0, limit: int = 100) -> list[dict]:
    return all_rows("""select id, student_id::text, kind, payload, created_at from live_events
                       where (%s::text is null or student_id::text=%s) and id > %s
                       order by id desc limit %s""", (student_id, student_id, after_id, limit))


def teacher_overview() -> dict:
    students = all_rows("""select s.id::text, s.first_name, s.grade,
                                  round(avg(m.p_known)::numeric, 3)::float as avg_mastery,
                                  (select max(started_at) from sessions se where se.student_id=s.id) as last_session
                           from students s left join mastery m on m.student_id=s.id
                           where s.active group by s.id order by s.first_name""")
    summaries = all_rows("""select x.body, x.created_at, s.student_id::text, st.first_name
                            from summaries x join sessions s on s.id=x.session_id
                            join students st on st.id=s.student_id
                            where x.audience='teacher' order by x.created_at desc limit 20""")
    safety_open = all_rows("""select e.id::text, e.student_id::text, st.first_name, e.created_at
                              from safety_events e left join students st on st.id=e.student_id
                              where not e.resolved order by e.created_at desc""")
    return {"students": students, "summaries": summaries, "open_safety_events": safety_open}


# ---------------------------------------------------------------- goals, reviews, skill scores (coach modes)


def active_goal(student_id: str, mode: str) -> dict | None:
    return one("""select id::text, mode, aim, level, minutes_per_day, plan, status, created_at from goals
                  where student_id::text=%s and mode=%s and status='active'
                  order by created_at desc limit 1""", (student_id, mode))


def create_goal(student_id: str, mode: str, aim: str, level: str | None = None) -> str:
    """One active goal per mode: a new aim retires the previous one (kept for history)."""
    with tx() as conn:
        conn.execute("""update goals set status='dropped' where student_id::text=%s and mode=%s and status='active'""",
                     (student_id, mode))
        return conn.execute("""insert into goals(student_id, mode, aim, level) values (%s,%s,%s,%s)
                               returning id::text""", (student_id, mode, aim.strip()[:200], level)).fetchone()["id"]


def set_goal_plan(goal_id: str, plan: dict) -> None:
    run("update goals set plan=%s where id::text=%s", (json(plan), goal_id))


def set_session_goal(session_id: str, goal_id: str) -> None:
    run("update sessions set goal_id=%s where id::text=%s", (goal_id, session_id))


def list_goals(student_id: str) -> list[dict]:
    return all_rows("""select g.id::text, g.mode, g.aim, g.level, g.plan, g.status, g.created_at,
                              (select count(*) from sessions s where s.goal_id=g.id)::int as sessions
                       from goals g where g.student_id::text=%s order by g.status='active' desc, g.created_at desc""",
                    (student_id,))


def save_review(session_id: str, student_id: str, goal_id: str | None, mode: str, r: dict) -> None:
    run("""insert into session_reviews(session_id, student_id, goal_id, mode, summary, strengths, improvements,
                                       next_steps, quiz_correct, quiz_total)
           values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           on conflict (session_id) do update set summary=excluded.summary, strengths=excluded.strengths,
             improvements=excluded.improvements, next_steps=excluded.next_steps,
             quiz_correct=excluded.quiz_correct, quiz_total=excluded.quiz_total""",
        (session_id, student_id, goal_id, mode, r.get("summary"), json(r.get("strengths") or []),
         json(r.get("improvements") or []), json(r.get("next_steps") or []), r.get("quiz_correct"),
         r.get("quiz_total")))


def add_skill_scores(student_id: str, session_id: str | None, goal_id: str | None, scores: dict[str, float],
                     source: str = "llm") -> None:
    for skill, v in scores.items():
        if v is None:
            continue
        run("""insert into skill_scores(student_id, session_id, goal_id, skill, score, source)
               values (%s,%s,%s,%s,%s,%s)""",
            (student_id, session_id, goal_id, skill, max(0.0, min(10.0, float(v))), source))


def last_review(student_id: str, mode: str) -> dict | None:
    return one("""select r.summary, r.improvements, r.next_steps, r.created_at from session_reviews r
                  where r.student_id::text=%s and r.mode=%s order by r.created_at desc limit 1""", (student_id, mode))


def session_review(session_id: str) -> dict | None:
    return one("""select summary, strengths, improvements, next_steps, quiz_correct, quiz_total, mode, created_at
                  from session_reviews where session_id::text=%s""", (session_id,))


def language_known(student_id: str) -> bool:
    """True once the student has told Guru which language they want (so it is not asked every call)."""
    return one("""select 1 as ok from memory_facts where student_id::text=%s and kind='note'
                  and content->>'type'='language' limit 1""", (student_id,)) is not None


def remember_language(student_id: str, lang: str, session_id: str | None) -> None:
    run("update students set language=%s where id::text=%s", (lang, student_id))
    add_fact(student_id, "note", {"type": "language", "id": "language", "value": lang}, 1.0, session_id)


def recent_reviews(student_id: str, limit: int = 5) -> list[dict]:
    return all_rows("""select r.mode, r.summary, r.improvements, r.strengths, r.created_at
                       from session_reviews r where r.student_id::text=%s
                       order by r.created_at desc limit %s""", (student_id, limit))


def recent_resources(student_id: str, limit: int = 6) -> list[dict]:
    return all_rows("""select content->>'kind' as kind, content->>'title' as title, content->>'by' as by,
                              content->>'why' as why, created_at, source_session::text as session_id
                       from memory_facts where student_id::text=%s and kind='note' and content->>'type'='resource'
                       order by created_at desc limit %s""", (student_id, limit))


def skill_trend(student_id: str, days: int = 30) -> str | None:
    """Plain words: which skills went up or down between the first and latest score in the window."""
    rows = all_rows("""select skill, score from skill_scores where student_id::text=%s
                       and created_at > now() - make_interval(days => %s) order by created_at""", (student_id, days))
    first: dict[str, float] = {}
    last: dict[str, float] = {}
    for r in rows:
        first.setdefault(r["skill"], r["score"])
        last[r["skill"]] = r["score"]
    up = [k.replace(".", " ") for k in last if last[k] - first[k] >= 0.5]
    down = [k.replace(".", " ") for k in last if first[k] - last[k] >= 0.5]
    if not up and not down:
        return None
    return "; ".join(([f"improving: {', '.join(up)}"] if up else []) + ([f"slipping: {', '.join(down)}"] if down else []))


def journal(student_id: str, limit: int = 14) -> list[dict]:
    """Day-by-day learning journal: each finished call with its review and the resources suggested in it."""
    return all_rows("""
        select s.id::text as session_id, s.started_at, s.channel, s.mode, s.topic_id,
               r.summary, r.strengths, r.improvements, r.next_steps,
               coalesce((select json_agg(json_build_object('kind', f.content->>'kind', 'title', f.content->>'title',
                                                           'by', f.content->>'by', 'why', f.content->>'why'))
                         from memory_facts f where f.source_session=s.id and f.kind='note'
                           and f.content->>'type'='resource'), '[]') as resources
        from sessions s left join session_reviews r on r.session_id=s.id
        where s.student_id::text=%s and s.ended_at is not null
        order by s.started_at desc limit %s""", (student_id, limit))


def recent_skill_averages(student_id: str, prefix: str, days: int = 30) -> dict[str, float]:
    rows = all_rows("""select skill, avg(score)::float as v from skill_scores
                       where student_id::text=%s and skill like %s and created_at > now() - make_interval(days => %s)
                       group by skill""", (student_id, prefix + "%", days))
    return {r["skill"]: round(r["v"], 1) for r in rows}


def skill_series(student_id: str, period: str) -> list[dict]:
    """Average score per skill per day / week / month bucket (period validated by the caller)."""
    assert period in ("day", "week", "month")
    span = {"day": "14 days", "week": "12 weeks", "month": "12 months"}[period]
    return all_rows(f"""select date_trunc('{period}', created_at) as bucket, skill,
                               round(avg(score)::numeric, 2)::float as score, count(*)::int as n
                        from skill_scores where student_id::text=%s and created_at > now() - interval '{span}'
                        group by 1, 2 order by 1, 2""", (student_id,))


# ---------------------------------------------------------------- dashboard page payloads


def close_stale_sessions() -> int:
    """Sessions still "active" long after they could have ended (phone calls are capped at 10 minutes by Bolna; browser
    calls get an hour and a half) are closed: their end webhook never arrived, e.g. an unanswered call."""
    return run("""update sessions set status='ended',
                         ended_at = least(now(), started_at + case when channel='phone' then interval '20 minutes'
                                                                   else interval '90 minutes' end)
                  where ended_at is null
                    and started_at < now() - case when channel='phone' then interval '20 minutes'
                                                  else interval '90 minutes' end""")


def latest_session(student_id: str | None = None) -> dict | None:
    close_stale_sessions()      # otherwise an old never-closed call is shown instead of the latest real one
    return one("""select s.id::text, s.student_id::text, s.status, s.channel, s.started_at, st.first_name
                  from sessions s join students st on st.id=s.student_id
                  where (%s::text is null or s.student_id::text=%s)
                  order by (s.ended_at is null) desc, s.started_at desc limit 1""", (student_id, student_id))


def session_feed(session_id: str) -> dict | None:
    s = one("""select s.id::text, s.student_id::text, s.topic_id, s.channel, s.status, s.started_at, s.ended_at,
                      s.transcript, st.first_name, s.mode
               from sessions s join students st on st.id=s.student_id where s.id::text=%s""", (session_id,))
    if not s:
        return None
    attempts = all_rows("""select a.question_id, q.text as question, a.student_answer, a.correct,
                                  a.misconception_id, mt.name as misconception_name, a.hint_level, a.created_at
                           from attempts a join questions q on q.id=a.question_id
                           left join misconception_types mt on mt.id=a.misconception_id
                           where a.session_id::text=%s order by a.created_at""", (session_id,))
    lines = []
    for raw in (s.pop("transcript") or "").splitlines():
        who, sep, text = raw.partition(":")
        if not sep or not text.strip():
            continue
        role = who.strip().lower()
        # older phone transcripts are stored as Bolna sent them ("assistant:" / "user:")
        guru = role in ("guru", "assistant", "agent", "bot")
        name = "Guru" if guru else (s["first_name"] if role in ("user", "human", "student") else who.strip())
        lines.append({"speaker": "guru" if guru else "student", "name": name, "text": text.strip()})
    if not lines:  # Bolna sends the full transcript only after the call: build it from attempts meanwhile
        for a in attempts:
            lines.append({"speaker": "guru", "name": "Guru", "text": a["question"]})
            lines.append({"speaker": "student", "name": s["first_name"], "text": a["student_answer"]})
    plan = all_rows("""select pi.day, pi.topic_id, t.name as topic, pi.type, pi.n_questions from plans p
                       join plan_items pi on pi.plan_id=p.id join topics t on t.id=pi.topic_id
                       where p.student_id::text=%s and p.created_at >= %s order by pi.day""",
                    (s["student_id"], s["started_at"]))
    return {**s, "topic": topic_names().get(s["topic_id"]), "lines": lines, "attempts": attempts,
            "confidence": session_confidence(session_id), "stats": session_stats(session_id), "plan": plan,
            "arc": session_arc(s, attempts), "review": session_review(session_id)}


def _snap(student_id: str, kind: str, key: str, session_id: str, started_at, before: bool) -> float | None:
    if before:
        r = one("""select value from learning_snapshots where student_id::text=%s and kind=%s and key=%s
                   and created_at < %s and (session_id is null or session_id::text<>%s)
                   order by created_at desc limit 1""", (student_id, kind, key, started_at, session_id))
    else:
        r = one("""select value from learning_snapshots where session_id::text=%s and kind=%s and key=%s
                   order by created_at desc, id desc limit 1""", (session_id, kind, key))
    return round(float(r["value"]), 3) if r else None


def session_arc(s: dict, attempts: list[dict]) -> dict:
    """Before/after for the end-of-call card: mastery of the session topic, the main misconception, confidence."""
    sid, stu, topic = s["id"], s["student_id"], s["topic_id"]
    tagged = [a["misconception_id"] for a in attempts if a["misconception_id"]]
    mis = max(set(tagged), key=tagged.count) if tagged else None
    return {"topic_id": topic,
            "mastery_before": _snap(stu, "mastery", topic, sid, s["started_at"], True) if topic else None,
            "mastery_after": _snap(stu, "mastery", topic, sid, None, False) if topic else None,
            "misconception": mis, "misconception_name": misconception_names().get(mis) if mis else None,
            "mis_before": _snap(stu, "misconception", mis, sid, s["started_at"], True) if mis else None,
            "mis_after": _snap(stu, "misconception", mis, sid, None, False) if mis else None,
            **{f"conf_{k}": v for k, v in session_confidence(sid).items()}}


def student_overview(student_id: str) -> dict | None:
    import mastery as m
    st = one("select id::text, first_name, language, grade from students where id::text=%s", (student_id,))
    if not st:
        return None
    rows = all_rows("""select ms.topic_id, t.name, ms.p_known, ms.stability_days, ms.attempts, ms.updated_at
                       from mastery ms join topics t on t.id=ms.topic_id where ms.student_id::text=%s
                       order by t.name""", (student_id,))
    topics = []
    for r in rows:
        p = float(r["p_known"])
        topics.append({**r, "p_known": round(p, 3),
                       "p_now": round(m.decayed(p, r["updated_at"], float(r["stability_days"])), 3),
                       "next_review_days": round(m.next_review_days(p, float(r["stability_days"])), 1)})
    facts = all_rows("""select f.id::text, f.kind, f.content, f.confidence, f.created_at, f.source_session::text,
                               s.started_at as source_started_at
                        from memory_facts f left join sessions s on s.id=f.source_session
                        where f.student_id::text=%s and f.superseded_by is null order by f.created_at desc""",
                     (student_id,))
    return {**st, "consented": has_consent(student_id), "topics": topics, "goals": list_goals(student_id),
            "last_reviews": all_rows("""select distinct on (mode) mode, summary, improvements, next_steps, created_at
                                         from session_reviews where student_id::text=%s
                                         order by mode, created_at desc""", (student_id,)),
            "misconceptions": progress_series(student_id)["misconceptions"],
            "focus_topic": pick_topic(student_id), "memory": facts, "sessions": recent_sessions(student_id, 20),
            "snapshots": all_rows("""select kind, key, value, created_at from learning_snapshots
                                     where student_id::text=%s order by created_at""", (student_id,))}


def parent_view(student_id: str) -> dict | None:
    st = one("select id::text, first_name from students where id::text=%s", (student_id,))
    if not st:
        return None
    latest = {r["audience"] + "_" + r["language"]: r["body"] for r in all_rows(
        """select distinct on (x.audience, x.language) x.audience, x.language, x.body
           from summaries x join sessions s on s.id=x.session_id where s.student_id::text=%s
           order by x.audience, x.language, x.created_at desc""", (student_id,))}
    sessions = all_rows("""select started_at from sessions where student_id::text=%s and ended_at is not null
                           order by started_at desc limit 7""", (student_id,))
    plan = all_rows("""select pi.day, t.name as topic, pi.type, pi.done from plans p
                       join plan_items pi on pi.plan_id=p.id join topics t on t.id=pi.topic_id
                       where p.id=(select id from plans where student_id::text=%s order by created_at desc limit 1)
                       order by pi.day""", (student_id,))
    return {**st, "parent_hi": latest.get("parent_hi"), "parent_en": latest.get("parent_en"),
            "sessions_this_week": len(sessions), "plan": plan, "guardian": guardian(student_id)}


def privacy_view(student_id: str) -> dict | None:
    st = one("select id::text, first_name, is_minor from students where id::text=%s", (student_id,))
    if not st:
        return None
    return {**st,
            "consents": all_rows("""select purpose, given_by, granted, granted_at, revoked_at from consents
                                    where student_id::text=%s order by purpose""", (student_id,)),
            "data_sources": all_rows("""select kind, purpose, created_at from data_sources
                                        where student_id::text=%s order by kind""", (student_id,)),
            "audit": all_rows("""select actor, action, entity, created_at from audit_log
                                 where entity_id=%s order by created_at desc limit 50""", (student_id,)),
            "counts": one("""select (select count(*) from memory_facts where student_id::text=%(s)s) as memory_facts,
                                    (select count(*) from sessions where student_id::text=%(s)s) as sessions,
                                    (select count(*) from attempts a join sessions x on x.id=a.session_id
                                      where x.student_id::text=%(s)s) as attempts""", {"s": student_id})}


def class_heatmap() -> dict:
    cells = all_rows("""select sm.student_id::text, sm.misconception_id, sm.strength from student_misconceptions sm
                        join students s on s.id=sm.student_id where s.active""")
    return {"misconceptions": [{"id": k, "name": v} for k, v in misconception_names().items()],
            "students": all_rows("select id::text, first_name from students where active order by first_name"),
            "cells": cells}


def latest_eval() -> dict | None:
    return one("""select id::text, created_at, n_students, tag_accuracy, false_positive_rate, avg_hints, notes,
                         report from eval_runs order by created_at desc limit 1""")


def pilot_cards() -> list[dict]:
    """Before/after per student from their first and latest sessions (real sessions only)."""
    return all_rows("""
        with s as (select x.id, x.student_id, x.started_at,
                          row_number() over (partition by x.student_id order by x.started_at) as first_n,
                          row_number() over (partition by x.student_id order by x.started_at desc) as last_n
                   from sessions x where x.channel in ('phone','web') and x.ended_at is not null
                     and coalesce(x.bolna_call_id, '') not like 'seed-%%')   -- seeded demo data is never "real"
        select st.id::text as student_id, st.first_name,
               (select coalesce(avg(case when a.correct then 1.0 else 0.0 end),0)::float from attempts a
                 where a.session_id=f.id) as acc_before,
               (select coalesce(avg(case when a.correct then 1.0 else 0.0 end),0)::float from attempts a
                 where a.session_id=l.id) as acc_after,
               (select value from confidence_logs c where c.session_id=f.id and phase='before' limit 1) as conf_before,
               (select value from confidence_logs c where c.session_id=l.id and phase='after'
                 order by created_at desc limit 1) as conf_after,
               (select count(*) from s s2 where s2.student_id=st.id)::int as sessions
        from students st join s f on f.student_id=st.id and f.first_n=1
        join s l on l.student_id=st.id and l.last_n=1 order by st.first_name""")


# ---------------------------------------------------------------- health


def ping() -> bool:
    return one("select 1 as ok")["ok"] == 1
