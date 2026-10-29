# ---------------------------------------------------------------- learner profile (cross-call memory)

PROFILE_LABELS = [("about", "About them"), ("motivation", "What motivates them"),
                  ("confidence_pattern", "Confidence"), ("recurring_mistakes", "Recurring mistakes"),
                  ("what_works", "What works with them"), ("watch_outs", "Be careful about"),
                  ("direction", "Direction (next steps)"), ("next_call_plan", "Plan for the next call")]

_strs = {"type": "array", "items": {"type": "string"}}
PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "about": {"type": "string", "description": "facts the student shared about themselves: interests, aims, "
                                                     "situation (only what they said; no personal data like address)"},
        "motivation": {"type": "string", "description": "what seems to drive them, in their own words where possible"},
        "confidence_pattern": {"type": "string", "description": "what they SAID about their confidence and how it "
                                                                "changed across calls (never guessed from voice)"},
        "recurring_mistakes": _strs,
        "what_works": {**_strs, "description": "teaching moves that worked with THIS student, plus evidence-based "
                                               "methods to use next (retrieval practice, spaced repetition, worked "
                                               "examples, small wins for self-efficacy, implementation intentions)"},
        "watch_outs": {**_strs, "description": "e.g. goes off-topic, gets discouraged by long explanations; "
                                               "include how to handle it kindly"},
        "direction": {"type": "string", "description": "where they are heading and the next 1-2 concrete steps"},
        "next_call_plan": {"type": "string", "description": "what to check or practise at the start of the next call"},
        "next_call_opener": {"type": "string", "description": "ONE short spoken sentence for the next call, in the "
                             "student's language (Hinglish in Latin script unless they chose Hindi or English), "
                             "that links to this call and ends with a question, e.g. 'Pichli baar aapne public "
                             "speaking ke darr ki baat ki thi, kya aapne mirror practice try ki?'"},
    },
    "required": ["about", "motivation", "confidence_pattern", "recurring_mistakes", "what_works", "watch_outs",
                 "direction", "next_call_plan", "next_call_opener"],
    "additionalProperties": False,
}


def update_profile(session_id: str) -> dict | None:
    """After every call: merge what this call showed into Guru's running notes about the student.
    These notes open the next call (web or phone), so every call builds on the last one."""
    sess = db.get_session(session_id)
    if not sess or not sess.get("transcript"):
        return None
    sid = sess["student_id"]
    st = db.student(sid) or {}
    prev = db.learner_profile(sid)
    review = db.session_review(session_id) or {}
    prev_txt = "\n".join(f"{k}: {v}" for k, v in (prev or {}).items() if k not in ("type", "updated_at")) or "none yet"
    out = chat("You keep a learning coach's private notes about one student, used to personalise the next call. "
               "Merge the previous notes with what this call shows: keep what is still true, update what changed, "
               "drop what is stale. Be specific and brief (each field under 40 words). Ground advice in learning "
               "science (retrieval practice, spacing, worked examples, growth mindset, self-efficacy through small "
               "wins, implementation intentions) and in what actually worked for this student. Never guess mood, "
               "health, personality or family matters; confidence is only what the student said. If the call was "
               "off-topic or rude, note kindly how to steer them back to learning, without judging them.",
               [{"role": "user", "content": f"Student: {st.get('first_name')}, class {st.get('grade') or '?'}, "
                                            f"language: {LANG_NAME.get(st.get('language'), 'unknown')}.\n"
                                            f"PREVIOUS NOTES:\n{prev_txt}\n\n"
                                            f"THIS CALL'S REVIEW: {review.get('summary') or 'none'} "
                                            f"Improve: {'; '.join(review.get('improvements') or [])}\n\n"
                                            f"TRANSCRIPT ({MODE_NAME.get(sess['mode'], sess['mode'])}):\n"
                                            f"{sess['transcript'][:10000]}"}],
               PROFILE_SCHEMA, max_tokens=3000, timeout=90)
    if not isinstance(out, dict):
        return None
    db.save_learner_profile(sid, out, session_id)
    try:
        graph.q("MATCH (s:Student {id:$sid}) SET s.direction=$d, s.motivation=$m",
                {"sid": sid, "d": out.get("direction") or "", "m": out.get("motivation") or ""})
    except Exception:
        pass
    events.emit(sid, "profile_updated", {"session_id": session_id})
    return out


GREET = {"hi": "Namaste {n}! Main Guru, aapka AI coach.", "en": "Hi {n}! It's Guru, your AI coach.",
         "hi-en": "Namaste {n}! Guru bol raha hoon, aapka AI coach."}
ASK_IMPROVE = {"hi": "Aaj aap kis cheez mein behtar hona chahenge?", "en": "What would you like to get better at today?",
               "hi-en": "Aaj kis cheez mein better hona chahoge?"}
WELCOME_BACK = {"hi": "Aapse phir baat karke accha laga.", "en": "Good to talk again.",
                "hi-en": "Phir se baat karke accha laga."}


def opening_line(student: dict) -> str:
    """The first thing Guru says on a phone call (Bolna welcome message): greeting + language question for a new
    student, otherwise greeting + one sentence linking to the last call + what to improve today. No LLM: instant."""
    sid, n = student["id"], student["first_name"]
    if not db.language_known(sid):
        return (f"Namaste {n}! Main Guru hoon, aapka AI coach. Aap Hindi, English, ya dono mix mein "
                "baat karna pasand karoge?")
    lang = student.get("language") if student.get("language") in GREET else "hi-en"
    hook = ((db.learner_profile(sid) or {}).get("next_call_opener") or "").strip()
    if hook:
        return f"{GREET[lang].format(n=n)} {hook}"
    if db.recent_reviews(sid, 1):
        return f"{GREET[lang].format(n=n)} {WELCOME_BACK[lang]} {ASK_IMPROVE[lang]}"
    return f"{GREET[lang].format(n=n)} {ASK_IMPROVE[lang]}"


def after_call(session_id: str) -> None:
    """Review (coach modes) then the learner profile; safe to call more than once."""
    sess = db.get_session(session_id)
    if not sess:
        return
    try:
        if sess["mode"] in MODES and sess.get("transcript") and not db.session_review(session_id):
            evaluate(session_id)
    except Exception:
        if db.get_session(session_id) is not None:
            log.exception("evaluation failed for %s", session_id)
    try:
        update_profile(session_id)
    except Exception:
        if db.get_session(session_id) is not None:
            log.exception("profile update failed for %s", session_id)
