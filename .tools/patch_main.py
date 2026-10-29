from pathlib import Path
p = Path("main.py"); s = p.read_text(encoding="utf-8")

# webhook -> phone.handle_webhook (binds calls by student, never loses a call, review + profile once)
old = s[s.index('@app.post("/bolna/webhook"'):s.index("def phone_transcript(")]
new = '''@app.post("/bolna/webhook", dependencies=[Depends(verify_webhook)])
def bolna_post_call(payload: dict):
    """Post-call webhook: sent on every status change (same id repeated). Store the full transcript and
    close the session if the agent never called end_session. Idempotent."""
    return phone.handle_webhook(payload, phone_transcript)


@app.post("/bolna/sync", dependencies=[Depends(verify_admin)])
def bolna_sync(limit: int = 20):
    """Recover calls whose webhook never arrived (tunnel down etc.) from Bolna's call history."""
    return phone.sync_recent_calls(phone_transcript, limit)


'''
s = s.replace(old, new)

# inbound calls get the same greeting + memory variables (and their session) as outbound calls
old2 = '''    return {"student_id": st["id"], "first_name": st["first_name"], "language": st["language"],
            "known_caller": "true"}'''
new2 = '''    if not db.has_consent(st["id"]):
        return {"student_id": st["id"], "first_name": st["first_name"], "known_caller": "true", "session_id": "",
                "greeting": f"Namaste {st['first_name']}! Pehle aapke parent ki permission chahiye. Dhanyavaad!",
                "memory": "No consent on file: end the call politely."}
    sess = db.create_session(st["id"], None, "phone", None, "open")
    return {**phone.call_variables(st["id"], sess["id"]), "language": st["language"], "known_caller": "true"}'''
assert old2 in s; s = s.replace(old2, new2)

# warm the profile schema too, and recover missed calls at startup
old3 = '''                                (coach._review_schema("topic"), "eval")):'''
new3 = '''                                (coach._review_schema("topic"), "eval"), (coach.PROFILE_SCHEMA, "eval")):'''
assert old3 in s; s = s.replace(old3, new3)
old4 = '''    threading.Thread(target=warm, daemon=True, name="schema-warmup").start()'''
new4 = '''    threading.Thread(target=warm, daemon=True, name="schema-warmup").start()

    def recover():
        try:
            out = phone.sync_recent_calls(phone_transcript, 20)
            if out["saved"]:
                log.info("recovered %d phone call(s) from Bolna history", len(out["saved"]))
        except Exception as e:
            log.warning("bolna call recovery skipped: %s", e)
    if settings.bolna_api_key:
        threading.Thread(target=recover, daemon=True, name="bolna-recover").start()'''
assert old4 in s; s = s.replace(old4, new4)
p.write_text(s, encoding="utf-8"); print("ok")
