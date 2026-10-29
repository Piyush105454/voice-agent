"""One-off patch: integrate coach modes (english/topic) into api/webcall.py and api/main.py."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = (ROOT / "api/webcall.py").read_text(encoding="utf-8")


def rep(a: str, b: str) -> None:
    global s
    assert a in s, "MISSING: " + a[:80]
    s = s.replace(a, b)


rep("import answers\nimport db\n", "import answers\nimport coach\nimport db\nimport events\n")
rep('''        "ended": "Yeh call khatam ho gayi hai. Bye!",
    },''', '''        "ended": "Yeh call khatam ho gayi hai. Bye!",
        "greet_english": "Hi {name}! I'm Guru, your English speaking coach. This call is recorded for your learning "
                         "and shared with your teacher and parent. Shall we start?",
        "greet_topic": "Namaste {name}! Main Guru hoon, aapka AI tutor. Aaj aap koi bhi topic seekh sakte ho. Yeh call "
                       "record hoti hai aur teacher aur parent ke saath share hoti hai. Shuru karein?",
    },''')
rep('''        "ended": "This call has ended. Bye!",
    },''', '''        "ended": "This call has ended. Bye!",
        "greet_english": "Hi {name}! I'm Guru, your English speaking coach. This call is recorded for your learning "
                         "and shared with your teacher and parent. Shall we start?",
        "greet_topic": "Hi {name}! I'm Guru, your AI tutor. Today you can learn any topic you like. This call is "
                       "recorded for your learning and shared with your teacher and parent. Shall we start?",
    },''')
rep('''    state: str = "greeting"           # greeting | confidence_before | question | confidence_after | done''',
    '''    mode: str = "maths"               # maths | english | topic
    state: str = "greeting"           # greeting | confidence_before | question | confidence_after | coach | done''')
rep('''    pending: list = field(default_factory=list)   # transcript lines before the DB session exists''',
    '''    pending: list = field(default_factory=list)   # transcript lines before the DB session exists
    history: list = field(default_factory=list)   # coach modes: [{"role","content"}] for the LLM
    system: str = ""                              # coach modes: mode prompt + student context (stable per call)
    turns: int = 0''')
rep('''            audio = base64.b64encode(sarvam.tts(text, sarvam.lang_code(c.language))).decode()''',
    '''            audio = base64.b64encode(sarvam.tts(text, _voice_lang(c))).decode()''')
rep('''def start(token: str, student_id: str) -> dict:
    _gc()
    st = db.student(student_id)
    with _calls_lock:
        c = _calls.get(token)
        if c is None or c.state == "done":
            c = Call(token=token, student_id=student_id, first_name=st["first_name"], language=st["language"])
            _calls[token] = c
    with c.lock:
        c.touched = time.time()
        if not db.has_consent(student_id):
            c.state = "done"
            return _speak(c, c.t("no_consent"))
        return _speak(c, c.t("greet", name=c.first_name))''',
    '''def _voice_lang(c: Call) -> str:
    """English-speaking practice is spoken/heard as English; other modes follow the student's language."""
    return "en-IN" if c.mode == "english" else sarvam.lang_code(c.language)


