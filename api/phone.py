"""Phone (Bolna) coach: the call is student-led. Guru opens with what it remembers, asks the language, asks what the
student wants help with, then runs maths (misconception engine), English speaking, or any topic.
Every function here answers a Bolna tool call, so it must be fast: no LLM calls, only Postgres/graph reads."""
from __future__ import annotations

from datetime import datetime, timezone

import coach
import db
import events
import memory
import service
from service import ServiceError

LANG_NAMES = {"hi": "Hindi", "en": "English", "hi-en": "Hinglish (Hindi + English mix)"}


def _ago(ts) -> str:
    if not ts:
        return ""
    d = (datetime.now(timezone.utc) - ts).days
    return "today" if d == 0 else "yesterday" if d == 1 else f"{d} days ago"


def _this_week(goal: dict) -> dict | None:
    weeks = (goal.get("plan") or {}).get("weeks") or []
    return weeks[min(len(weeks) - 1, coach._week_index(goal))] if weeks else None


def _weekly_trend(student_id: str) -> str | None:
    """Plain-words change per skill between the first and last week with data (last 12 weeks)."""
    by: dict[str, list[float]] = {}
    for r in db.skill_series(student_id, "week"):
        by.setdefault(r["skill"], []).append(r["score"])
    ups = [k.split(".")[-1] for k, v in by.items() if len(v) > 1 and v[-1] - v[0] >= 0.5]
    downs = [k.split(".")[-1] for k, v in by.items() if len(v) > 1 and v[0] - v[-1] >= 0.5]
    if not ups and not downs:
        return None
    parts = ([f"improving in {', '.join(ups)}"] if ups else []) + ([f"dipping in {', '.join(downs)}"] if downs else [])
    return " and ".join(parts)


def open_session(student_id: str, call_id: str | None) -> dict:
    """get_session_context: create the call's session and give Guru everything it should remember."""
    st = db.student(student_id)
    if not st:
        raise ServiceError(404, "unknown student")
    if not db.has_consent(student_id):
        raise ServiceError(403, "no guardian consent on file; the call must end politely")
    sess = db.create_session(student_id, call_id, "phone", None, "open")
    if not sess["existing"]:
        events.emit(student_id, "session_started", {"session_id": sess["id"], "mode": "open", "channel": "phone"})

    last = db.one("""select r.mode, r.summary, r.improvements, s.started_at from session_reviews r
                     join sessions s on s.id=r.session_id where r.student_id::text=%s
                     order by r.created_at desc limit 1""", (student_id,))
    conf = db.one("""select skill, score, created_at from skill_scores where student_id::text=%s
                     and source='self_report' order by created_at desc limit 1""", (student_id,))
    goals = [{"mode": g["mode"], "aim": g["aim"], "this_week": (_this_week(g) or {}).get("focus")}
             for g in db.list_goals(student_id) if g["status"] == "active"]
    mis = db.active_misconceptions(student_id, None, 0.4)
    names = db.misconception_names()

    options = [f"Your goal: {g['aim']}" for g in goals[:2]]
    if last and last["improvements"]:
        options.append(f"Continue: {last['improvements'][0]}")
    if mis:
        options.append(f"Maths: fix '{names[mis[0]['id']]}'")
    options += ["English speaking practice", "Anything you want to learn or improve"]

    return {
        "session_id": sess["id"], "first_name": st["first_name"],
        # ask the language only on the first call; afterwards use the saved choice
        "language": LANG_NAMES.get(st["language"], "Hinglish") if db.language_known(student_id) else "unknown: ask",
        "recent_days": [{"when": _ago(r["created_at"]), "practised": coach.MODE_NAME.get(r["mode"], r["mode"]),
                         "summary": r["summary"], "still_to_improve": (r["improvements"] or [])[:2]}
                        for r in db.recent_reviews(student_id, 3)],
        "already_suggested": [r["title"] for r in db.recent_resources(student_id, 6)],
        "last_call": ({"when": _ago(last["started_at"]), "practised": coach.MODE_NAME.get(last["mode"], last["mode"]),
                       "summary": last["summary"], "work_on": (last["improvements"] or [])[:2]} if last else None),
        "goals": goals,
        "last_self_reported_confidence": ({"value": round(conf["score"]), "skill": conf["skill"].split(".")[0],
                                           "when": _ago(conf["created_at"])} if conf else None),
        "weekly_progress": _weekly_trend(student_id),
        "mistakes_to_fix": [{"name": names[m["id"]], "strength": round(float(m["strength"]), 2)} for m in mis[:2]],
        "suggested_options": options[:4],
    }


def set_language(session_id: str, language: str) -> dict:
    sess = db.get_session(session_id)
    if not sess:
        raise ServiceError(404, "unknown session_id; call get_session_context first")
    lang = {"hindi": "hi", "hi": "hi", "english": "en", "en": "en", "hinglish": "hi-en", "hi-en": "hi-en",
            "mix": "hi-en", "both": "hi-en"}.get(language.strip().lower(), "hi-en")
    db.remember_language(sess["student_id"], lang, session_id)
    return {"ok": True, "language": LANG_NAMES[lang],
            "instruction": f"From now on speak {LANG_NAMES[lang]}."}


