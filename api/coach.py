"""Goal-driven voice coach for the open modes: general coaching (default), English speaking and any topic
(maths keeps its own engine). Per turn: Claude replies in character with JSON {say, goal, language, resource, end_call}. At the end: Claude evaluates the
transcript -> review (improvement points) + skill scores (0-10) that feed day/week/month progress.
Everything degrades: no LLM -> scripted fallback lines, review from simple transcript stats."""
from __future__ import annotations

import logging
import threading

import db
import events
import graph
import summaries
from llm import chat, prompt

log = logging.getLogger("coach")
MODES = ("coach", "english", "topic")
MAX_TURNS = 14          # then the coach is told to wrap up
HISTORY_TURNS = 24      # messages kept in the prompt (12 exchanges)

SKILLS = {
    "coach": {"understanding": "explains the idea or problem in their own words",
              "application": "uses what they learned on a new example or their own situation",
              "communication": "says clearly what they find hard and how they think",
              "participation": "how much and how willingly the student engaged"},
    "english": {"fluency": "speaks in full, connected sentences without long gaps (judged from the transcript)",
                "grammar": "tense, word order, articles",
                "vocabulary": "range and accuracy of words",
                "participation": "how much and how willingly the student spoke"},
    "topic": {"understanding": "explains the idea in their own words",
              "recall": "remembers what was taught earlier in the session",
              "reasoning": "applies the idea to a new example or question",
              "participation": "how much and how willingly the student answered"},
}
MODE_NAME = {"coach": "Coaching", "english": "English speaking", "topic": "Any topic", "maths": "Maths"}


def goal_mode(mode: str) -> str:
    """Goals are stored per subject area; open coaching goals live with 'topic' (general learning goals)."""
    return "topic" if mode == "coach" else mode

TURN_SCHEMA = {
    "type": "object",
    "properties": {"say": {"type": "string"}, "goal": {"type": ["string", "null"]},
                   # Claude's validator rejects enum + ["string","null"]; anyOf is the accepted form
                   "language": {"anyOf": [{"type": "string", "enum": ["hi", "en", "hi-en"]}, {"type": "null"}]},
                   "resource": {"anyOf": [{"type": "null"}, {
                       "type": "object",
                       "properties": {"kind": {"type": "string", "enum": ["book", "quote", "method"]},
                                      "title": {"type": "string"},
                                      "by": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                                      "why": {"type": "string"}},
                       "required": ["kind", "title", "by", "why"], "additionalProperties": False}]},
                   "end_call": {"type": "boolean"}},
    "required": ["say", "goal", "language", "resource", "end_call"],
    "additionalProperties": False,
}