def start(token: str, student_id: str, mode: str = "maths") -> dict:
    _gc()
    if mode not in ("maths", *coach.MODES):
        raise service.ServiceError(422, "mode must be maths, english or topic")
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
        return _speak(c, c.t("greet" if mode == "maths" else f"greet_{mode}", name=c.first_name))''')
rep('''    keyterms = ["minus", "plus", "x", "Guru", c.first_name, "seventeen", "twenty", "equal"]
    try:
        out = sarvam.stt(audio, filename, content_type, sarvam.lang_code(c.language), keyterms)''',
    '''    keyterms = ["Guru", c.first_name] + (["minus", "plus", "x", "seventeen", "twenty", "equal"]
                                         if c.mode == "maths" else [])
    try:
        out = sarvam.stt(audio, filename, content_type, _voice_lang(c), keyterms)''')
rep('''    with c.lock:
        if c.session_id and c.state != "done":
            c.state = "done"
            service.end_session(c.session_id)
        c.state = "done"
    return {"ok": True}''', '''    with c.lock:
        if c.session_id and c.state != "done":
            c.state = "done"
            if c.mode == "maths":
                service.end_session(c.session_id)
            else:
                coach.finish(c.session_id)
        c.state = "done"
    return {"ok": True}''')
rep('''def _finish(c: Call) -> dict:''', '''def _begin_coach(c: Call) -> dict:
    """Coach modes: open a session (consent re-checked), then let the model greet and start the first activity."""
    if not db.has_consent(c.student_id):
        raise service.ServiceError(403, "no consent")
    st = {**db.student(c.student_id), "id": c.student_id}
    goal = db.active_goal(c.student_id, c.mode)
    sess = db.create_session(c.student_id, f"web-{c.token[-24:]}-{int(time.time())}", "web", None, c.mode,
                             goal["id"] if goal else None)
    c.session_id = sess["id"]
    for speaker, line in c.pending:
        db.append_transcript(c.session_id, speaker, line)
    c.pending.clear()
    events.emit(c.student_id, "session_started", {"session_id": c.session_id, "mode": c.mode, "channel": "web"})
    c.system = coach.system_prompt(st, c.mode)
    c.history = coach.opening(st, c.mode)
    c.state = "coach"
    return _coach_say(c)


def _coach_say(c: Call) -> dict:
    r = coach.reply(c.system, c.history, c.mode, c.turns)
    c.turns += 1
    c.history.append({"role": "assistant", "content": r["say"]})
    if r.get("goal"):
        coach.set_goal(c.student_id, c.mode, r["goal"], c.session_id)
    events.emit(c.student_id, "coach_turn", {"session_id": c.session_id, "mode": c.mode, "turn": c.turns})
    if r["end_call"]:
        c.state = "done"
        out = _speak(c, r["say"])
        coach.finish(c.session_id)
        return out
    return _speak(c, r["say"])


def _finish(c: Call) -> dict:''')
rep('''    if text and safety.scan(text):
        if c.session_id:
            service.end_session(c.session_id, safety_flag=True)''', '''    if text and safety.scan(text):
        if c.session_id and c.mode != "maths":
            coach.finish(c.session_id, safety_flag=True)
        elif c.session_id:
            service.end_session(c.session_id, safety_flag=True)''')
rep('''        try:
            _begin_session(c)
        except service.ServiceError as e:''', '''        try:
            if c.mode != "maths":
                return _begin_coach(c)
            _begin_session(c)
        except service.ServiceError as e:''')
rep('''    if c.state == "question":
        r = service.submit_answer(c.session_id, c.question["id"], text)''', '''    if c.state == "coach":
        c.history.append({"role": "user", "content": text})
        return _coach_say(c)

    if c.state == "question":
        r = service.submit_answer(c.session_id, c.question["id"], text)''')
(ROOT / "api/webcall.py").write_text(s, encoding="utf-8")

s = (ROOT / "api/main.py").read_text(encoding="utf-8")
rep('''class TokenIn(BaseModel):
    token: str
''', '''class TokenIn(BaseModel):
    token: str


class StartIn(TokenIn):
    mode: str = "maths"   # maths | english | topic
''')
rep('''@app.post("/web-call/start")
def web_start(b: TokenIn):
    student_id = voice_router.read_token(b.token)
    out = webcall.start(b.token, student_id)''', '''@app.post("/web-call/start")
def web_start(b: StartIn):
    student_id = voice_router.read_token(b.token)
    out = webcall.start(b.token, student_id, b.mode)''')
(ROOT / "api/main.py").write_text(s, encoding="utf-8")
print("patched")
