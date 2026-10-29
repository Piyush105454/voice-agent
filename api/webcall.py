"""Sarvam browser call: the fallback voice channel when Bolna is out of credit.
Browser records one utterance -> Sarvam STT -> this state machine (same tutor core as the Bolna tools)
-> Sarvam TTS -> browser plays it. Deterministic call flow mirroring the Bolna prompt (agent.md §4.2),
so there is no LLM on the critical path. If Sarvam TTS/STT fails, the reply text is still returned
and the page falls back to the browser's own speech engine / a text box."""
from __future__ import annotations

import base64
import logging
import threading
import time
from dataclasses import dataclass, field

import answers
import coach
import db
import events
import safety
import sarvam
import service

log = logging.getLogger("webcall")
MAX_QUESTIONS = 3
IDLE_TTL_S = 2 * 3600

L = {
    "hi": {
        "no_consent": "Maaf kijiye, pehle sign up karke permission deni hogi. Bye!",
        "topic_open": "Namaste {name}! Aaj hum {topic} practice karenge. 1 se 10 mein, is topic mein kitna confident ho?",
        "conf_again": "1 se 10 ke beech ek number boliye.",
        "first_q": "Theek hai. Pehla sawaal: {q}",
        "next_q": "Agla sawaal: {q}",
        "praise": ["Bahut accha, tumne sahi step lagaya!", "Shabaash, ekdum sahi!", "Wah, steps se socha, bahut accha!"],
        "your_turn": "Ab aap batao, kya aayega?",
        "repeat": "Main phir se poochta hoon: {q}",
        "didnt_hear": "Mujhe sunai nahi diya. Kya aap dobara bol sakte ho?",
        "conf_after": "Ab is topic mein kitna confident feel karte ho, 1 se 10 mein?",
        "close": "Shabaash {name}! Aaj aapne {n} sawaal sahi kiye. Kal ki practice: {plan}. Bye, take care!",
        "close_none": "Bahut accha try kiya {name}! Kal ki practice: {plan}. Bye, take care!",
        "ended": "Yeh call khatam ho gayi hai. Bye!",
    },
    "en": {
        "no_consent": "Sorry, you need to sign up and give permission first. Bye!",
        "topic_open": "Hi {name}! Today we'll practise {topic}. From 1 to 10, how confident do you feel about it?",
        "conf_again": "Please say a number between 1 and 10.",
        "first_q": "Okay. First question: {q}",
        "next_q": "Next question: {q}",
        "praise": ["Great, you used the right step!", "Well done, exactly right!", "Nice, you thought it through step by step!"],
        "your_turn": "Now you tell me, what do you get?",
        "repeat": "Let me ask again: {q}",
        "didnt_hear": "I couldn't hear that. Could you say it again?",
        "conf_after": "Now how confident do you feel about this topic, from 1 to 10?",
        "close": "Well done {name}! You got {n} questions right today. Tomorrow's practice: {plan}. Bye, take care!",
        "close_none": "Great effort {name}! Tomorrow's practice: {plan}. Bye, take care!",
        "ended": "This call has ended. Bye!",
    },
}


@dataclass
class Call:
    token: str
    student_id: str
    first_name: str
    language: str
    mode: str = "coach"               # coach (open, default) | maths | english | topic
    state: str = "new"                # new | confidence_before | question | confidence_after | coach | done
    session_id: str | None = None
    topic: str | None = None
    question: dict | None = None
    asked: int = 0
    correct: int = 0
    silences: int = 0
    pending: list = field(default_factory=list)   # transcript lines before the DB session exists
    history: list = field(default_factory=list)   # coach modes: [{"role","content"}] for the LLM
    system: str = ""                              # coach modes: mode prompt + student context (stable per call)
    turns: int = 0
    goal_linked: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    touched: float = field(default_factory=time.time)

    @property
    def lang(self) -> str:
        return "en" if self.language == "en" else "hi"

    def t(self, key: str, **kw) -> str:
        return L[self.lang][key].format(**kw)


_calls: dict[str, Call] = {}
_calls_lock = threading.Lock()


def _gc() -> None:
    cutoff = time.time() - IDLE_TTL_S
    with _calls_lock:
        for k in [k for k, c in _calls.items() if c.touched < cutoff]:
            _calls.pop(k, None)


def _log(c: Call, speaker: str, text: str) -> None:
    if not text:
        return
    if c.session_id:
        db.append_transcript(c.session_id, speaker, text)
    else:
        c.pending.append((speaker, text))


