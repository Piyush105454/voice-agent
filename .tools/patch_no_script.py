"""One-off patch: calls start straight into a natural opening (no recording notice, no 'shall we start?')."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "api/webcall.py"
s = p.read_text(encoding="utf-8")


def rep(a: str, b: str) -> None:
    global s
    assert a in s, "MISSING: " + a[:80]
    s = s.replace(a, b)


# 1) start(): consent is captured once at sign-up, so begin the session immediately
start = s.index("def start(token: str, student_id: str, mode: str = \"coach\") -> dict:")
end = s.index("def transcribe(")
s = s[:start] + '''def start(token: str, student_id: str, mode: str = "coach") -> dict:
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


''' + s[end:]

# 2) coach session begins without waiting for a yes
cb_start = s.index("def _begin_coach(c: Call) -> dict:")
cb_end = s.index("def _coach_say(")
s = s[:cb_start] + '''def _begin_coach(c: Call) -> dict:
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


''' + s[cb_end:]

# 3) the yes/no greeting state is gone
g_start = s.index('    if c.state == "greeting":')
g_end = s.index('    if c.state in ("confidence_before", "confidence_after"):')
s = s[:g_start] + s[g_end:]

# 4) strings: drop the scripted greetings, add the maths opener
s = re.sub(r'\n        "greet": .*?\n(?=        "greet_again")', "\n", s, flags=re.S)
for key in ("greet_again", "decline", "greet_english", "greet_topic", "greet_coach"):
    s = re.sub(r'\n        "' + key + r'": "(?:[^"\\]|\\.)*"(?:\s*\n\s*"(?:[^"\\]|\\.)*")*,', "", s)
rep('''        "no_consent": "Maaf kijiye, pehle aapke parent ki permission chahiye. Bye!",''',
    '''        "no_consent": "Maaf kijiye, pehle sign up karke permission deni hogi. Bye!",
        "topic_open": "Namaste {name}! Aaj hum {topic} practice karenge. 1 se 10 mein, is topic mein kitna confident ho?",''')
rep('''        "no_consent": "Sorry, I need your parent's permission first. Bye!",''',
    '''        "no_consent": "Sorry, you need to sign up and give permission first. Bye!",
        "topic_open": "Hi {name}! Today we'll practise {topic}. From 1 to 10, how confident do you feel about it?",''')
rep('''    state: str = "greeting"           # greeting | confidence_before | question | confidence_after | coach | done''',
    '''    state: str = "new"                # new | confidence_before | question | confidence_after | coach | done''')
# prefetch is no longer needed: the opening is the first thing generated
s = s.replace("    prefetch: object = None                       # Future of the opening reply (coach modes)\n", "")
s = s.replace('_prefetch_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="coach-prefetch")\n', "")
s = s.replace("from concurrent.futures import ThreadPoolExecutor\n", "")
s = s.replace('''def _coach_say(c: Call, ready: dict | None = None) -> dict:
    r = ready or coach.reply(c.system, c.history, c.mode, c.turns)''', '''def _coach_say(c: Call) -> dict:
    r = coach.reply(c.system, c.history, c.mode, c.turns)''')
p.write_text(s, encoding="utf-8")

# coach: the opening instruction no longer assumes a "yes"
c = ROOT / "api/coach.py"
t = c.read_text(encoding="utf-8")
a = '''    return [{"role": "user", "content": "(The student just said yes to start. Greet them by name in one short line "
                                        "and begin the first activity.)"}]'''
assert a in t
t = t.replace(a, '''    return [{"role": "user", "content": "(Call connected: the student pressed Start. Give your opening turn now, "
                                        "exactly as your instructions describe. Do not mention recording or consent.)"}]''')
t = t.replace('"""First user message: tells the model the call has started (the student already agreed to begin)."""',
              '"""First user message: the call is connected; the model opens (consent was given once at sign-up)."""')
c.write_text(t, encoding="utf-8")
print("patched")
