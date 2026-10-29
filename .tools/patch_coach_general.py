"""One-off patch: general 'coach' mode (student-led, memory-driven, resources) in api/coach.py."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "api/coach.py"
s = p.read_text(encoding="utf-8")


def rep(a: str, b: str) -> None:
    global s
    assert a in s, "MISSING: " + a[:80]
    s = s.replace(a, b)


rep('''"""Goal-driven voice coach for the open modes: English speaking and any topic (maths keeps its own engine).
Per turn: Claude replies in character with JSON {say, goal, end_call}.''',
    '''"""Goal-driven voice coach for the open modes: general coaching (default), English speaking and any topic
(maths keeps its own engine). Per turn: Claude replies in character with JSON {say, goal, language, resource, end_call}.''')
rep('MODES = ("english", "topic")', 'MODES = ("coach", "english", "topic")')
rep('''SKILLS = {
    "english":''', '''SKILLS = {
    "coach": {"understanding": "explains the idea or problem in their own words",
              "application": "uses what they learned on a new example or their own situation",
              "communication": "says clearly what they find hard and how they think",
              "participation": "how much and how willingly the student engaged"},
    "english":''')
rep('MODE_NAME = {"english": "English speaking", "topic": "Any topic", "maths": "Maths"}',
    '''MODE_NAME = {"coach": "Coaching", "english": "English speaking", "topic": "Any topic", "maths": "Maths"}


def goal_mode(mode: str) -> str:
    """Goals are stored per subject area; open coaching goals live with 'topic' (general learning goals)."""
    return "topic" if mode == "coach" else mode''')
rep('''                   "end_call": {"type": "boolean"}},
    "required": ["say", "goal", "language", "end_call"],''', '''                   "resource": {"anyOf": [{"type": "null"}, {
                       "type": "object",
                       "properties": {"kind": {"type": "string", "enum": ["book", "quote", "method"]},
                                      "title": {"type": "string"},
                                      "by": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                                      "why": {"type": "string"}},
                       "required": ["kind", "title", "by", "why"], "additionalProperties": False}]},
                   "end_call": {"type": "boolean"}},
    "required": ["say", "goal", "language", "resource", "end_call"],''')

# richer, mode-aware memory context
rep('''def context(student: dict, mode: str) -> str:
    """Stable per-student context appended to the mode prompt (cached across the call's turns)."""
    goal = db.active_goal(student["id"], mode)''', '''def context(student: dict, mode: str) -> str:
    """Stable per-student context appended to the mode prompt (cached across the call's turns)."""
    if mode == "coach":
        return coach_memory(student)
    goal = db.active_goal(student["id"], goal_mode(mode))''')
rep('''def _week_index(goal: dict) -> int:''', '''LANG_NAME = {"hi": "Hindi", "en": "English", "hi-en": "Hinglish (Hindi + English mix)"}


def coach_memory(student: dict) -> str:
    """Day-by-day memory for open coaching: recent calls (any mode), open improvement points, goals, trends,
    resources already suggested. Everything Guru needs to start where the student left off."""
    sid = student["id"]
    lines = [f"STUDENT: {student['first_name']}, class {student.get('grade') or '?'}."]
    lines.append(f"LANGUAGE: {LANG_NAME.get(student.get('language'), 'Hinglish')} (chosen before; use it)."
                 if db.language_known(sid) else "LANGUAGE: unknown. Ask in your first turn.")
    days = db.recent_reviews(sid, 5)
    if days:
        lines.append("MEMORY (most recent first):")
        for r in days:
            imp = "; ".join((r["improvements"] or [])[:2])
            lines.append(f"- {_ago(r['created_at'])}, {MODE_NAME.get(r['mode'], r['mode'])}: {r['summary'] or ''}"
                         + (f" Still to improve: {imp}" if imp else ""))
    else:
        lines.append("MEMORY: this is your first call with them.")
    goals = [g for g in db.list_goals(sid) if g["status"] == "active"]
    for g in goals[:3]:
        w = ((g.get("plan") or {}).get("weeks") or [])
        week = w[min(len(w) - 1, _week_index(g))]["focus"] if w else None
        lines.append(f"GOAL ({MODE_NAME.get(g['mode'], g['mode'])}): {g['aim']}" + (f"; this week: {week}" if week else ""))
    mis = db.active_misconceptions(sid, None, 0.5)
    if mis:
        lines.append("OPEN MATHS MISCONCEPTIONS: " + ", ".join(m["name"] for m in mis[:2]))
    trend = db.skill_trend(sid)
    if trend:
        lines.append("PROGRESS: " + trend)
    given = db.recent_resources(sid, 6)
    if given:
        lines.append("ALREADY SUGGESTED (do not repeat): " + "; ".join(r["title"] for r in given))
    return "\\n".join(lines)


def _ago(ts) -> str:
    from datetime import datetime, timezone
    d = (datetime.now(timezone.utc) - ts).days
    return "today" if d == 0 else "yesterday" if d == 1 else f"{d} days ago"


def _week_index(goal: dict) -> int:''')
rep('''FALLBACK = {
    "english":''', '''FALLBACK = {
    "coach": ["What would you like to get better at today?", "What feels hardest about it right now?",
              "Let's try one small example together. Tell me how you would start.",
              "Good work today. Practise this once more tomorrow. Bye!"],
    "english":''')
rep('''        lang = out.get("language") if out.get("language") in ("hi", "en", "hi-en") else None
        return {"say": out["say"].strip(), "goal": (out.get("goal") or None), "language": lang,
                "end_call": bool(out.get("end_call"))}''', '''        lang = out.get("language") if out.get("language") in ("hi", "en", "hi-en") else None
        res = out.get("resource") if isinstance(out.get("resource"), dict) and out["resource"].get("title") else None
        return {"say": out["say"].strip(), "goal": (out.get("goal") or None), "language": lang, "resource": res,
                "end_call": bool(out.get("end_call"))}''')
rep('''def set_goal(student_id: str, mode: str, aim: str, session_id: str | None) -> str:
    gid = db.create_goal(student_id, mode, aim)''', '''def save_resource(student_id: str, session_id: str | None, res: dict) -> None:
    """Books, quotes and methods Guru suggested: kept with the call they came from, shown on the platform."""
    db.add_fact(student_id, "note", {"type": "resource", "kind": res.get("kind"), "title": str(res.get("title"))[:160],
                                     "by": (res.get("by") or None), "why": str(res.get("why") or "")[:240]},
                0.9, session_id)


def set_goal(student_id: str, mode: str, aim: str, session_id: str | None) -> str:
    gid = db.create_goal(student_id, goal_mode(mode), aim)''')
rep('''    goal = db.active_goal(sid, mode)
    out = chat(''', '''    goal = db.active_goal(sid, goal_mode(mode))
    out = chat(''')
p.write_text(s, encoding="utf-8")
print("coach patched")
