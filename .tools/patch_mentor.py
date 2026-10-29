from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


# ---------- db: about field
edit("api/db.py", [
    ('''    return one("""select id::text, first_name, language, grade, phone_e164, is_minor, active, class_id::text,
                         call_window_start, call_window_end
                  from students where id::text=%s""", (student_id,))''',
     '''    return one("""select id::text, first_name, language, grade, about, phone_e164, is_minor, active,
                         class_id::text, call_window_start, call_window_end
                  from students where id::text=%s""", (student_id,))'''),
    ('''def create_student(first_name: str, grade: int | None, language: str | None, is_minor: bool,
                   phone: str | None, consent_given_by: str) -> str:''',
     '''def create_student(first_name: str, grade: int | None, language: str | None, is_minor: bool,
                   phone: str | None, consent_given_by: str, about: str | None = None) -> str:'''),
    ('''        sid = conn.execute("""insert into students(class_id, first_name, phone_e164, language, grade, is_minor)
                              values ((select id from classes order by name limit 1), %s, %s, %s, %s, %s)
                              returning id::text""",
                           (first_name.strip()[:40], phone or None, language or "hi-en", grade, is_minor)).fetchone()["id"]''',
     '''        sid = conn.execute("""insert into students(class_id, first_name, phone_e164, language, grade, is_minor, about)
                              values ((select id from classes order by name limit 1), %s, %s, %s, %s, %s, %s)
                              returning id::text""",
                           (first_name.strip()[:40], phone or None, language or "hi-en", grade, is_minor,
                            (about or "").strip()[:120] or None)).fetchone()["id"]'''),
])

edit("api/main.py", [
    ('''    grade: int | None = Field(default=None, ge=1, le=12)
    language: str | None = None        # hi | en | hi-en | None (Guru asks on the first call)''',
     '''    grade: int | None = Field(default=None, ge=1, le=12)   # only for school students; Guru is for anyone
    about: str | None = Field(default=None, max_length=120)  # "college student", "working in sales", "job seeker"…
    language: str | None = None        # hi | en | hi-en | None (Guru asks on the first call)'''),
    ('''    sid = db.create_student(b.first_name, b.grade, b.language, b.is_minor, phone,
                            "guardian" if b.is_minor else "student_adult")''',
     '''    sid = db.create_student(b.first_name, b.grade, b.language, b.is_minor, phone,
                            "guardian" if b.is_minor else "student_adult", b.about)'''),
])

# ---------- coach: "who" instead of "class ?", mentor framing, challenges in the profile
edit("api/coach.py", [
    ('''    lines = [f"STUDENT: {student['first_name']}, class {student.get('grade') or '?'}, "''',
     '''    lines = [f"PERSON: {who(student)}, "'''),
    ('''    lines = [f"STUDENT: {spoken_name(student['first_name'])}, class {student.get('grade') or '?'}."]''',
     '''    lines = [f"PERSON: {who(student)}."]'''),
    ('''    plan = chat("You design short, realistic learning plans for school students in India. Be specific and encouraging.",
                [{"role": "user", "content": f"Student: class {st.get('grade')}, about 10 minutes of voice practice a day.\\n"''',
     '''    plan = chat("You are a mentor designing short, realistic improvement plans for one person in India (a school or "
                "college student, a working professional or a job seeker). Be specific, practical and encouraging.",
                [{"role": "user", "content": f"Person: {who({**st, 'id': student_id})}, about 10 minutes of voice "
                                             "mentoring a day.\\n"'''),
    ('''    out = chat("You evaluate a short voice coaching session with a school student. Judge only from the transcript "''',
     '''    out = chat("You evaluate a short voice mentoring session with one learner (any age or background). Judge only "
               "from the transcript "'''),
    ('''               [{"role": "user", "content": f"Mode: {MODE_NAME[mode]}. Student: {st['first_name']}, class {st.get('grade')}.\\n"''',
     '''               [{"role": "user", "content": f"Mode: {MODE_NAME[mode]}. Person: {who({**st, 'id': sid})}.\\n"'''),
    ('''               [{"role": "user", "content": f"Student: {st.get('first_name')}, class {st.get('grade') or '?'}, "''',
     '''               [{"role": "user", "content": f"Person: {who({**st, 'id': sid})}, "'''),
    ('''    out = chat("You are a learning coach writing a short progress note for a school student. Use only the data given. "''',
     '''    out = chat("You are a mentor writing a short progress note for one learner. Use only the data given. "'''),
    ('''MODE_NAME = {"coach": "Coaching",''', '''MODE_NAME = {"coach": "Mentoring",'''),
    # profile: problems with root cause / next action / status, and what was tried with the result
    ('''        "topics_covered": {**_strs,''',
     '''        "challenges": {**_strs, "description": "open problems the person brought (studies, career, work, confidence, "
                                               "habits...), each as: problem; likely root cause; next small action; "
                                               "status new / improving / solved. Keep older ones and update status."},
        "solutions_tried": {**_strs, "description": "what was tried so far and what happened, e.g. 'Pomodoro 25 min: "
                                                    "helped focus 2 of 3 days'. Keep older ones."},
        "topics_covered": {**_strs,'''),
    ('''                 "goal_in_their_words", "topics_covered", "next_topics", "direction", "next_call_plan",''',
     '''                 "goal_in_their_words", "challenges", "solutions_tried", "topics_covered", "next_topics",
                 "direction", "next_call_plan",'''),
    ('''PROFILE_LABELS = [("about", "About them"), ("motivation", "What motivates them"),''',
     '''PROFILE_LABELS = [("about", "About them"), ("challenges", "Open problems (problem; root cause; next action; status)"),
                  ("solutions_tried", "Tried so far and result"), ("motivation", "What motivates them"),'''),
    ('''    out = chat("You keep a learning coach's private notes about one student, used to personalise the next call. "''',
     '''    out = chat("You keep a mentor's private notes about one person (a student, college learner, working "
               "professional or job seeker), used to personalise the next call. Track their real problems like a good "
               "counsellor-mentor: the problem, its likely root cause, what they tried and whether it worked, and the "
               "next small step. "'''),
])

# who(): one line describing the person, used everywhere instead of "class ?"
edit("api/coach.py", [
    ('''def _unquote(text: str) -> str:''',
     '''def who(student: dict) -> str:
    """'Ashu, college student' / 'Riya, class 9' / 'Piyush': no assumption that everyone is in school."""
    parts = [spoken_name(student.get("first_name")) or "Unknown"]
    if student.get("about"):
        parts.append(str(student["about"]))
    elif student.get("grade"):
        parts.append(f"class {student['grade']}")
    return ", ".join(parts)


def _unquote(text: str) -> str:'''),
])

# mentor-style openings
edit("api/coach.py", [
    ('''ASK_IMPROVE = {"hi": "आज आप किस चीज़ में बेहतर होना चाहेंगे?", "en": "What would you like to get better at today?",
               "hi-en": "Aaj kis cheez mein better hona chahoge?"}''',
     '''ASK_IMPROVE = {"hi": "आज क्या चल रहा है, किस बात में मदद करूँ?", "en": "What's on your mind today, what can I help you with?",
               "hi-en": "Aaj kya chal raha hai, kis baat mein help karun?"}'''),
])
print("ok")
