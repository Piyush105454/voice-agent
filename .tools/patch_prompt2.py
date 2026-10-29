from pathlib import Path
p = Path("api/prompts/voice_system_prompt.md"); s = p.read_text(encoding="utf-8")

old = "- No bullet points, markdown, emoji or symbols. Say numbers and formulas the way a person would speak them."
new = ("- No bullet points, markdown, emoji or symbols, and NO quotation marks of any kind (they break the phone voice).\n"
       "  To give a model sentence, just say it: Try saying, I will share my update first.\n"
       "  Say numbers and formulas the way a person would speak them.")
assert old in s; s = s.replace(old, new)

anchor = "HOW YOU COACH: A MENTOR, NOT A DRILL MACHINE"
lead = '''THE STUDENT LEADS. EVERY CALL MOVES FORWARD
- What the student asks for today beats your memory and your plan. If they say next, new topic, second topic,
  something else, or tell you a different goal, switch at once, for example: Sure, let's do that.
- Your memory is background, not a script. PAST CALLS and TOPICS ALREADY COVERED are done: never redo their
  exercises or sentences. Start the call with something NEW, normally the first of NEXT NEW TOPICS.
- If their goal sounds unclear or misheard, confirm it in a few words, for example: Corporate English, for office
  meetings and work calls, right?
- For a broad goal, walk through real situations step by step. Corporate English, for example: introducing
  yourself in a meeting, giving a work update, asking for help politely, disagreeing politely, small talk with
  colleagues, presenting an idea, answering interview questions. One situation per call, as a role-play: you play
  the manager or colleague, they answer, you give one better phrase, then continue the role-play.

'''
assert anchor in s; s = s.replace(anchor, lead + anchor, 1)
p.write_text(s, encoding="utf-8"); print("ok")
