"""One-off patch: goals / skills / coach-feedback endpoints, review + mode in session feed, maths reviews."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch(rel: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        assert a in s, f"{rel} MISSING: {a[:80]}"
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")


patch("api/main.py", [(
    '''@app.get("/teacher/overview", dependencies=[Depends(verify_admin)])''',
    '''class GoalIn(BaseModel):
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


@app.get("/teacher/overview", dependencies=[Depends(verify_admin)])''')])

patch("api/db.py", [
    ('''    s = one("""select s.id::text, s.student_id::text, s.topic_id, s.channel, s.status, s.started_at, s.ended_at,
                      s.transcript, st.first_name''',
     '''    s = one("""select s.id::text, s.student_id::text, s.topic_id, s.channel, s.status, s.started_at, s.ended_at,
                      s.transcript, st.first_name, s.mode''')
    , ('''            "arc": session_arc(s, attempts)}''',
       '''            "arc": session_arc(s, attempts), "review": session_review(session_id)}'''),
    ('''    return {**st, "consented": has_consent(student_id), "topics": topics,''',
     '''    return {**st, "consented": has_consent(student_id), "topics": topics, "goals": list_goals(student_id),
            "last_reviews": all_rows("""select distinct on (mode) mode, summary, improvements, next_steps, created_at
                                         from session_reviews where student_id::text=%s
                                         order by mode, created_at desc""", (student_id,)),''')])

# Maths sessions: same review + skill-score trail as the coach modes, built from what was measured.
patch("api/service.py", [(
    '''        summaries.create_all(student_id, session_id)
''', '''        summaries.create_all(student_id, session_id)
        _maths_review(student_id, session_id)
''')])
s = (ROOT / "api/service.py").read_text(encoding="utf-8")
s = s.replace('''def end_session(session_id: str, safety_flag: bool = False, wait: bool = False) -> dict:''', '''def _maths_review(student_id: str, session_id: str) -> None:
    sess = db.get_session(session_id)
    if not sess or not sess["topic_id"]:
        return
    stats = db.session_stats(session_id)
    names = db.misconception_names()
    mis = db.session_misconceptions(session_id)
    p, _, _ = db.get_mastery(student_id, sess["topic_id"])
    topic = db.topic_names()[sess["topic_id"]]
    db.save_review(session_id, student_id, sess.get("goal_id"), "maths", {
        "summary": f"Practised {topic}: {int(stats['correct_n'] or 0)} of {int(stats['questions'] or 0)} questions solved.",
        "strengths": [f"Solved {int(stats['correct_n'])} question(s)"] if stats["correct_n"] else [],
        "improvements": [f"Fix: {names[m]}" for m in mis[:3]],
        "next_steps": [f"Review {topic} tomorrow"],
        "quiz_correct": int(stats["correct_n"] or 0), "quiz_total": int(stats["questions"] or 0)})
    scores = {"maths.mastery": round(p * 10, 2)}
    conf = db.session_confidence(session_id)
    db.add_skill_scores(student_id, session_id, sess.get("goal_id"), scores, "model")
    if conf.get("after"):
        db.add_skill_scores(student_id, session_id, sess.get("goal_id"), {"maths.confidence": conf["after"]},
                            "self_report")


def end_session(session_id: str, safety_flag: bool = False, wait: bool = False) -> dict:''')
(ROOT / "api/service.py").write_text(s, encoding="utf-8")
print("patched")
