from pathlib import Path
p = Path("api/prompts/voice_system_prompt.md"); s = p.read_text(encoding="utf-8")
start = s.index("HOW YOU SPEAK\n")
end = s.index("TOOLS\n")
new = '''HOW YOU SPEAK
- This is a phone call. SHORT turns: one or two short sentences, at most 20 words, then stop and let them talk.
  Never give a speech. Never add a second question. After a question, stop and wait.
- Speak slowly and simply, one idea per turn, like a patient friendly elder sibling or favourite teacher.
- Always respectful: say aap, never tu or tum. Call the student by name ({first_name}) now and then.
- First call (your memory says so): be extra welcoming. Get to know them a little (what they study, what they
  enjoy, what they dream of becoming) and make them feel this is a safe place to make mistakes.
- If you do not know their name (first_name is empty), ask it politely once and use it after that.

THEIR LANGUAGE, THEIR WAY
- If LANGUAGE above says unknown, the opening line asked it: when they answer, call set_language(session_id,
  language) once. Then speak ONLY that language, and if they switch later, follow them.
- Hindi: simple everyday Hindi written in Devanagari script (for example: ठीक है, आप बहुत अच्छा कर रहे हैं), with
  common English words like college, exam, AI kept as they are. Never Latin-script Hindi for these students.
- Hinglish: a natural Hindi and English mix written in Latin script (for example: Theek hai, aap bahut accha kar
  rahe ho).
- English: simple, clear English with short sentences. Never switch to Hindi unless they do.

LISTEN FIRST, ANSWER WHAT THEY ASK
- If the student asks a question, ANSWER IT FIRST, directly and concretely, in one or two sentences. Then, only if
  needed, one short follow-up question. Never reply to a question with only more questions.
- If their words look unfinished (one or two words like haan, to, main, ek minute), do not start explaining:
  just say a tiny prompt such as हाँ, बोलिए or Go on, and wait.
- If they say you are not listening, talking too much, or too fast: say sorry in three words, then answer their
  last real question in one short sentence.
- Before you advise, reflect back what you heard in a few words so they know you listened.

SAFE FOR THE PHONE VOICE
- No bullet points, markdown, emoji, brackets or symbols, and NO quotation marks of any kind (they break the
  phone voice). To give a model sentence, just say it: Try saying, I will share my update first.
  Say numbers and formulas the way a person would speak them.
- Never say ek second, context, system, tool, server or anything technical. If a tool fails, just continue
  the conversation naturally with what you remember.

'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8")

# Hindi students hear the opening line in Devanagari (the Hindi voice reads it far more naturally)
c = Path("api/coach.py"); t = c.read_text(encoding="utf-8")
reps = {
    '''GREET = {"hi": "Namaste {n}! Main Guru, aapka AI coach.",''': '''GREET = {"hi": "नमस्ते {n}! मैं गुरु, आपका AI कोच।",''',
    '''ASK_IMPROVE = {"hi": "Aaj aap kis cheez mein behtar hona chahenge?",''': '''ASK_IMPROVE = {"hi": "आज आप किस चीज़ में बेहतर होना चाहेंगे?",''',
    '''WELCOME_BACK = {"hi": "Aapse phir baat karke accha laga.",''': '''WELCOME_BACK = {"hi": "आपसे फिर बात करके अच्छा लगा।",''',
    '''FIRST_MEET = {"hi": "Aapse milkar bahut khushi hui.",''': '''FIRST_MEET = {"hi": "आपसे मिलकर बहुत खुशी हुई।",''',
}
for a, b in reps.items():
    assert a in t, a
    t = t.replace(a, b)
old = '''                             "student's language (Hinglish in Latin script unless they chose Hindi or English), "'''
new = '''                             "student's language (Hindi in Devanagari, Hinglish in Latin script, or English), "'''
assert old in t; t = t.replace(old, new)
c.write_text(t, encoding="utf-8")

# Bolna: slower voice, more patience before replying, steadier wording; English agent speaks with an English voice
b = Path("scripts/bolna_sync_agent.py"); u = b.read_text(encoding="utf-8")
old = '''"llm_config": {"provider": "openai", "model": "gpt-5.4-mini", "max_tokens": 150,
                                       "temperature": 1},'''
new = '''"llm_config": {"provider": "openai", "model": "gpt-5.4-mini", "max_tokens": 150,
                                       "temperature": 0.7},'''
assert old in u; u = u.replace(old, new)
old = '''"provider_config": {"voice": "Priya", "voice_id": "priya", "model": "bulbul:v3",
                                            "language": "hi", "speed": 1},'''
new = '''# speed 0.9: students said Guru spoke too fast
                        "provider_config": {"voice": "Priya", "voice_id": "priya", "model": "bulbul:v3",
                                            "language": lang, "speed": 0.9},'''
assert old in u; u = u.replace(old, new)
old = '''"encoding": "linear16", "sampling_rate": 8000, "endpointing": 900},'''
new = '''"encoding": "linear16", "sampling_rate": 8000, "endpointing": 1200},'''
assert old in u; u = u.replace(old, new)
u = u.replace('''# endpointing 900 ms: learners pause mid-sentence; 500 ms cut "I can do this, and I will help"
                    # into fragments that Guru then treated as mistakes''',
              '''# endpointing 1200 ms: learners pause mid-sentence; shorter values cut "I can do this, and I will
                    # help" into fragments and let Guru talk over students who were still thinking''')
b.write_text(u, encoding="utf-8")
print("ok")
