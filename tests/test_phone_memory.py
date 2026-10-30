"""Phone calls are never lost and every call builds on the last one:
- Bolna may leave the call id empty: get_session_context must not crash (it used to 500 on the 2nd call),
- the webhook finds the student's session from the call's user_data even without an id,
- after the call: review + learner profile, and the NEXT call opens with a line linked to this one."""
import pytest
from fastapi.testclient import TestClient

import coach
import db
import graph
from config import settings

RAHUL = "11111111-1111-4111-8111-111111111111"
H = {"X-Webhook-Secret": settings.webhook_secret}
A = {"X-Admin-Key": settings.admin_key}


@pytest.fixture(scope="module", autouse=True)
def databases():
    try:
        db.ping(), graph.ping()
    except Exception as e:
        pytest.skip(f"databases not available: {e}")
    from scripts_reset import reset
    reset()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(coach, "_background", lambda fn, *a: fn(*a))
    import main
    return TestClient(main.app)


PROFILE = {"about": "Class 8, likes cricket, wants to be an engineer", "motivation": "make parents proud",
           "confidence_pattern": "said 4/10 at start, 7/10 at end",
           "recurring_mistakes": ['stops after "I can do this, and I will help the team"'],
           "goal_in_their_words": "corporate English for office meetings",
           "topics_covered": ["introducing yourself"], "next_topics": ["giving a work update", "polite requests"],
           "what_works": ["tiny worked example then try", "active recall"], "watch_outs": ["jokes a lot: redirect kindly"],
           "direction": "Master linear equations, then word problems", "next_call_plan": "Check 2 inverse-step questions",
           "next_call_opener": "Pichli baar humne equations pe kaam kiya tha, kya aapne woh 2 sawaal try kiye?"}


def test_empty_call_id_twice_does_not_crash(client):
    a = client.post("/bolna/get_session_context", headers=H, json={"student_id": RAHUL, "call_id": ""})
    b = client.post("/bolna/get_session_context", headers=H, json={"student_id": RAHUL, "call_id": ""})
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["session_id"] == b.json()["session_id"]          # a retry reuses the live session
    db.close_session(a.json()["session_id"], "ended")


def test_webhook_binds_by_student_and_builds_memory(client, monkeypatch):
    calls = []
    monkeypatch.setattr(coach, "evaluate", lambda sid: calls.append(("review", sid)))
    monkeypatch.setattr(coach, "chat", lambda *a, **k: PROFILE)   # the profile writer
    db.remember_language(RAHUL, "hi-en", None)

    # the session is created when dialling (no Bolna id known to the tools)
    sess = db.create_session(RAHUL, None, "phone", None, "open")
    payload = {"id": "exec-xyz", "status": "completed",
               "context_details": {"recipient_data": {"student_id": RAHUL, "session_id": sess["id"]}},
               "transcript": "assistant: Namaste Rahul!\nuser: equations practice karni hai\nassistant: Chalo!"}
    r = client.post("/bolna/webhook", headers=H, json=payload).json()
    assert r["session_id"] == sess["id"]
    saved = db.get_session(sess["id"])
    assert saved["bolna_call_id"] == "exec-xyz" and saved["ended_at"] and "Rahul: equations" in saved["transcript"]
    assert saved["mode"] == "coach"                                   # open chat counts as coaching -> reviewed
    assert ("review", sess["id"]) in calls
    assert db.learner_profile(RAHUL)["direction"].startswith("Master linear")

    client.post("/bolna/webhook", headers=H, json=payload)            # Bolna repeats "completed"
    assert calls.count(("review", sess["id"])) == 1

    # next call: opening line links to the last call, memory carries the notes
    st = {**db.student(RAHUL), "id": RAHUL}
    line = coach.opening_line(st)
    assert line.startswith("Hi Rahul") and "Pichli baar" in line and "record" not in line.lower()
    import phone
    v = phone.call_variables(RAHUL, "s-1")
    assert v["greeting"] == line and "What works with them" in v["memory"] and "{" not in v["memory"]
    assert "NEXT NEW TOPICS" in v["memory"] and "giving a work update" in v["memory"]
    assert "corporate English" in v["memory"] and "introducing yourself" in v["memory"]
    assert "PAST CALLS" in v["memory"] or "first call" in v["memory"]
    j = client.get(f"/students/{RAHUL}/journal", headers=A).json()
    assert j["profile"]["next_call_plan"] == PROFILE["next_call_plan"]


def test_webhook_without_any_session_still_saves_the_call(client, monkeypatch):
    monkeypatch.setattr(coach, "after_call", lambda sid: None)
    payload = {"id": "exec-lost", "status": "completed", "created_at": "2026-10-29T16:38:55+00:00",
               "context_details": {"recipient_data": {"student_id": RAHUL}},
               "transcript": "assistant: Hi\nuser: hello"}
    r = client.post("/bolna/webhook", headers=H, json=payload).json()
    s = db.get_session(r["session_id"])
    assert s["bolna_call_id"] == "exec-lost" and s["transcript"] and s["ended_at"]
    assert client.post("/bolna/webhook", headers=H, json={"id": "exec-none", "status": "ringing"}).json()["ignored"]


def test_new_student_phone_opening_asks_language():
    import main
    c = TestClient(main.app)
    sid = c.post("/students", headers=A, json={"first_name": "Zoya", "consent": True}).json()["student_id"]
    line = coach.opening_line({**db.student(sid), "id": sid})
    assert line.startswith("Namaste Zoya!") and "milkar" in line and "Hindi, English, ya dono ka mix" in line
    assert coach.spoken_name("rahul ai") == "Rahul" and coach.opening_line({"id": sid, "first_name": ""}) == coach.UNKNOWN_CALLER


def test_stale_active_session_does_not_pin_the_live_console():
    """An unanswered call whose end webhook never came stays 'active'. The live console must show the latest real call."""
    sid = db.one("select id::text from students where first_name='Rahul'")["id"]
    old = db.create_session(sid, None, "phone", None, "open")
    db.run("update sessions set started_at = now() - interval '3 hours' where id::text=%s", (old["id"],))
    real = db.create_session(sid, "exec-live-ok", "phone", None, "coach")
    db.run("update sessions set started_at = now() - interval '2 hours', ended_at = now() - interval '110 minutes', "
           "status='ended' where id::text=%s", (real["id"],))
    shown = db.latest_session(sid)
    assert shown["id"] != old["id"]                                    # not the 3-hour-old 'active' ghost
    assert db.get_session(old["id"])["ended_at"] is not None           # the ghost was closed
    assert db.get_session(old["id"])["status"] == "ended"
    fresh = db.create_session(sid, None, "phone", None, "open")        # a call that is really in progress stays live
    assert db.latest_session(sid)["id"] == fresh["id"]
    db.close_session(fresh["id"], "ended")
