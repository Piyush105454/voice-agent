"""One-off patch: prepare the coach's opening line while the greeting plays (first LLM call is the slowest)."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "api/webcall.py"
s = p.read_text(encoding="utf-8")


def rep(a: str, b: str) -> None:
    global s
    assert a in s, "MISSING: " + a[:80]
    s = s.replace(a, b)


rep("    goal_linked: bool = False\n", "    goal_linked: bool = False\n    prefetch: object = None                       # Future of the opening reply (coach modes)\n")
rep('''        return _speak(c, c.t("greet" if mode == "maths" else f"greet_{mode}", name=c.first_name))''',
    '''        if mode != "maths" and c.prefetch is None:
            # The first model call of a conversation is the slowest (~12 s measured). Prepare the opening line now,
            # while the consent greeting is being played; nothing is stored until the student says yes.
            st_full = {**st, "id": student_id}
            c.system = coach.system_prompt(st_full, mode)
            c.history = coach.opening(st_full, mode)
            c.prefetch = _prefetch_pool.submit(coach.reply, c.system, list(c.history), mode, 0)
        return _speak(c, c.t("greet" if mode == "maths" else f"greet_{mode}", name=c.first_name))''')
rep('''    c.system = coach.system_prompt(st, c.mode)
    c.history = coach.opening(st, c.mode)
    c.state = "coach"
    return _coach_say(c)''', '''    if not c.system:
        c.system = coach.system_prompt(st, c.mode)
        c.history = coach.opening(st, c.mode)
    c.state = "coach"
    first = None
    if c.prefetch is not None:
        try:
            first = c.prefetch.result(timeout=20)
        except Exception as e:
            log.warning("prefetched opening failed: %s", e)
        c.prefetch = None
    return _coach_say(c, first)''')
rep('''def _coach_say(c: Call) -> dict:
    r = coach.reply(c.system, c.history, c.mode, c.turns)''', '''def _coach_say(c: Call, ready: dict | None = None) -> dict:
    r = ready or coach.reply(c.system, c.history, c.mode, c.turns)''')
rep("_calls: dict[str, Call] = {}\n", "_calls: dict[str, Call] = {}\n_prefetch_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix=\"coach-prefetch\")\n")
rep("import threading\n", "import threading\nfrom concurrent.futures import ThreadPoolExecutor\n")
p.write_text(s, encoding="utf-8")
print("patched")
