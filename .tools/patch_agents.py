from pathlib import Path
import re

# --- sync script: two agents (Hindi/Hinglish ears, English ears), calmer turn-taking, neutral fillers
p = Path("scripts/bolna_sync_agent.py"); s = p.read_text(encoding="utf-8")
s = s.replace('AGENT_NAME = "Guru Line tutor"', 'AGENT_NAME = "Guru Line tutor"\n'
              '# one agent per "ear": Sarvam STT set to Hindi writes English speech as broken Devanagari fragments,\n'
              '# so students who chose English get an agent whose transcriber listens in English.\n'
              'AGENTS = {"hi": ("BOLNA_AGENT_ID", "bolna_agent_id", ""), "en": ("BOLNA_AGENT_ID_EN", "bolna_agent_id_en", " (English)")}')
s = s.replace("def payload() -> dict:", "def payload(lang: str = \"hi\") -> dict:")
s = s.replace('"agent_name": AGENT_NAME,', '"agent_name": AGENT_NAME + AGENTS[lang][2],')
old_tr = '''"transcriber": {"provider": "sarvam", "model": "saaras:v4", "language": "hi", "stream": True,
                                    "encoding": "linear16", "sampling_rate": 8000, "endpointing": 500},'''
assert old_tr in s, "transcriber"
s = s.replace(old_tr, '''# endpointing 900 ms: learners pause mid-sentence; 500 ms cut "I can do this, and I will help"
                    # into fragments that Guru then treated as mistakes
                    "transcriber": {"provider": "sarvam", "model": "saaras:v4", "language": lang, "stream": True,
                                    "encoding": "linear16", "sampling_rate": 8000, "endpointing": 900},''')
s = s.replace('''"number_of_words_for_interruption": 2,   # coughs/"haan" don't cut Guru off''',
              '''"number_of_words_for_interruption": 2,   # coughs/"haan" don't cut Guru off
                                "incremental_delay": 700,                # wait a little longer before replying''')
old_main = s[s.index("def save_agent_id"):s.index('if __name__ == "__main__":')]
new_main = '''def save_agent_id(env_key: str, agent_id: str) -> None:
    env = ROOT / ".env"
    s = env.read_text(encoding="utf-8")
    if re.search(rf"(?m)^{env_key}=", s):
        s = re.sub(rf"(?m)^{env_key}=.*$", f"{env_key}={agent_id}", s)
    else:
        s = s.rstrip("\\n") + f"\\n{env_key}={agent_id}\\n"
    env.write_text(s, encoding="utf-8")


def main() -> None:
    base = settings.public_base_url
    if not base.startswith("https://") or "yourdomain" in base:
        sys.exit("PUBLIC_BASE_URL must be your public https URL (run scripts/dev_tunnel.py or set it in .env)")
    headers = {"Authorization": f"Bearer {settings.bolna_api_key}"}
    for lang, (env_key, attr, _) in AGENTS.items():
        body = payload(lang)
        if "--dry-run" in sys.argv:
            print(json.dumps(body, indent=2, ensure_ascii=False))
            continue
        agent_id = getattr(settings, attr)
        if agent_id:
            r = httpx.put(f"{API}/v2/agent/{agent_id}", headers=headers, json=body, timeout=30)
            action = "updated"
        else:
            r = httpx.post(f"{API}/v2/agent", headers=headers, json=body, timeout=30)
            action = "created"
        if r.status_code >= 400:
            sys.exit(f"Bolna {r.status_code} ({lang}): {r.text[:500]}")
        out = r.json()
        if action == "created":
            agent_id = out["agent_id"]
            save_agent_id(env_key, agent_id)
            setattr(settings, attr, agent_id)
        print(f"agent {action} [{lang}]: {agent_id} -> tools at {base}/bolna/*")


'''
s = s.replace(old_main, new_main)
p.write_text(s, encoding="utf-8")

# --- settings + routing by the student's language
c = Path("api/config.py"); t = c.read_text(encoding="utf-8")
t = t.replace('    bolna_agent_id: str = ""\n', '    bolna_agent_id: str = ""\n    bolna_agent_id_en: str = ""      # same agent, English speech recognition\n')
c.write_text(t, encoding="utf-8")

b = Path("api/bolna.py"); u = b.read_text(encoding="utf-8")
old = '''def trigger_call(phone_e164: str, student_id: str, extra: dict | None = None) -> dict:
    body = {"agent_id": settings.bolna_agent_id, "recipient_phone_number": phone_e164,'''
new = '''def agent_for(language: str | None) -> str:
    """English speakers get the agent that listens in English (the Hindi transcriber breaks English speech)."""
    return settings.bolna_agent_id_en if language == "en" and settings.bolna_agent_id_en else settings.bolna_agent_id


def trigger_call(phone_e164: str, student_id: str, extra: dict | None = None, language: str | None = None) -> dict:
    body = {"agent_id": agent_for(language), "recipient_phone_number": phone_e164,'''
assert old in u; u = u.replace(old, new)
# neutral fillers: Bolna speaks these before a tool runs, in any language the call is in
for a, b2 in (('"Theek hai."', '"Okay."'), ('"Chaliye shuru karte hain..."', '"Okay."'),
              ('"Bahut accha goal hai..."', '"Great goal."'), ('"Hmm, dekhte hain..."', '"Hmm."')):
    u = u.replace(a, b2)
b.write_text(u, encoding="utf-8")

v = Path("api/voice_router.py"); w = v.read_text(encoding="utf-8")
old = '''out = bolna.trigger_call(st["phone_e164"], student_id, phone.call_variables(student_id, sess["id"]))'''
new = '''out = bolna.trigger_call(st["phone_e164"], student_id, phone.call_variables(student_id, sess["id"]),
                                         st.get("language") if db.language_known(student_id) else None)'''
assert old in w; v.write_text(w.replace(old, new), encoding="utf-8")

# webhook: executions of the English agent are ours too
r = Path("api/bolna.py"); x = r.read_text(encoding="utf-8")
old = '''    r = httpx.get(f"{API}/v2/agent/{settings.bolna_agent_id}/executions",
                  headers={"Authorization": f"Bearer {settings.bolna_api_key}"},
                  params={"page_size": limit}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return (d.get("data") if isinstance(d, dict) else d) or []'''
new = '''    out: list[dict] = []
    for agent in filter(None, {settings.bolna_agent_id, settings.bolna_agent_id_en}):
        r = httpx.get(f"{API}/v2/agent/{agent}/executions",
                      headers={"Authorization": f"Bearer {settings.bolna_api_key}"},
                      params={"page_size": limit}, timeout=30)
        r.raise_for_status()
        d = r.json()
        out += (d.get("data") if isinstance(d, dict) else d) or []
    return sorted(out, key=lambda e: str(e.get("created_at") or ""), reverse=True)'''
assert old in x; r.write_text(x.replace(old, new), encoding="utf-8")
print("ok")
