"""Goal-driven voice coach for the open modes: general coaching (default), English speaking and any topic
(maths keeps its own engine). Per turn: Claude replies in character with JSON {say, goal, language, resource, end_call}. At the end: Claude evaluates the
transcript -> review (improvement points) + skill scores (0-10) that feed day/week/month progress.
Everything degrades: no LLM -> scripted fallback lines, review from simple transcript stats."""
from __future__ import annotations

import logging
import re
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
MODE_NAME = {"coach": "Mentoring", "english": "English speaking", "topic": "Any topic", "maths": "Maths"}


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
    lines = [f"PERSON: {who(student)}, "
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


def who(student: dict) -> str:
    """'Ashu, college student' / 'Riya, class 9' / 'Piyush': no assumption that everyone is in school."""
    parts = [spoken_name(student.get("first_name")) or "Unknown"]
    if student.get("about"):
        parts.append(str(student["about"]))
    elif student.get("grade"):
        parts.append(f"class {student['grade']}")
    return ", ".join(parts)


def _unquote(text: str) -> str:
    """Drop quoted practice sentences from memory: they made the next call re-drill the same line."""
    return re.sub(r'["“][^"”]{0,160}["”]', "a practice sentence", text or "").strip()


def coach_memory(student: dict) -> str:
    """What Guru remembers at the start of a call, built for PROGRESS: the goal in the student's words, what was
    already covered (never redo it), the next new topics, and how to coach this person. Same text for browser and
    phone calls."""
    sid = student["id"]
    prof = db.learner_profile(sid) or {}
    lines = [f"PERSON: {who(student)}."]
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
    if days:
        import learning_graph
        steps = learning_graph.next_steps(sid, 3)
        if steps:
            lines.append("NEXT BEST STEPS (ranked from their data; use one, explain why it works in simple words): "
                         + "; ".join(f"{x['title']} ({x['principle']})" for x in steps))
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
        lines += [f"- {label}: {v}" for label, v in notes]
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
    plan = chat("You are a mentor designing short, realistic improvement plans for one person in India (a school or "
                "college student, a working professional or a job seeker). Be specific, practical and encouraging.",
                [{"role": "user", "content": f"Person: {who({**st, 'id': student_id})}, about 10 minutes of voice "
                                             "mentoring a day.\n"
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
    out = chat("You evaluate a short voice mentoring session with one learner (any age or background). Judge only "
               "from the transcript "
               "(it is speech-to-text, so ignore spelling and filler words). Be fair, specific and kind. "
               "Never comment on mood, personality, health or family. Improvement points must be concrete "
               "and actionable (quote a better version of what the student said when useful).",
               [{"role": "user", "content": f"Mode: {MODE_NAME[mode]}. Person: {who({**st, 'id': sid})}.\n"
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
    after_call(session_id)


# ---------------------------------------------------------------- learner profile (cross-call memory)

PROFILE_LABELS = [("about", "About them"), ("challenges", "Open problems (problem; root cause; next action; status)"),
                  ("solutions_tried", "Tried so far and result"), ("motivation", "What motivates them"),
                  ("confidence_pattern", "Confidence"), ("recurring_mistakes", "Patterns to fix (one at a time)"),
                  ("what_works", "What works with them"), ("watch_outs", "Be careful about"),
                  ("direction", "Direction"), ("next_call_plan", "Plan for the next call")]

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
        "goal_in_their_words": {"type": "string", "description": "what the student said they want, in their own "
                                "words. Speech-to-text mishears: e.g. 'cooperative English' or 'कोपरेट इंग्लिश' "
                                "from a working adult most likely means corporate (office) English. If an ACTIVE GOAL is "
                                "more specific than the transcript, use the active goal"},
        "challenges": {**_strs, "description": "open problems the person brought (studies, career, work, confidence, "
                                               "habits...), each as: problem; likely root cause; next small action; "
                                               "status new / improving / solved. Keep older ones and update status."},
        "solutions_tried": {**_strs, "description": "what was tried so far and what happened, e.g. 'Pomodoro 25 min: "
                                                    "helped focus 2 of 3 days'. Keep older ones."},
        "topics_covered": {**_strs, "description": "short names of topics/situations already practised across all "
                                                  "calls (keep the old ones, add this call's)"},
        "next_topics": {**_strs, "description": "3 NEW topics not yet covered, in a sensible order, that move them "
                                                "toward their goal (e.g. corporate English: introducing yourself in a "
                                                "meeting, giving a work update, polite requests, disagreeing politely, "
                                                "small talk with colleagues, answering interview questions)"},
        "direction": {"type": "string", "description": "where they are heading and the next 1-2 concrete steps"},
        "next_call_plan": {"type": "string", "description": "how the next call should MOVE FORWARD: a short warm "
                           "check-in, then the first of next_topics through a real conversation or role-play. Never "
                           "plan to re-practise a sentence from an earlier call."},
        "next_call_opener": {"type": "string", "description": "ONE short spoken sentence for the next call, in the "
                             "student's language (Hindi in Devanagari, Hinglish in Latin script, or English), under 20 words, "
                             "no greeting, exactly one question, "
                             "that links to their goal with a warm check-in and offers the next NEW topic, ending with "
                             "a question, e.g. 'Last time we practised introducing yourself; today shall we try giving "
                             "a quick work update in a meeting?'. Never a drill, never a sentence to repeat, no "
                             "quotation marks."},
        "language_chosen": {"anyOf": [{"type": "string", "enum": ["hi", "en", "hi-en"]}, {"type": "null"}],
                            "description": "the language the student SAID they want to talk in (hi Hindi, en English, "
                                           "hi-en mix); null if they never said"},
    },
    "required": ["about", "motivation", "confidence_pattern", "recurring_mistakes", "what_works", "watch_outs",
                 "goal_in_their_words", "challenges", "solutions_tried", "topics_covered", "next_topics",
                 "direction", "next_call_plan",
                 "next_call_opener", "language_chosen"],
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
    active_goals = "; ".join(g["aim"] for g in db.list_goals(sid) if g["status"] == "active") or "none"
    prev_txt = "\n".join(f"{k}: {v}" for k, v in (prev or {}).items() if k not in ("type", "updated_at")) or "none yet"
    out = chat("You keep a mentor's private notes about one person (a student, college learner, working "
               "professional or job seeker), used to personalise the next call. Track their real problems like a good "
               "counsellor-mentor: the problem, its likely root cause, what they tried and whether it worked, and the "
               "next small step. "
               "Merge the previous notes with what this call shows: keep what is still true, update what changed, "
               "drop what is stale. Be specific and brief (each field under 40 words). Ground advice in learning "
               "science (retrieval practice, spacing, worked examples, growth mindset, self-efficacy through small "
               "wins, implementation intentions) and in what actually worked for this student. Never guess mood, "
               "health, personality or family matters; confidence is only what the student said. If the call was "
               "off-topic or rude, note kindly how to steer them back to learning, without judging them. "
               "Refer to the student by name, never as he or she. Coaching must PROGRESS: every call covers something "
               "new toward the student's own goal; never plan to repeat an exercise or sentence that was already "
               "practised. If the student asked for something different or switched topic during the call (e.g. from "
               "English practice to becoming an AI engineer), that new topic becomes goal_in_their_words, the first "
               "of next_topics, the direction and the next_call_opener. The transcript "
               "is speech-to-text and often broken or misheard: do not record misrecognitions as the student's "
               "mistakes.",
               [{"role": "user", "content": f"Person: {who({**st, 'id': sid})}, "
                                            f"language: {LANG_NAME.get(st.get('language'), 'unknown')}.\n"
                                            f"ACTIVE GOALS: {active_goals}\n"
                                            f"PREVIOUS NOTES:\n{prev_txt}\n\n"
                                            f"THIS CALL'S REVIEW: {review.get('summary') or 'none'} "
                                            f"Improve: {'; '.join(review.get('improvements') or [])}\n\n"
                                            f"TRANSCRIPT ({MODE_NAME.get(sess['mode'], sess['mode'])}):\n"
                                            f"{sess['transcript'][:10000]}"}],
               PROFILE_SCHEMA, max_tokens=3000, timeout=90)
    if not isinstance(out, dict):
        return None
    lang = out.pop("language_chosen", None)
    if lang in LANG_NAME and not db.language_known(sid):     # e.g. said on a call whose language tool failed
        db.remember_language(sid, lang, session_id)
    db.save_learner_profile(sid, out, session_id)
    try:
        graph.q("MATCH (s:Student {id:$sid}) SET s.direction=$d, s.motivation=$m",
                {"sid": sid, "d": out.get("direction") or "", "m": out.get("motivation") or ""})
    except Exception:
        pass
    return out


GREET = {"hi": "नमस्ते {n}! मैं गुरु, आपका AI कोच।", "en": "Hi {n}! It's Guru, your AI coach.",
         "hi-en": "Hi {n}! Guru bol raha hoon, aapka AI coach."}
ASK_IMPROVE = {"hi": "आज क्या चल रहा है, किस बात में मदद करूँ?", "en": "What's on your mind today, what can I help you with?",
               "hi-en": "Aaj kya chal raha hai, kis baat mein help karun?"}
WELCOME_BACK = {"hi": "आपसे फिर बात करके अच्छा लगा।", "en": "Good to talk again.",
                "hi-en": "Phir se baat karke accha laga."}
FIRST_MEET = {"hi": "आपसे मिलकर बहुत खुशी हुई।", "en": "So nice to meet you.",
              "hi-en": "Aapse milkar bahut khushi hui."}
# A caller Guru has no profile for: warm, respectful, asks only the name (no data assumed).
UNKNOWN_CALLER = ("Namaste! Main Guru hoon, ek AI learning coach. Aapse baat karke bahut accha laga. "
                  "Aapka shubh naam kya hai?")


def spoken_name(first_name: str | None) -> str:
    """How Guru says the name: first word, capitalised ('rahul ai' -> 'Rahul', 'ASHU' -> 'Ashu')."""
    word = (first_name or "").strip().split()
    return word[0][:1].upper() + word[0][1:].lower() if word else ""


def opening_line(student: dict) -> str:
    """The first thing Guru says on a phone call (Bolna welcome message). The student signed up, so Guru already
    knows their name and greets them by it. First call: a warm hello + the language question (or what to improve
    if the language was chosen at sign-up). Later calls: one sentence linking to the last call. No LLM: instant."""
    sid, n = student["id"], spoken_name(student.get("first_name"))
    if not n:
        return UNKNOWN_CALLER
    prof = db.learner_profile(sid)
    first_call = not prof and not db.one("""select 1 as ok from sessions where student_id::text=%s
                                             and ended_at is not null limit 1""", (sid,))
    if first_call or not db.language_known(sid):
        return (f"Namaste {n}! Main Guru hoon, aapka AI mentor. Aapse milkar bahut khushi hui. "
                "Hum kis language mein baat shuru karein: Hindi, English, ya dono ka mix?")
    lang = student.get("language") if student.get("language") in GREET else "hi-en"
    if first_call:
        return f"{GREET[lang].format(n=n)} {FIRST_MEET[lang]} {ASK_IMPROVE[lang]}"
    hook = ((prof or {}).get("next_call_opener") or "").strip()
    # Claude's saved line often starts with its own greeting ("Hi Piyush," / "नमस्ते आशु,"): we already greeted
    hook = re.sub(r"^(?:hi|hello|hey|namaste|नमस्ते|नमस्कार)[^,!।.?]{0,20}[,!।.]\s*", "", hook, flags=re.I).strip()
    hook = hook[:1].upper() + hook[1:]
    if hook:
        return f"{GREET[lang].format(n=n)} {hook}"
    return f"{GREET[lang].format(n=n)} {WELCOME_BACK[lang]} {ASK_IMPROVE[lang]}"


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
    import learning_graph
    learning_graph.sync_safely(sess["student_id"])
    events.emit(sess["student_id"], "profile_updated", {"session_id": session_id, "graph": True})


# ---------------------------------------------------------------- progress feedback (day / week / month)


def progress_feedback(student_id: str, period: str) -> dict:
    series = db.skill_series(student_id, period)
    reviews = db.all_rows("""select mode, summary, improvements, created_at from session_reviews
                             where student_id::text=%s order by created_at desc limit 8""", (student_id,))
    if not series:
        return {"headline": "No practice data yet.", "points": ["Do a short call to start tracking progress."],
                "focus_next": "Start with one 10-minute session."}
    trend = _trend(series)
    out = chat("You are a mentor writing a short progress note for one learner. Use only the data given. "
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