def _review_schema(mode: str) -> dict:
    skill_props = {k: {"type": "number", "description": v + " (0-10)"} for k, v in SKILLS[mode].items()}
    strs = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "2 short sentences to the student, simple words"},
            "strengths": strs, "improvements": strs, "next_steps": strs,
            "scores": {"type": "object", "properties": skill_props, "required": list(skill_props),
                       "additionalProperties": False},
            "self_confidence": {"type": ["integer", "null"],
                                "description": "the 1-10 number the STUDENT said when asked how confident they feel; null if not asked/answered"},
            "quiz_correct": {"type": "integer"}, "quiz_total": {"type": "integer"},
            "aim": {"type": ["string", "null"]},
            "teacher_summary": {"type": "string", "description": "exactly 3 lines, English"},
            "parent_summary_hi": {"type": "string", "description": "3 short warm sentences in Hindi (Devanagari)"},
        },
        "required": ["summary", "strengths", "improvements", "next_steps", "scores", "self_confidence",
                     "quiz_correct", "quiz_total", "aim", "teacher_summary", "parent_summary_hi"],
        "additionalProperties": False,
    }


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "weeks": {"type": "array", "items": {
            "type": "object",
            "properties": {"week": {"type": "integer"}, "focus": {"type": "string"}, "milestone": {"type": "string"},
                           "practice": {"type": "array", "items": {"type": "string"}}},
            "required": ["week", "focus", "milestone", "practice"], "additionalProperties": False}},
    },
    "required": ["summary", "weeks"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- context


def context(student: dict, mode: str) -> str:
    """Stable per-student context appended to the mode prompt (cached across the call's turns)."""
    if mode == "coach":
        return coach_memory(student)
    goal = db.active_goal(student["id"], goal_mode(mode))
    last = db.last_review(student["id"], mode)
    scores = db.recent_skill_averages(student["id"], mode + ".")
    lines = [f"STUDENT: {student['first_name']}, class {student.get('grade') or '?'}, "
             f"prefers {'English' if student.get('language') == 'en' else 'Hinglish'}."]
    if goal:
        lines.append(f"MAIN GOAL: {goal['aim']}")
        plan = goal.get("plan") or {}
        if plan.get("weeks"):
            w = plan["weeks"][min(len(plan["weeks"]) - 1, _week_index(goal))]
            lines.append(f"THIS WEEK'S FOCUS: {w['focus']} (milestone: {w['milestone']})")
    else:
        lines.append("MAIN GOAL: not set yet. Early in the call, ask what they want to get better at or their dream goal.")
    if last:
        imp = "; ".join((last.get("improvements") or [])[:3])
        lines.append(f"LAST SESSION: {last.get('summary') or ''} To work on: {imp}")
    if scores:
        lines.append("RECENT SKILL SCORES (0-10): " + ", ".join(f"{k.split('.')[-1]} {v}" for k, v in scores.items()))
    return "\n".join(lines)


LANG_NAME = {"hi": "Hindi", "en": "English", "hi-en": "Hinglish (Hindi + English mix)"}


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
    return "\n".join(lines)


def _ago(ts) -> str:
    from datetime import datetime, timezone
    d = (datetime.now(timezone.utc) - ts).days
    return "today" if d == 0 else "yesterday" if d == 1 else f"{d} days ago"


def _week_index(goal: dict) -> int:
    from datetime import datetime, timezone
    return max(0, (datetime.now(timezone.utc) - goal["created_at"]).days // 7)


def system_prompt(student: dict, mode: str) -> str:
    name = "coach_general.md" if mode == "coach" else f"coach_{mode}.md"
    return prompt(name) + "\n\n" + context(student, mode)


# ---------------------------------------------------------------- turns


FALLBACK = {
    "coach": ["What would you like to get better at today?", "What feels hardest about it right now?",
              "Let's try one small example together. Tell me how you would start.",
              "Good work today. Practise this once more tomorrow. Bye!"],
    "english": ["Tell me about your favourite food in two sentences.", "What did you do yesterday? Please answer in English.",
                "Describe your school in three words.", "Good effort! Shall we stop here for today? Bye!"],
    "topic": ["What would you like to learn today?", "Can you tell me what you already know about it?",
              "Good. Let's try one quick question on that.", "Nice work today. Let's stop here. Bye!"],
}


def opening(student: dict, mode: str) -> list[dict]:
    """First user message: the call is connected; the model opens (consent was given once at sign-up)."""
    return [{"role": "user", "content": "(Call connected: the student pressed Start. Give your opening turn now, "
                                        "exactly as your instructions describe. Do not mention recording or consent.)"}]


def reply(system: str, history: list[dict], mode: str, turn_no: int) -> dict:
    msgs = history[-HISTORY_TURNS:]
    if msgs and msgs[0]["role"] != "user":
        msgs = msgs[1:]
    if turn_no >= MAX_TURNS and msgs and msgs[-1]["role"] == "user":
        msgs = msgs[:-1] + [{"role": "user", "content": msgs[-1]["content"]
                             + "\n(Time is nearly up: wrap up now as your instructions say.)"}]
    out = chat(system, msgs, TURN_SCHEMA, max_tokens=1500, timeout=12, purpose="chat")
    if isinstance(out, dict) and str(out.get("say", "")).strip():
        lang = out.get("language") if out.get("language") in ("hi", "en", "hi-en") else None
        res = out.get("resource") if isinstance(out.get("resource"), dict) and out["resource"].get("title") else None
        return {"say": out["say"].strip(), "goal": (out.get("goal") or None), "language": lang, "resource": res,
                "end_call": bool(out.get("end_call"))}
    lines = FALLBACK[mode]
    i = min(turn_no, len(lines) - 1)
    return {"say": lines[i], "goal": None, "end_call": i == len(lines) - 1, "fallback": True}


# ---------------------------------------------------------------- goals & plans


def save_resource(student_id: str, session_id: str | None, res: dict) -> None:
    """Books, quotes and methods Guru suggested: kept with the call they came from, shown on the platform."""
    db.add_fact(student_id, "note", {"type": "resource", "kind": res.get("kind"), "title": str(res.get("title"))[:160],
                                     "by": (res.get("by") or None), "why": str(res.get("why") or "")[:240]},
                0.9, session_id)


def set_goal(student_id: str, mode: str, aim: str, session_id: str | None) -> str:
    gid = db.create_goal(student_id, goal_mode(mode), aim)
    if session_id:
        db.set_session_goal(session_id, gid)
    db.add_fact(student_id, "goal", {"text": aim, "mode": mode}, 0.9, session_id)
    try:
        graph.add_goal(student_id, gid, aim)
    except Exception as e:
        log.warning("graph goal failed: %s", e)
    _background(make_plan, student_id, mode, gid, aim)
    return gid


def make_plan(student_id: str, mode: str, goal_id: str, aim: str) -> dict:
    st = db.student(student_id)
    plan = chat("You design short, realistic learning plans for school students in India. Be specific and encouraging.",
                [{"role": "user", "content": f"Student: class {st.get('grade')}, about 10 minutes of voice practice a day.\n"
                                             f"Mode: {MODE_NAME[mode]}.\nTheir goal in their own words: \"{aim}\".\n"
                                             "Make a 4-week plan: each week has a focus, a checkable milestone, and "
                                             "3 short practice activities that work on a voice call. For a big career "
                                             "goal, cover the first foundation steps only."}],
                PLAN_SCHEMA, max_tokens=4000, timeout=60)
    if not isinstance(plan, dict) or not plan.get("weeks"):
        plan = {"summary": f"Four weeks of short daily practice toward: {aim}",
                "weeks": [{"week": i, "focus": f, "milestone": m, "practice": p} for i, (f, m, p) in enumerate([
                    ("Warm up and basics", "Talk for one minute about the goal", ["daily 10-minute call"]),
                    ("Core ideas", "Answer 3 quiz questions correctly", ["explain one idea a day"]),
                    ("Practice and fix mistakes", "Fewer repeated mistakes than week 1", ["redo last week's hard parts"]),
                    ("Show what you learned", "A 2-minute explanation without help", ["mini presentation"])], 1)]}
    db.set_goal_plan(goal_id, plan)
    return plan


# ---------------------------------------------------------------- end of session


def evaluate(session_id: str) -> dict | None:
    """Claude grades the transcript -> review + skill scores + summaries. Runs off the call's critical path."""
    sess = db.get_session(session_id)
    if not sess or not sess.get("transcript"):
        return None
    mode, sid = sess["mode"], sess["student_id"]
    st = db.student(sid)
    goal = db.active_goal(sid, goal_mode(mode))
    out = chat("You evaluate a short voice coaching session with a school student. Judge only from the transcript "
               "(it is speech-to-text, so ignore spelling and filler words). Be fair, specific and kind. "
               "Never comment on mood, personality, health or family. Improvement points must be concrete "
               "and actionable (quote a better version of what the student said when useful).",
               [{"role": "user", "content": f"Mode: {MODE_NAME[mode]}. Student: {st['first_name']}, class {st.get('grade')}.\n"
                                            f"Goal: {goal['aim'] if goal else 'not set'}.\n\nTRANSCRIPT:\n{sess['transcript'][:12000]}"}],
               _review_schema(mode), max_tokens=6000, timeout=90)
    student_lines = [ln for ln in sess["transcript"].splitlines() if not ln.startswith("Guru:")]
    if not isinstance(out, dict):
        words = sum(len(ln.split(": ", 1)[-1].split()) for ln in student_lines)
        out = {"summary": f"{st['first_name']} practised {MODE_NAME[mode].lower()} and spoke about {words} words.",
               "strengths": ["Took part in the whole session"] if student_lines else [],
               "improvements": ["Try answering in full sentences"], "next_steps": ["Practise again tomorrow"],
               "scores": {}, "self_confidence": None, "quiz_correct": None, "quiz_total": None, "aim": None,
               "teacher_summary": "", "parent_summary_hi": ""}
    db.save_review(session_id, sid, sess.get("goal_id"), mode, out)
    scores = {f"{mode}.{k}": v for k, v in (out.get("scores") or {}).items()}
    if scores:
        db.add_skill_scores(sid, session_id, sess.get("goal_id"), scores, "llm")
    if out.get("self_confidence"):
        db.add_skill_scores(sid, session_id, sess.get("goal_id"), {f"{mode}.confidence": out["self_confidence"]},
                            "self_report")
    if out.get("aim") and not goal:
        set_goal(sid, mode, out["aim"], session_id)
    if out.get("teacher_summary"):
        db.save_summary(session_id, "teacher", "en", out["teacher_summary"])
    if out.get("parent_summary_hi"):
        db.save_summary(session_id, "parent", "hi", out["parent_summary_hi"])
    for skill, v in scores.items():
        try:
            graph.q("""MATCH (s:Student {id:$sid}) MERGE (k:Skill {id:$k}) SET k.name=$name
                       MERGE (s)-[r:SKILL]->(k) SET r.score=$v, r.updated=timestamp()""",
                    {"sid": sid, "k": skill, "name": skill.split(".")[-1], "v": float(v)})
        except Exception:
            pass
    events.emit(sid, "review_ready", {"session_id": session_id, "mode": mode})
    return out


def _background(fn, *args) -> None:
    """Slow LLM work (plans, evaluations) runs off the call's critical path."""
    threading.Thread(target=fn, args=args, daemon=True).start()


def finish(session_id: str, safety_flag: bool = False) -> None:
    sess = db.get_session(session_id)
    if not sess or not db.close_session(session_id, "safety_stop" if safety_flag else "ended"):
        return
    if safety_flag:
        summaries.notify_teacher_safety(sess["student_id"], session_id)
    events.emit(sess["student_id"], "session_ended", {"session_id": session_id, "mode": sess["mode"]})
    _background(_evaluate_safely, session_id)


def _evaluate_safely(session_id: str) -> None:
    try:
        evaluate(session_id)
    except Exception:
        if db.get_session(session_id) is not None:
            log.exception("evaluation failed for %s", session_id)


# ---------------------------------------------------------------- progress feedback (day / week / month)


def progress_feedback(student_id: str, period: str) -> dict:
    series = db.skill_series(student_id, period)
    reviews = db.all_rows("""select mode, summary, improvements, created_at from session_reviews
                             where student_id::text=%s order by created_at desc limit 8""", (student_id,))
    if not series:
        return {"headline": "No practice data yet.", "points": ["Do a short call to start tracking progress."],
                "focus_next": "Start with one 10-minute session."}
    trend = _trend(series)
    out = chat("You are a learning coach writing a short progress note for a school student. Use only the data given. "
               "Be honest: if something did not improve, say so kindly. No mood or personality comments.",
               [{"role": "user", "content": f"Period: by {period}.\nSkill averages (0-10) per {period}:\n"
                                            + "\n".join(f"{r['bucket']:%Y-%m-%d} {r['skill']}: {r['score']} (n={r['n']})" for r in series)
                                            + f"\n\nRecent session reviews: {[(r['mode'], r['summary'], r['improvements']) for r in reviews]}"}],
               {"type": "object", "properties": {"headline": {"type": "string"},
                                                 "points": {"type": "array", "items": {"type": "string"}},
                                                 "focus_next": {"type": "string"}},
                "required": ["headline", "points", "focus_next"], "additionalProperties": False},
               max_tokens=3000, timeout=60)
    if isinstance(out, dict):
        return {**out, "trend": trend}
    up = [k for k, d in trend.items() if d > 0.3]
    down = [k for k, d in trend.items() if d < -0.3]
    return {"headline": f"{len(up)} skill(s) improved this {period}." if up else f"Steady this {period}.",
            "points": [f"Up: {', '.join(up)}" if up else "No clear gains yet",
                       f"Needs attention: {', '.join(down)}" if down else "Nothing dropped"],
            "focus_next": f"Practise {down[0].split('.')[-1]} next." if down else "Keep the daily habit.", "trend": trend}


def _trend(series: list[dict]) -> dict[str, float]:
    by: dict[str, list[float]] = {}
    for r in series:
        by.setdefault(r["skill"], []).append(r["score"])
    return {k: round(v[-1] - v[0], 2) for k, v in by.items() if len(v) > 1}
