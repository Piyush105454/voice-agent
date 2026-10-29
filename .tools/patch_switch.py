from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


switch = '''SWITCHING TOPIC IN A CALL (follow the person's mind)
- The moment they ask for another topic (other topic, change, next, I want to learn X, AI engineer, career, coding
  ...), switch for real, immediately:
  1. Say yes in a few words and name the new topic exactly as they said it. Do not offer a different version of it
     (never turn AI engineer into interview English).
  2. Call choose_topic(session_id, mode="coach", topic=<their topic in their words>). If it is a goal (become an AI
     engineer, get a job, crack an exam), also call set_goal(session_id, aim).
  3. Drop the old activity completely: no more practice sentences, no say this, no repeat after me.
  4. Mentor them on the topic ITSELF: ask one question to know their starting point (for AI engineer: student or
     working, any coding yet?), then give real, concrete guidance, for example the roadmap Python, then maths basics
     (linear algebra, probability), then machine learning, then small projects, plus free resources such as
     Google's Machine Learning Crash Course, Andrew Ng's Machine Learning course, or the book Hands-On Machine
     Learning by Aurelien Geron. One idea per turn, then check what they think.
- The language of the call is only how you talk. Speaking English with an English learner does NOT mean every topic
  becomes English practice. Correct their English only if they asked for English practice right now.
- If you are not sure what they want, ask once: Do you want to learn about X itself, or practise speaking about it?

'''
edit("api/prompts/voice_system_prompt.md", [
    ("THE STUDENT LEADS. EVERY CALL MOVES FORWARD", switch + "THE STUDENT LEADS. EVERY CALL MOVES FORWARD"),
])
for f in ("api/prompts/coach_general.md", "api/prompts/coach_english.md", "api/prompts/coach_topic.md"):
    s = Path(f).read_text(encoding="utf-8")
    if "SWITCHING TOPIC" not in s:
        Path(f).write_text(s.rstrip("\n") + "\n\n" + switch.replace("Call choose_topic(session_id, mode=\"coach\", "
                           "topic=<their topic in their words>). If it is a goal (become an AI\n     engineer, get a "
                           "job, crack an exam), also call set_goal(session_id, aim).",
                           "If it is a goal (become an AI engineer, get a job, crack an exam), fill the goal field."),
                           encoding="utf-8")

edit("api/phone.py", [
    ('''            "Open coaching on what the student chose. Diagnose first''',
     '''            "Mentor them on the topic itself (its real knowledge, roadmap and next steps), not on language "
            "practice, unless the topic IS spoken English. Diagnose first'''),
    ('''                                "the better sentence. Near the end ask them to rate their confidence 1-10.")''',
     '''                                "the better sentence. Near the end ask them to rate their confidence 1-10. If they "
                                "ask for another subject or goal, stop English practice and call choose_topic again "
                                "with mode coach and their topic.")'''),
])

# Notes after the call: a topic switch becomes the new direction and the next call starts there
edit("api/coach.py", [
    ('''"practised. If the student asked for something different or a new topic, that wins.''',
     '''"practised. If the student asked for something different or switched topic during the call (e.g. from "
               "English practice to becoming an AI engineer), that new topic becomes goal_in_their_words, the first "
               "of next_topics, the direction and the next_call_opener.'''),
])
print("ok")
