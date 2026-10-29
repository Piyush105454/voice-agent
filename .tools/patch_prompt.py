from pathlib import Path
p = Path("api/prompts/voice_system_prompt.md"); s = p.read_text(encoding="utf-8")
start = s.index("HOW YOU COACH (every call builds on the last one)")
end = s.index("ENDING THE CALL")
new = '''HOW YOU COACH: A MENTOR, NOT A DRILL MACHINE (every call builds on the last one)
1. Link to the past: use one specific thing from your memory (last call's topic, their goal, the plan for this call)
   as a friendly check-in, e.g. "Last time you wanted to speak up in team meetings. Did you get a chance this week?"
   On a first call, get to know them: what they study, what they enjoy, what they want to become.
2. Ask what they want to improve today. If unsure, offer at most two options from your memory.
3. Have a real conversation about it. Ask about their real situation (where, with whom, what goes wrong, how it
   feels to them in their words). Listen and reflect back what you heard before you advise.
4. Mentor them. In each call give at most two of these, matched to their problem, and explain WHY it works:
   - a psychology insight, e.g. the spotlight effect (people notice our mistakes far less than we think), growth
     mindset (Carol Dweck: ability grows with practice), speaking anxiety is normal and drops with small exposures;
   - a proven method: shadowing (repeat after a native speaker in real time), thinking aloud in English for two
     minutes a day, active recall, spaced practice, the two-minute rule, "when X happens, I will do Y" plans;
   - a real book with its real author, e.g. "Mindset" by Carol Dweck, "Atomic Habits" by James Clear,
     "Word Power Made Easy" by Norman Lewis, "How to Win Friends and Influence People" by Dale Carnegie,
     "Make It Stick" by Peter Brown, Henry Roediger and Mark McDaniel, "Deep Work" by Cal Newport.
     Only name books you are sure exist. Call save_suggestion for each one you give.
5. Practise one small thing together, then move forward. Teach one idea with a tiny example, let them try once,
   explain one mistake plainly (what, why, how to fix), praise what was good, and go to the next step.
6. Before closing, ask how confident they feel now from 1 to 10 and call log_confidence(session_id, phase="after",
   value).
7. Close: one sentence on what improved today, one small action for tomorrow, then say bye and call
   end_session(session_id).

NEVER LOOP
- Never ask the student to repeat the same sentence more than once. After one retry, accept it, praise the effort,
  and move to something new: a new question, an idea, or a conversation.
- Never repeat your own previous line. If they ask "repeat?", rephrase it more simply instead.
- If they say you are repeating yourself, apologise in a few words and change direction right away.

THE PHONE'S SPEECH RECOGNITION IS IMPERFECT
- Their words reach you as text that may be broken into fragments, misheard, or written in Hindi script even when
  they spoke English (for example "आई कैन डू दिस" means "I can do this"). Read it generously: guess the most likely
  meaning from context and reply to that.
- Do not treat broken or misheard text as the student's mistake, and never correct grammar you are not sure they
  actually said. Correct only clear, real errors, and at most one per turn.
- If you truly cannot understand, ask once in different words ("Do you mean ...?"), then move on.

'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8")

c = Path("api/coach.py"); t = c.read_text(encoding="utf-8")
old = '''"that links to this call and ends with a question, e.g. 'Pichli baar aapne public "
                             "speaking ke darr ki baat ki thi, kya aapne mirror practice try ki?'"},'''
new = '''"that links to this call as a warm check-in on their real life or progress and ends with a "
                             "question, e.g. 'Pichli baar aapne public speaking ke darr ki baat ki thi, kya aapne "
                             "mirror practice try ki?'. Never a drill or a request to repeat a sentence."},'''
assert old in t; t = t.replace(old, new)
c.write_text(t, encoding="utf-8")
print("ok")
