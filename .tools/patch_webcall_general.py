"""One-off patch: 'coach' (open coaching) mode in the web-call engine."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "api/webcall.py"
s = p.read_text(encoding="utf-8")


def rep(a: str, b: str) -> None:
    global s
    assert a in s, "MISSING: " + a[:80]
    s = s.replace(a, b)


rep('''        "greet_topic": "Namaste {name}! Main Guru hoon, aapka AI tutor. Aaj aap koi bhi topic seekh sakte ho. Yeh call "
                       "record hoti hai aur teacher aur parent ke saath share hoti hai. Shuru karein?",
    },''', '''        "greet_topic": "Namaste {name}! Main Guru hoon, aapka AI tutor. Aaj aap koi bhi topic seekh sakte ho. Yeh call "
                       "record hoti hai aur teacher aur parent ke saath share hoti hai. Shuru karein?",
        "greet_coach": "Namaste {name}! Main Guru hoon, aapka AI learning coach. Yeh call aapki padhai ke liye record "
                       "hoti hai aur teacher aur parent ke saath share hoti hai. Shuru karein?",
    },''')
rep('''        "greet_topic": "Hi {name}! I'm Guru, your AI tutor. Today you can learn any topic you like. This call is "
                       "recorded for your learning and shared with your teacher and parent. Shall we start?",
    },''', '''        "greet_topic": "Hi {name}! I'm Guru, your AI tutor. Today you can learn any topic you like. This call is "
                       "recorded for your learning and shared with your teacher and parent. Shall we start?",
        "greet_coach": "Hi {name}! I'm Guru, your AI learning coach. This call is recorded for your learning and "
                       "shared with your teacher and parent. Shall we start?",
    },''')
rep('''    mode: str = "maths"               # maths | english | topic''', '''    mode: str = "coach"               # coach (open, default) | maths | english | topic''')
rep('''    if r.get("language") and r["language"] != c.language:
        # the student chose a language: remember it, and switch this call's voice + speech recognition to it
        db.run("update students set language=%s where id::text=%s", (r["language"], c.student_id))
        c.language = r["language"]
    # the model may repeat the goal field on later turns: only a genuinely new aim creates a goal
    current = db.active_goal(c.student_id, c.mode)''', '''    if r.get("language"):
        # the student chose a language: remember it (not asked again next call) and switch this call's voice + STT
        if r["language"] != c.language or not db.language_known(c.student_id):
            db.remember_language(c.student_id, r["language"], c.session_id)
        c.language = r["language"]
    if r.get("resource"):
        coach.save_resource(c.student_id, c.session_id, r["resource"])
    # the model may repeat the goal field on later turns: only a genuinely new aim creates a goal
    current = db.active_goal(c.student_id, coach.goal_mode(c.mode))''')
p.write_text(s, encoding="utf-8")
print("webcall patched")
