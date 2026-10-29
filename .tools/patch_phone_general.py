"""One-off patch: phone (Bolna) calls become memory-led open coaching by default."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        assert a in s, f"{rel} MISSING: {a[:80]}"
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")


patch("api/phone.py", [
    # balanced, student-led options: goals and open improvement points first, maths only if a mistake is open
    ('''    options = []
    if mis:
        options.append(f"Maths: fix '{names[mis[0]['id']]}' in {db.topic_names()[mis[0]['topic_id']]}")
    options += [f"{coach.MODE_NAME[g['mode']]}: {g['aim']}" for g in goals]
    if not any(g["mode"] == "english" for g in goals):
        options.append("English speaking practice")
    options.append("Any topic you are curious about")
''', '''    options = [f"Your goal: {g['aim']}" for g in goals[:2]]
    if last and last["improvements"]:
        options.append(f"Continue: {last['improvements'][0]}")
    if mis:
        options.append(f"Maths: fix '{names[mis[0]['id']]}'")
    options += ["English speaking practice", "Anything you want to learn or improve"]
'''),
    ('''        "preferred_language": LANG_NAMES.get(st["language"], "Hinglish"),''',
     '''        # ask the language only on the first call; afterwards use the saved choice
        "language": LANG_NAMES.get(st["language"], "Hinglish") if db.language_known(student_id) else "unknown: ask",
        "recent_days": [{"when": _ago(r["created_at"]), "practised": coach.MODE_NAME.get(r["mode"], r["mode"]),
                         "summary": r["summary"], "still_to_improve": (r["improvements"] or [])[:2]}
                        for r in db.recent_reviews(student_id, 3)],
        "already_suggested": [r["title"] for r in db.recent_resources(student_id, 6)],'''),
    ('''    db.run("update students set language=%s where id::text=%s", (lang, sess["student_id"]))
    return {"ok": True, "language": LANG_NAMES[lang],''', '''    db.remember_language(sess["student_id"], lang, session_id)
    return {"ok": True, "language": LANG_NAMES[lang],'''),
    ('''    mode = {"math": "maths", "mathematics": "maths", "english speaking": "english", "any": "topic",
            "general": "topic"}.get((mode or "").strip().lower(), (mode or "").strip().lower())
    if mode not in ("maths", "english", "topic"):
        raise ServiceError(422, "mode must be maths, english or topic")
    sid = sess["student_id"]
    goal = db.active_goal(sid, mode)''', '''    mode = {"math": "maths", "mathematics": "maths", "english speaking": "english", "any": "coach",
            "general": "coach", "open": "coach", "coaching": "coach"}.get((mode or "").strip().lower(),
                                                                        (mode or "").strip().lower())
    if mode not in ("coach", "maths", "english", "topic"):
        raise ServiceError(422, "mode must be coach, maths, english or topic")
    sid = sess["student_id"]
    goal = db.active_goal(sid, coach.goal_mode(mode))'''),
    ('''    if mode == "english":
        notes["instruction"] = (''', '''    if mode == "coach":
        notes["instruction"] = (
            "Open coaching on what the student chose. Diagnose first (ask what exactly is hard or have them try one "
            "small example), then teach one idea at a time with an everyday example and let them try. Explain their "
            "mistake plainly: what it is, why it happens, how to fix it. When it truly helps (once, at most twice), "
            "suggest ONE real book (exact title and author), a correctly attributed quote, or a proven method "
            "(active recall, spaced repetition, Feynman technique, Pomodoro, error notebook, shadowing for spoken "
            "English) and call save_suggestion with it. Never invent a book or quote.")
    elif mode == "english":
        notes["instruction"] = ('''),
])

patch("api/phone.py", [('''def set_goal(session_id: str, aim: str) -> dict:''', '''def save_suggestion(session_id: str, kind: str, title: str, by: str | None, why: str) -> dict:
    """A book / quote / method Guru suggested on the phone: stored with the call, shown on the platform."""
    sess = db.get_session(session_id)
    if not sess:
        raise ServiceError(404, "unknown session_id")
    kind = kind if kind in ("book", "quote", "method") else "method"
    coach.save_resource(sess["student_id"], session_id, {"kind": kind, "title": title, "by": by, "why": why})
    return {"ok": True}


def set_goal(session_id: str, aim: str) -> dict:''')])

patch("api/main.py", [('''@app.post("/bolna/set_goal", dependencies=[Depends(verify_webhook)])''', '''class SuggestionIn(BaseModel):
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
    return {"days": db.journal(sid), "resources": db.recent_resources(sid, 12)}


@app.post("/bolna/set_goal", dependencies=[Depends(verify_webhook)])''')])

patch("api/bolna.py", [
    ('''        _tool("choose_topic", "The student chose what to practise. mode: maths, english or topic. Returns the first "
              "question (maths) or coaching notes (english/topic).",
              {"session_id": s, "mode": {"type": "string", "enum": ["maths", "english", "topic"]}, "topic": s},''',
     '''        _tool("choose_topic", "The student chose what to work on. mode: coach (anything: subjects, exams, skills, "
              "goals, study habits; the default), maths (misconception drills) or english (spoken English). "
              "Returns the first question (maths) or coaching notes.",
              {"session_id": s, "mode": {"type": "string", "enum": ["coach", "maths", "english"]}, "topic": s},'''),
    ('''        _tool("set_goal",''', '''        _tool("save_suggestion", "Save a real book, a correctly attributed quote, or a proven study method you just "
              "suggested, so the student can see it on their platform.",
              {"session_id": s, "kind": {"type": "string", "enum": ["book", "quote", "method"]}, "title": s, "by": s,
               "why": s}, ["session_id", "kind", "title", "why"], "Theek hai."),
        _tool("set_goal",'''),
])
print("phone/main/bolna patched")
