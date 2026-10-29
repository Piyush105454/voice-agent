"""The tutor core. One implementation behind every channel: Bolna phone tools, the text simulator,
and the Sarvam browser call. Postgres is written first (truth); graph + events are best-effort."""
from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor

import db
from config import settings
import events
import graph
import mastery
import memory
import safety
import summaries
import tutor

log = logging.getLogger("service")
_bg = ThreadPoolExecutor(max_workers=2, thread_name_prefix="post-session")


class ServiceError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _g(fn, *args) -> None:
    try:
        fn(*args)
    except Exception as e:  # graph is derived; rebuild_graph() repairs drift
        log.warning("graph %s failed: %s", fn.__name__, e)


def _session(session_id: str) -> dict:
    s = db.get_session(session_id)
    if not s:
        raise ServiceError(404, "unknown session_id; call get_session_context first")
    return s


# ---------------------------------------------------------------- get_session_context


def get_context(student_id: str, call_id: str | None = None, channel: str = "phone") -> dict:
    st = db.student(student_id)
    if not st:
        raise ServiceError(404, "unknown student")
    if not db.has_consent(student_id):
        raise ServiceError(403, "no guardian consent on file; the call must end politely")
    topic_id = db.pick_topic(student_id)
    sess = db.create_session(student_id, call_id, channel, topic_id)
    topic_id = sess["topic_id"]
    ctx = memory.retrieve(student_id, topic_id)
    q = db.next_question(sess["id"], student_id, topic_id, ctx["misconceptions"])
    if not sess["existing"]:
        events.emit(student_id, "session_started", {"session_id": sess["id"], "topic": topic_id,
                                                    "channel": channel})
    return {"session_id": sess["id"], "first_name": st["first_name"], "language": st["language"],
            "topic": db.topic_names()[topic_id], "topic_id": topic_id,
            "active_misconceptions": ctx["misconceptions"], "strategy": ctx["strategy"],
            "weak_prerequisite": ctx["weak_prereq"]["name"] if ctx["weak_prereq"] else None,
            "question": {"id": q["id"], "text": q["text"]} if q else None}


# ---------------------------------------------------------------- submit_answer


def submit_answer(session_id: str, question_id: str, text: str) -> dict:
    sess = _session(session_id)
    if sess["ended_at"]:
        raise ServiceError(409, "session already ended")
    sid = sess["student_id"]

    if safety.scan(text):
        end_session(session_id, safety_flag=True)
        return {"action": "safety_stop", "say": safety.reply(db.student(sid)["language"]),
                "correct": False, "misconception": None, "hint_level": 0, "hint_text": None,
                "next_question": None}

    qn = db.get_question(question_id)
    if not qn:
        raise ServiceError(404, f"unknown question_id {question_id!r}; use the id from the last question")
    st = db.student(sid)

    judged = tutor.judge(qn, text, db.misconception_descriptions())
    prior = db.hints_used(session_id, qn["id"])
    act = tutor.decide_action(judged["correct"], prior)
    mis = judged.get("misconception")
    db.log_attempt(session_id, qn["id"], text, judged["correct"], mis, act["hint_level"])

    # mastery (BKT) + stability
    p_old, stab, _ = db.get_mastery(sid, qn["topic_id"])
    p_new = mastery.bkt_update(p_old, judged["correct"], prior)
    stab_new = mastery.grow_stability(stab, judged["correct"], prior)
    db.set_mastery(sid, qn["topic_id"], p_new, stab_new)
    db.snapshot(sid, session_id, "mastery", qn["topic_id"], p_new)
    _g(graph.set_mastery, sid, qn["topic_id"], p_new, stab_new)

    # misconception strength: up on a tagged error, down on correct use of the same idea
    if mis:
        strength = mastery.misconception_update(db.get_misconception_strength(sid, mis), "error")
        n = db.set_misconception_strength(sid, mis, strength, is_evidence=True)
        db.snapshot(sid, session_id, "misconception", mis, strength)
        _g(graph.set_misconception_strength, sid, mis, strength, n)
        events.emit(sid, "misconception_detected", {"misconception": mis, "strength": round(strength, 3),
                                                    "topic": qn["topic_id"], "question_id": qn["id"]})
    elif judged["correct"]:
        targets = set((qn["wrong_answer_map"] or {}).values()) | {
            m["id"] for m in db.active_misconceptions(sid, qn["topic_id"])}
        for m in targets & {m["id"] for m in db.active_misconceptions(sid)}:
            strength = mastery.misconception_update(db.get_misconception_strength(sid, m),
                                                    "correct" if prior == 0 else "guided_correct")
            n = db.set_misconception_strength(sid, m, strength, is_evidence=False)
            db.snapshot(sid, session_id, "misconception", m, strength)
            _g(graph.set_misconception_strength, sid, m, strength, n)

    events.emit(sid, "attempt", {"correct": judged["correct"], "misconception": mis, "mastery": round(p_new, 3),
                                 "topic": qn["topic_id"], "question_id": qn["id"], "hint_level": act["hint_level"]})

    out = {"correct": judged["correct"], "misconception": mis,
           "misconception_name": db.misconception_names().get(mis) if mis else None,
           "hint_level": act["hint_level"], "action": act["action"], "hint_text": None,
           "mastery": round(p_new, 3), "next_question": None}
    if act["action"] != "praise_next":
        strategy = memory.retrieve(sid, qn["topic_id"])["strategy"] if settings.llm_hints else "step_by_step"
        out["hint_text"] = tutor.hint(qn, mis, act["hint_level"], st["language"], strategy,
                                      db.misconception_descriptions().get(mis, ""))
    if act["action"] in ("praise_next", "reveal"):
        active = [m["id"] for m in db.active_misconceptions(sid, qn["topic_id"])]
        nq = db.next_question(session_id, sid, qn["topic_id"], active)
        out["next_question"] = {"id": nq["id"], "text": nq["text"]} if nq else None
    return out


