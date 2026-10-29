from pathlib import Path
p = Path("coach.py"); s = p.read_text(encoding="utf-8")
start = s.index('GREET = {"hi"')
end = s.index("def after_call(")
new = '''GREET = {"hi": "Namaste {n}! Main Guru, aapka AI coach.", "en": "Hi {n}! It's Guru, your AI coach.",
         "hi-en": "Hi {n}! Guru bol raha hoon, aapka AI coach."}
ASK_IMPROVE = {"hi": "Aaj aap kis cheez mein behtar hona chahenge?", "en": "What would you like to get better at today?",
               "hi-en": "Aaj kis cheez mein better hona chahoge?"}
WELCOME_BACK = {"hi": "Aapse phir baat karke accha laga.", "en": "Good to talk again.",
                "hi-en": "Phir se baat karke accha laga."}
FIRST_MEET = {"hi": "Aapse milkar bahut khushi hui.", "en": "So nice to meet you.",
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
    first_call = not db.recent_reviews(sid, 1)
    if not db.language_known(sid):
        return (f"Hi {n}! Main Guru hoon, aapka AI coach. " + ("Aapse milkar bahut khushi hui. " if first_call else "")
                + "Aap Hindi, English, ya dono mix mein baat karna pasand karoge?")
    lang = student.get("language") if student.get("language") in GREET else "hi-en"
    if first_call:
        return f"{GREET[lang].format(n=n)} {FIRST_MEET[lang]} {ASK_IMPROVE[lang]}"
    hook = ((db.learner_profile(sid) or {}).get("next_call_opener") or "").strip()
    if hook:
        return f"{GREET[lang].format(n=n)} {hook}"
    return f"{GREET[lang].format(n=n)} {WELCOME_BACK[lang]} {ASK_IMPROVE[lang]}"


'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8")

ph = Path("phone.py"); t = ph.read_text(encoding="utf-8")
old = '''    return {"student_id": student_id, "first_name": st["first_name"], "session_id": session_id or "",'''
new2 = '''    return {"student_id": student_id, "first_name": coach.spoken_name(st["first_name"]), "session_id": session_id or "",'''
assert old in t; ph.write_text(t.replace(old, new2), encoding="utf-8")

m = Path("main.py"); u = m.read_text(encoding="utf-8")
old3 = '''        return {"student_id": "", "first_name": "", "known_caller": "false"}'''
new3 = '''        return {"student_id": "", "first_name": "", "known_caller": "false", "session_id": "",
                "greeting": coach.UNKNOWN_CALLER,
                "memory": "This caller has not signed up yet, so you know nothing about them. Be warm and respectful: "
                          "learn their name, ask what they study or want to get better at, help with one small thing, "
                          "and tell them that signing up on the Guru Line website lets you remember them next time. "
                          "Do not call any tools."}'''
assert old3 in u; u = u.replace(old3, new3)
u = u.replace('''"greeting": f"Namaste {st['first_name']}! Pehle aapke parent ki permission chahiye. Dhanyavaad!",''',
              '''"greeting": f"Namaste {coach.spoken_name(st['first_name'])}! Guru bol raha hoon. Hum baat shuru "
                            "karein, usse pehle aapke parent ki permission chahiye. Dhanyavaad, jaldi milte hain!",''')
m.write_text(u, encoding="utf-8"); print("ok")