def _speak(c: Call, text: str) -> dict:
    """Reply payload. Audio is best-effort: on any Sarvam error the browser speaks the text itself."""
    _log(c, "Guru", text)
    audio, parts, tts_error = None, [], None
    t0 = time.perf_counter()
    if sarvam.enabled():
        try:
            parts = [base64.b64encode(a).decode() for a in sarvam.tts_parts(text, _voice_lang(c))]
            audio = parts[0]
        except Exception as e:
            tts_error = "out_of_credit" if getattr(e, "out_of_credit", False) else str(e)[:120]
            log.warning("sarvam tts failed: %s", e)
    # audio_parts: one clip per sentence, play in order. audio_b64 kept for older clients (first clip only).
    return {"reply_text": text, "audio_b64": audio, "audio_parts": parts, "audio_mime": sarvam.TTS_MIME if audio else None,
            "tts_error": tts_error, "state": c.state, "done": c.state == "done", "session_id": c.session_id,
            "topic": c.topic, "question": c.question, "timing": {"tts_s": round(time.perf_counter() - t0, 2)}}


def _voice_lang(c: Call) -> str:
    """English-speaking practice is spoken/heard as English; other modes follow the student's language."""
    return "en-IN" if c.mode == "english" else sarvam.lang_code(c.language)


def start(token: str, student_id: str, mode: str = "coach") -> dict:
    """The student pressed Start: no scripted notice, no "shall we start?". Consent was agreed once at sign-up
    (checked here); the call opens straight into Guru's own greeting (coach) or today's topic (maths)."""
    _gc()
    if mode not in ("maths", *coach.MODES):
        raise service.ServiceError(422, "mode must be coach, maths, english or topic")
    st = db.student(student_id)
    with _calls_lock:
        c = _calls.get(token)
        if c is None or c.state == "done" or c.mode != mode:
            c = Call(token=token, student_id=student_id, first_name=st["first_name"], language=st["language"],
                     mode=mode)
            _calls[token] = c
    with c.lock:
        c.touched = time.time()
        if not db.has_consent(student_id):
            c.state = "done"
            return _speak(c, c.t("no_consent"))
        if c.session_id:                       # start() called twice for the same call: don't open a second session
            return _speak(c, c.history[-1]["content"] if c.history else c.t("didnt_hear"))
        if mode == "maths":
            _begin_session(c)
            c.state = "confidence_before"
            return _speak(c, c.t("topic_open", name=c.first_name, topic=c.topic))
        return _begin_coach(c)


def transcribe(c: Call, audio: bytes, filename: str, content_type: str) -> tuple[str, str | None]:
    keyterms = ["Guru", c.first_name] + (["minus", "plus", "x", "seventeen", "twenty", "equal"]
                                         if c.mode == "maths" else [])
    try:
        # trim silence + split at pauses + MP3 + parallel; coach modes get Latin-script output (translit)
        out = sarvam.stt_fast(audio, filename, content_type, _voice_lang(c), keyterms,
                              mode=None if c.mode == "maths" else "translit")
        return out["transcript"], None
    except Exception as e:
        log.warning("sarvam stt failed: %s", e)
        return "", "out_of_credit" if getattr(e, "out_of_credit", False) else str(e)[:120]


def turn(token: str, text: str | None = None, audio: bytes | None = None, filename: str = "audio.webm",
         content_type: str = "audio/webm") -> dict:
    c = _calls.get(token)
    if c is None:
        raise service.ServiceError(404, "call not started (or the server restarted); reload the page")
    with c.lock:
        c.touched = time.time()
        stt_error = None
        t0 = time.perf_counter()
        if audio:
            text, stt_error = transcribe(c, audio, filename, content_type)
        stt_s = time.perf_counter() - t0
        text = (text or "").strip()
        _log(c, "Student", text)
        out = _step(c, text)
        total = time.perf_counter() - t0
        out["timing"] = {"stt_s": round(stt_s, 2), "tts_s": out["timing"]["tts_s"],
                         "logic_s": round(total - stt_s - out["timing"]["tts_s"], 2), "total_s": round(total, 2)}
        log.info("web-call turn %s state=%s %s", c.token[-6:], c.state, out["timing"])
        out["user_text"] = text
        out["stt_error"] = stt_error
        return out


def hang_up(token: str) -> dict:
    c = _calls.get(token)
    if not c:
        return {"ok": True}
    with c.lock:
        if c.session_id and c.state != "done":
            c.state = "done"
            if c.mode == "maths":
                service.end_session(c.session_id)
            else:
                coach.finish(c.session_id)
        c.state = "done"
    return {"ok": True}


def _begin_session(c: Call) -> None:
    ctx = service.get_context(c.student_id, call_id=f"web-{c.token[-24:]}-{int(time.time())}", channel="web")
    c.session_id, c.topic, c.question = ctx["session_id"], ctx["topic"], ctx["question"]
    for speaker, line in c.pending:
        db.append_transcript(c.session_id, speaker, line)
    c.pending.clear()


