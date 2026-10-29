from pathlib import Path
p = Path("api/coach.py"); s = p.read_text(encoding="utf-8")

# ---- 1) coach_memory: progression-oriented, no verbatim drill sentences
start = s.index("def coach_memory(student: dict) -> str:")
end = s.index("def _ago(ts) -> str:")
new_mem = '''def _unquote(text: str) -> str:
    """Drop quoted practice sentences from memory: they made the next call re-drill the same line."""
    return re.sub(r'["“][^"”]{0,160}["”]', "a practice sentence", text or "").strip()


def coach_memory(student: dict) -> str:
    """What Guru remembers at the start of a call, built for PROGRESS: the goal in the student's words, what was
    already covered (never redo it), the next new topics, and how to coach this person. Same text for browser and
    phone calls."""
    sid = student["id"]
    prof = db.learner_profile(sid) or {}
    lines = [f"STUDENT: {spoken_name(student['first_name'])}, class {student.get('grade') or '?'}."]
    lines.append(f"LANGUAGE: {LANG_NAME.get(student.get('language'), 'Hinglish')} (chosen before; use it)."
                 if db.language_known(sid) else "LANGUAGE: unknown. Ask in your first turn.")
    goals = [g for g in db.list_goals(sid) if g["status"] == "active"]
    if prof.get("goal_in_their_words"):
        lines.append(f"THEIR GOAL (their words): {prof['goal_in_their_words']}")
    for g in goals[:2]:
        w = ((g.get("plan") or {}).get("weeks") or [])
        week = w[min(len(w) - 1, _week_index(g))]["focus"] if w else None
        lines.append(f"GOAL ({MODE_NAME.get(g['mode'], g['mode'])}): {g['aim']}" + (f"; this week: {week}" if week else ""))
    days = db.recent_reviews(sid, 4)
    if not days:
        lines.append("MEMORY: this is your first call with them.")
    else:
        lines.append("PAST CALLS (done: build on them, never redo their exercises or sentences):")
        for r in days:
            first = _unquote((r["summary"] or "").split(". ")[0])
            lines.append(f"- {_ago(r['created_at'])}, {MODE_NAME.get(r['mode'], r['mode'])}: {first}")
    if prof.get("topics_covered"):
        lines.append("TOPICS ALREADY COVERED (do not repeat): " + "; ".join(prof["topics_covered"][:8]))
    if prof.get("next_topics"):
        lines.append("NEXT NEW TOPICS (offer these, or follow whatever the student asks for): "
                     + "; ".join(prof["next_topics"][:4]))
    mis = db.active_misconceptions(sid, None, 0.5)
    if mis:
        lines.append("OPEN MATHS MISCONCEPTIONS: " + ", ".join(m["name"] for m in mis[:2]))
    trend = db.skill_trend(sid)
    if trend:
        lines.append("PROGRESS: " + trend)
    given = db.recent_resources(sid, 6)
    if given:
        lines.append("ALREADY SUGGESTED (do not repeat): " + "; ".join(r["title"] for r in given))
    notes = [(label, prof.get(key)) for key, label in PROFILE_LABELS]
    notes = [(label, "; ".join(map(str, v[:3])) if isinstance(v, list) else v) for label, v in notes if v]
    if notes:
        lines.append("HOW TO COACH THEM (your notes):")
        lines += [f"- {label}: {_unquote(str(v))}" for label, v in notes]
    return "\\n".join(lines)


'''
s = s[:start] + new_mem + s[end:]
if "\nimport re\n" not in s:
    s = s.replace("import logging\n", "import logging\nimport re\n", 1)

# ---- 2) profile: goal in their words, topics covered, next NEW topics; plan moves forward
s = s.replace('''PROFILE_LABELS = [("about", "About them"), ("motivation", "What motivates them"),
                  ("confidence_pattern", "Confidence"), ("recurring_mistakes", "Recurring mistakes"),
                  ("what_works", "What works with them"), ("watch_outs", "Be careful about"),
                  ("direction", "Direction (next steps)"), ("next_call_plan", "Plan for the next call")]''',
'''PROFILE_LABELS = [("about", "About them"), ("motivation", "What motivates them"),
                  ("confidence_pattern", "Confidence"), ("recurring_mistakes", "Patterns to fix (one at a time)"),
                  ("what_works", "What works with them"), ("watch_outs", "Be careful about"),
                  ("direction", "Direction"), ("next_call_plan", "Plan for the next call")]''')
old = '''        "direction": {"type": "string", "description": "where they are heading and the next 1-2 concrete steps"},
        "next_call_plan": {"type": "string", "description": "what to check or practise at the start of the next call"},'''
new = '''        "goal_in_their_words": {"type": "string", "description": "what the student said they want, in their own "
                                "words. Speech-to-text mishears: e.g. 'cooperative English' or 'कोपरेट इंग्लिश' "
                                "from a working adult most likely means corporate (office) English"},
        "topics_covered": {**_strs, "description": "short names of topics/situations already practised across all "
                                                  "calls (keep the old ones, add this call's)"},
        "next_topics": {**_strs, "description": "3 NEW topics not yet covered, in a sensible order, that move them "
                                                "toward their goal (e.g. corporate English: introducing yourself in a "
                                                "meeting, giving a work update, polite requests, disagreeing politely, "
                                                "small talk with colleagues, answering interview questions)"},
        "direction": {"type": "string", "description": "where they are heading and the next 1-2 concrete steps"},
        "next_call_plan": {"type": "string", "description": "how the next call should MOVE FORWARD: a short warm "
                           "check-in, then the first of next_topics through a real conversation or role-play. Never "
                           "plan to re-practise a sentence from an earlier call."},'''
assert old in s; s = s.replace(old, new)
s = s.replace('''    "required": ["about", "motivation", "confidence_pattern", "recurring_mistakes", "what_works", "watch_outs",
                 "direction", "next_call_plan", "next_call_opener", "language_chosen"],''',
'''    "required": ["about", "motivation", "confidence_pattern", "recurring_mistakes", "what_works", "watch_outs",
                 "goal_in_their_words", "topics_covered", "next_topics", "direction", "next_call_plan",
                 "next_call_opener", "language_chosen"],''')
old_op = '''"that links to this call as a warm check-in on their real life or progress and ends with a "
                             "question, e.g. 'Pichli baar aapne public speaking ke darr ki baat ki thi, kya aapne "
                             "mirror practice try ki?'. Never a drill or a request to repeat a sentence."},'''
new_op = '''"that links to their goal with a warm check-in and offers the next NEW topic, ending with "
                             "a question, e.g. 'Last time we practised introducing yourself; today shall we try giving "
                             "a quick work update in a meeting?'. Never a drill, never a sentence to repeat, no "
                             "quotation marks."},'''
assert old_op in s; s = s.replace(old_op, new_op)
old_sys = '''"Refer to the student by name, never as he or she.",'''
new_sys = '''"Refer to the student by name, never as he or she. Coaching must PROGRESS: every call covers something "
               "new toward the student's own goal; never plan to repeat an exercise or sentence that was already "
               "practised. If the student asked for something different or a new topic, that wins. The transcript "
               "is speech-to-text and often broken or misheard: do not record misrecognitions as the student's "
               "mistakes.",'''
assert old_sys in s; s = s.replace(old_sys, new_sys)
p.write_text(s, encoding="utf-8")
print("ok")