def choose_topic(session_id: str, mode: str, topic: str | None = None) -> dict:
    """The student picked what to practise. Maths starts the misconception engine; the others get coaching notes."""
    sess = db.get_session(session_id)
    if not sess:
        raise ServiceError(404, "unknown session_id; call get_session_context first")
    mode = {"math": "maths", "mathematics": "maths", "english speaking": "english", "any": "coach",
            "general": "coach", "open": "coach", "coaching": "coach"}.get((mode or "").strip().lower(),
                                                                        (mode or "").strip().lower())
    if mode not in ("coach", "maths", "english", "topic"):
        raise ServiceError(422, "mode must be coach, maths, english or topic")
    sid = sess["student_id"]
    goal = db.active_goal(sid, coach.goal_mode(mode))
    db.run("update sessions set mode=%s, goal_id=%s where id::text=%s",
           (mode, goal["id"] if goal else None, session_id))

    if mode == "maths":
        topic_id = db.resolve_topic(topic) or db.pick_topic(sid)
        db.run("update sessions set topic_id=%s where id::text=%s", (topic_id, session_id))
        ctx = memory.retrieve(sid, topic_id)
        q = db.next_question(session_id, sid, topic_id, ctx["misconceptions"])
        return {"mode": "maths", "topic": db.topic_names()[topic_id],
                "active_misconceptions": ctx["misconceptions"], "strategy": ctx["strategy"],
                "question": {"id": q["id"], "text": q["text"]} if q else None,
                "instruction": "Ask the confidence question (1-10) and call log_confidence, then ask the question "
                               "exactly and call submit_answer with every answer."}

    last = db.last_review(sid, mode)
    week = _this_week(goal) if goal else None
    notes = {
        "mode": mode, "topic": topic or (goal["aim"] if goal else None),
        "goal": goal["aim"] if goal else None,
        "this_week_focus": week["focus"] if week else None,
        "milestone": week["milestone"] if week else None,
        "work_on_from_last_time": (last["improvements"] or [])[:2] if last else [],
    }
    if mode == "coach":
        notes["instruction"] = (
            "Open coaching on what the student chose. Diagnose first (ask what exactly is hard or have them try one "
            "small example), then teach one idea at a time with an everyday example and let them try. Explain their "
            "mistake plainly: what it is, why it happens, how to fix it. When it truly helps (once, at most twice), "
            "suggest ONE real book (exact title and author), a correctly attributed quote, or a proven method "
            "(active recall, spaced repetition, Feynman technique, Pomodoro, error notebook, shadowing for spoken "
            "English) and call save_suggestion with it. Never invent a book or quote.")
    elif mode == "english":
        notes["instruction"] = ("Coach spoken English: short activities (introduce yourself, describe your day, "
                                "role-play an interview). Correct ONE mistake per turn gently and ask them to repeat "
                                "the better sentence. Near the end ask them to rate their confidence 1-10.")
    else:
        notes["instruction"] = ("Teach the chosen topic in tiny spoken steps: one idea, an everyday Indian example, "
                                "then a quick check question. Hint before answer. Every few turns ask a quiz question.")
    if not goal:
        notes["instruction"] += " If they say a bigger goal, call set_goal with it."
    return notes


def save_suggestion(session_id: str, kind: str, title: str, by: str | None, why: str) -> dict:
    """A book / quote / method Guru suggested on the phone: stored with the call, shown on the platform."""
    sess = db.get_session(session_id)
    if not sess:
        raise ServiceError(404, "unknown session_id")
    kind = kind if kind in ("book", "quote", "method") else "method"
    coach.save_resource(sess["student_id"], session_id, {"kind": kind, "title": title, "by": by, "why": why})
    return {"ok": True}


def set_goal(session_id: str, aim: str) -> dict:
    sess = db.get_session(session_id)
    if not sess:
        raise ServiceError(404, "unknown session_id")
    mode = sess["mode"] if sess["mode"] in ("maths", "english", "topic") else "topic"
    current = db.active_goal(sess["student_id"], mode)
    if current and current["aim"].strip().lower() == aim.strip().lower():
        return {"ok": True, "goal": current["aim"]}
    coach.set_goal(sess["student_id"], mode, aim, session_id)
    return {"ok": True, "goal": aim, "note": "A 4-week plan is being prepared; mention it briefly."}


def end(session_id: str, safety_flag: bool = False) -> dict:
    """Maths keeps its own end (plan + summaries). Coach modes close now and are evaluated when Bolna's post-call
    webhook delivers the full transcript."""
    sess = db.get_session(session_id)
    if not sess:
        raise ServiceError(404, "unknown session_id")
    if sess["mode"] == "maths" and sess["topic_id"]:
        return service.end_session(session_id, safety_flag)
    closed = db.close_session(session_id, "safety_stop" if safety_flag else "ended")
    if closed:
        if safety_flag:
            from summaries import notify_teacher_safety
            notify_teacher_safety(sess["student_id"], session_id)
        events.emit(sess["student_id"], "session_ended", {"session_id": session_id, "mode": sess["mode"]})
    goal = db.active_goal(sess["student_id"], sess["mode"]) if sess["mode"] in coach.MODES else None
    return {"ok": True, "next_plan": [f"10 minutes of {coach.MODE_NAME.get(sess['mode'], 'practice').lower()} tomorrow"]
            + ([f"Keep going on: {goal['aim']}"] if goal else [])}
