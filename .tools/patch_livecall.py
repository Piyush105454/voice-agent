from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")


# ---- db: a call that never reported its end must not pin the live console forever
edit("api/db.py", [
    ('''def latest_session(student_id: str | None = None) -> dict | None:
    return one(''', '''def close_stale_sessions() -> int:
    """Sessions still "active" long after they could have ended (phone calls are capped at 10 minutes by Bolna; browser
    calls get an hour and a half) are closed: their end webhook never arrived, e.g. an unanswered call."""
    return run("""update sessions set status='ended',
                         ended_at = least(now(), started_at + case when channel='phone' then interval '20 minutes'
                                                                   else interval '90 minutes' end)
                  where ended_at is null
                    and started_at < now() - case when channel='phone' then interval '20 minutes'
                                                  else interval '90 minutes' end""")


def latest_session(student_id: str | None = None) -> dict | None:
    close_stale_sessions()      # otherwise an old never-closed call is shown instead of the latest real one
    return one('''),
])

# ---- voice_router: dial the number that was typed, not only the one saved on the profile
edit("api/voice_router.py", [
    ('''def start_call(student_id: str, provider: str | None = None) -> dict:''',
     '''def normalize_phone(raw: str) -> str:
    """'6261720559' / '+91 62617 20559' / '916261720559' -> '+916261720559'. Anything else is refused."""
    import re
    s = re.sub(r"[\\s\\-().]", "", raw or "")
    if s.startswith("+"):
        num = s
    elif len(s) == 10 and s.isdigit():
        num = "+91" + s
    elif len(s) == 12 and s.startswith("91") and s.isdigit():
        num = "+" + s
    else:
        raise VoiceError(422, "enter a 10-digit mobile number, or a full number like +919876543210")
    if not (num[1:].isdigit() and 8 <= len(num) - 1 <= 15):
        raise VoiceError(422, "that does not look like a valid phone number")
    return num


def start_call(student_id: str, provider: str | None = None, phone: str | None = None) -> dict:'''),
    ('''    mode = provider or settings.voice_provider
    tried: list[str] = []
''', '''    mode = provider or settings.voice_provider
    tried: list[str] = []
    to = normalize_phone(phone) if phone and phone.strip() else st["phone_e164"]   # typed number wins for this call
'''),
    ('''    if mode in ("auto", "bolna") and bolna.enabled() and st["phone_e164"]:''',
     '''    if mode in ("auto", "bolna") and bolna.enabled() and to:'''),
    ('''out = bolna.trigger_call(st["phone_e164"], student_id,''', '''out = bolna.trigger_call(to, student_id,'''),
])

# ---- main: accept phone/name on /voice/call, close stale sessions at startup too
edit("api/main.py", [
    ('''class CallIn(BaseModel):
    student_id: str
    provider: str | None = None   # auto | bolna | sarvam (override)''',
     '''class CallIn(BaseModel):
    student_id: str
    provider: str | None = None   # auto | bolna | sarvam (override)
    phone: str | None = None      # dial this number instead of the one saved on the profile (e.g. a verified test number)
    name: str | None = None       # accepted for the console; the greeting always uses the profile's name'''),
    ('''    return voice_router.start_call(b.student_id, b.provider)''', '''    return voice_router.start_call(b.student_id, b.provider, b.phone)'''),
    ('''    def recover():
        try:''', '''    def recover():
        try:
            db.close_stale_sessions()
        except Exception as e:
            logging.getLogger("bolna").warning("stale session cleanup skipped: %s", e)
        try:'''),
])
print("ok")
