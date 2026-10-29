"""Scripted "Replay Rahul session" for the live demo (works with no phone line).
Runs through the real tutor core (service.*): every grade, hint, mastery and misconception update is real;
only the student's answers are scripted. Paced with delays so the dashboard animates."""
from __future__ import annotations

import threading
import time

import db
import service

RAHUL = "11111111-1111-4111-8111-111111111111"
# What the student does on each question: tagged wrong -> guided fix, or straight correct.
SCRIPT = [
    ["wrong_tagged", "correct"],   # e.g. x + 5 = 12 -> "17" (adds instead of inverse) -> hint -> "7"
    ["correct"],                   # uses the inverse unaided
    ["dont_know", "correct"],      # unsure on a harder one -> one nudge -> solves it
]
CONF_BEFORE, CONF_AFTER = 3, 6
_running: dict[str, bool] = {}


def _spoken(n: str) -> str:
    return f"minus {n[1:]}" if n.startswith("-") else n


def _answer(kind: str, q: dict) -> str:
    if kind == "correct":
        return f"toh {_spoken(q['answer'])}"
    if kind == "dont_know":
        return "pata nahi, thoda confuse hoon"
    wam = q["wrong_answer_map"] or {}
    wrong = next((k for k, v in wam.items() if v == "adds_instead_of_inverse"), None) or next(iter(wam), "0")
    return _spoken(wrong)


def _line(session_id: str, speaker: str, text: str, pause: float) -> None:
    db.append_transcript(session_id, speaker, text)
    if pause:
        time.sleep(pause)


def _run(student_id: str, session_id: str, first_q: dict, delay: float) -> None:
    name = db.student(student_id)["first_name"]
    say = lambda who, text, k=1.0: _line(session_id, who, text, delay * k)  # noqa: E731
    try:
        say("Guru", f"Namaste {name}! Main Guru hoon, aapka AI tutor. Yeh call record hoti hai aur aapke "
                    "teacher aur parent ke saath share hoti hai. Shuru karein?", 0.6)
        say(name, "Haan, chalo.", 0.5)
        topic = db.topic_names()[db.get_session(session_id)["topic_id"]]
        say("Guru", f"Aaj hum {topic} karenge. 1 se 10 mein, kitna confident feel karte ho?", 0.6)
        say(name, str(CONF_BEFORE), 0.3)
        service.log_confidence(session_id, None, "before", CONF_BEFORE)

        q = first_q
        for qi, steps in enumerate(SCRIPT):
            if not q:
                break
            say("Guru", ("Pehla sawaal: " if qi == 0 else "") + q["text"], 0.8)
            full = db.get_question(q["id"])
            for kind in steps:
                ans = _answer(kind, full)
                say(name, ans, 0.2)
                r = service.submit_answer(session_id, q["id"], ans)
                if r["action"] == "praise_next":
                    say("Guru", "Shabaash, tumne sahi step lagaya!", 0.6)
                    q = r["next_question"]
                    break
                say("Guru", r["hint_text"], 1.0)
            else:
                q = None if r["action"] != "reveal" else r["next_question"]

        say("Guru", "Ab is topic mein kitna confident ho, 1 se 10 mein?", 0.5)
        say(name, str(CONF_AFTER), 0.3)
        service.log_confidence(session_id, None, "after", CONF_AFTER)
        end = service.end_session(session_id)
        say("Guru", f"Bahut accha {name}! Kal ki practice: {', '.join(end['next_plan'])}. Bye!", 0)
    finally:
        _running.pop(student_id, None)


def replay(student_id: str = RAHUL, delay: float = 2.0, wait: bool = False) -> dict:
    if _running.get(student_id):
        raise service.ServiceError(409, "a replay is already running for this student")
    _running[student_id] = True
    try:
        ctx = service.get_context(student_id, call_id=f"replay-{int(time.time())}", channel="simulator")
    except Exception:
        _running.pop(student_id, None)
        raise
    t = threading.Thread(target=_run, args=(student_id, ctx["session_id"], ctx["question"], delay), daemon=True)
    t.start()
    if wait:
        t.join()
    return {"session_id": ctx["session_id"], "topic": ctx["topic"], "student_id": student_id}