# ---------------------------------------------------------------- log_confidence


def log_confidence(session_id: str, topic: str | None, phase: str, value: int) -> dict:
    sess = _session(session_id)
    if phase not in ("before", "after"):
        raise ServiceError(422, "phase must be 'before' or 'after'")
    topic_id = db.resolve_topic(topic) or sess["topic_id"]
    value = max(1, min(10, int(value)))
    db.log_confidence(session_id, topic_id, phase, value)
    if sess.get("mode") in ("english", "topic"):
        db.add_skill_scores(sess["student_id"], session_id, sess.get("goal_id"), {f"{sess['mode']}.confidence": value},
                            "self_report")
    events.emit(sess["student_id"], "confidence", {"phase": phase, "value": value, "topic": topic_id})
    return {"ok": True}


# ---------------------------------------------------------------- end_session


def plan_for(student_id: str, topic_id: str) -> tuple[list[dict], list[str]]:
    """Deterministic 3-day mini plan: weakest prerequisite first, retrieval practice, then independent."""
    names = db.topic_names()
    try:
        weak = graph.weakest_prerequisite(student_id, topic_id)
    except Exception:
        weak = None
    items: list[dict] = []
    if weak:
        items.append({"day": 1, "topic_id": weak["id"], "type": "guided", "n": 3})
    items.append({"day": 1, "topic_id": topic_id, "type": "review", "n": 3})
    items.append({"day": 2, "topic_id": topic_id, "type": "independent", "n": 3})
    nxt = db.one("select topic_id from topic_prereqs where prereq_id=%s order by topic_id limit 1", (topic_id,))
    items.append({"day": 3, "topic_id": nxt["topic_id"] if nxt else topic_id, "type": "guided", "n": 3})
    spoken = [f"{names[i['topic_id']]} recap" if i["type"] == "guided" and i["day"] == 1
              else f"{i['n']} {names[i['topic_id']]} problems" for i in items if i["day"] == 1]
    return items, spoken


def _post_session(student_id: str, session_id: str) -> None:
    """Slow work (LLM memory extraction, summaries, graph session node) off the call's critical path."""
    try:
        if not db.get_session(session_id):  # guardian deleted the memory right after the call
            return
        transcript = db.get_transcript(session_id)
        memory.write_from_transcript(student_id, session_id, transcript)
        summaries.create_all(student_id, session_id)
        _maths_review(student_id, session_id)
        sess = db.get_session(session_id)
        if not sess:
            return
        conf = db.session_confidence(session_id)
        _g(graph.add_session, student_id, session_id, sess["topic_id"], conf.get("before"), conf.get("after"),
           float(db.session_stats(session_id)["accuracy"]))
    except Exception:
        if db.get_session(session_id) is None:   # deleted mid-way (guardian delete): nothing left to write
            log.info("post-session work skipped: session %s was deleted", session_id)
        else:
            log.exception("post-session work failed for %s", session_id)


def _maths_review(student_id: str, session_id: str) -> None:
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


def end_session(session_id: str, safety_flag: bool = False, wait: bool = False) -> dict:
    sess = _session(session_id)
    sid = sess["student_id"]
    transcript = db.get_transcript(session_id)
    first_close = db.close_session(session_id, "safety_stop" if safety_flag else "ended")
    items, spoken = plan_for(sid, sess["topic_id"] or db.pick_topic(sid))
    if not first_close:  # idempotent: Bolna tool + post-call webhook may both end it
        return {"ok": True, "next_plan": spoken, "already_ended": True}
    if safety_flag or safety.scan(transcript):
        summaries.notify_teacher_safety(sid, session_id)
    db.save_plan(sid, items)
    events.emit(sid, "session_ended", {"session_id": session_id, "plan": spoken, "safety": bool(safety_flag)})
    fut: Future = _bg.submit(_post_session, sid, session_id)
    if wait:
        fut.result(timeout=60)
    return {"ok": True, "next_plan": spoken}