def _begin_coach(c: Call) -> dict:
    """Coach modes: open a session and let Guru speak first (greeting, language if unknown, memory, today's need)."""
    st = {**db.student(c.student_id), "id": c.student_id}
    goal = db.active_goal(c.student_id, coach.goal_mode(c.mode))
    sess = db.create_session(c.student_id, f"web-{c.token[-24:]}-{int(time.time())}", "web", None, c.mode,
                             goal["id"] if goal else None)
    c.session_id = sess["id"]
    events.emit(c.student_id, "session_started", {"session_id": c.session_id, "mode": c.mode, "channel": "web"})
    c.system = coach.system_prompt(st, c.mode)
    c.history = coach.opening(st, c.mode)
    c.state = "coach"
    return _coach_say(c)


def _coach_say(c: Call) -> dict:
    r = coach.reply(c.system, c.history, c.mode, c.turns)
    c.turns += 1
    c.history.append({"role": "assistant", "content": r["say"]})
    if r.get("language"):
        # the student chose a language: remember it (not asked again next call) and switch this call's voice + STT
        if r["language"] != c.language or not db.language_known(c.student_id):
            db.remember_language(c.student_id, r["language"], c.session_id)
        c.language = r["language"]
    if r.get("resource"):
        coach.save_resource(c.student_id, c.session_id, r["resource"])
    # the model may repeat the goal field on later turns: only a genuinely new aim creates a goal
    current = db.active_goal(c.student_id, coach.goal_mode(c.mode))
    if r.get("goal") and (not current or current["aim"].strip().lower() != r["goal"].strip().lower()):
        coach.set_goal(c.student_id, c.mode, r["goal"], c.session_id)
    elif current and not c.goal_linked:
        db.set_session_goal(c.session_id, current["id"])
        c.goal_linked = True
    events.emit(c.student_id, "coach_turn", {"session_id": c.session_id, "mode": c.mode, "turn": c.turns})
    if r["end_call"]:
        c.state = "done"
        out = _speak(c, r["say"])
        coach.finish(c.session_id)
        return out
    return _speak(c, r["say"])


def _finish(c: Call) -> dict:
    end = service.end_session(c.session_id)
    c.state = "done"
    plan = ", ".join(end.get("next_plan") or []) or "thodi si revision"
    key = "close" if c.correct else "close_none"
    return _speak(c, c.t(key, name=c.first_name, n=c.correct, plan=plan))


def _ask_next(c: Call, nq: dict | None, prefix: str) -> dict:
    if nq is None or c.asked >= MAX_QUESTIONS:
        c.state, c.question = "confidence_after", None
        return _speak(c, f"{prefix} {c.t('conf_after')}".strip())
    c.question = nq
    c.asked += 1
    return _speak(c, f"{prefix} {c.t('next_q', q=nq['text'])}".strip())


def _step(c: Call, text: str) -> dict:
    if c.state == "done":
        return _speak(c, c.t("ended"))

    if text and safety.scan(text):
        if c.session_id and c.mode != "maths":
            coach.finish(c.session_id, safety_flag=True)
        elif c.session_id:
            service.end_session(c.session_id, safety_flag=True)
        else:
            from summaries import notify_teacher_safety
            notify_teacher_safety(c.student_id, None)
        c.state = "done"
        return _speak(c, safety.reply(c.language))

    if not text:
        c.silences += 1
        if c.state == "question" and c.question:
            if c.silences == 1:
                return _speak(c, c.t("repeat", q=c.question["text"]))
            text = "pata nahi"  # second silence on a question -> treat as "don't know" -> hint ladder
        else:
            return _speak(c, c.t("didnt_hear"))
    c.silences = 0

    if c.state in ("confidence_before", "confidence_after"):
        v = answers.confidence_value(text)
        if v is None:
            return _speak(c, c.t("conf_again"))
        phase = "before" if c.state == "confidence_before" else "after"
        service.log_confidence(c.session_id, None, phase, v)
        if phase == "after":
            return _finish(c)
        if not c.question:
            c.state = "confidence_after"
            return _speak(c, c.t("conf_after"))
        c.state, c.asked = "question", 1
        return _speak(c, c.t("first_q", q=c.question["text"]))

    if c.state == "coach":
        c.history.append({"role": "user", "content": text})
        return _coach_say(c)

    if c.state == "question":
        r = service.submit_answer(c.session_id, c.question["id"], text)
        if r["action"] == "safety_stop":
            c.state = "done"
            return _speak(c, r["say"])
        if r["action"] == "praise_next":
            c.correct += 1
            praise = L[c.lang]["praise"][(c.correct - 1) % len(L[c.lang]["praise"])]
            return _ask_next(c, r["next_question"], praise)
        if r["action"] == "reveal":
            return _ask_next(c, r["next_question"], r["hint_text"])
        suffix = f" {c.t('your_turn')}" if r["action"] == "explain_step" else ""
        return _speak(c, r["hint_text"] + suffix)

    return _speak(c, c.t("didnt_hear"))
