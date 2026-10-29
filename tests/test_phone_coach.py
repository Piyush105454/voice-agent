"""Student-led phone call (Bolna tools) in a coach mode: memory recap -> language -> topic -> goal -> confidence ->
end -> post-call webhook stores a clean transcript (Guru/<name>, Latin script) and triggers the evaluation."""
import pytest
from fastapi.testclient import TestClient

import coach
import db
import graph
import sarvam
from config import settings

RAHUL = "11111111-1111-4111-8111-111111111111"
H = {"X-Webhook-Secret": settings.webhook_secret}


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


def test_english_phone_call_end_to_end(client, monkeypatch):
    evaluated = []
    monkeypatch.setattr(coach, "evaluate", lambda sid: evaluated.append(sid))
    monkeypatch.setattr(coach, "make_plan", lambda *a: None)
    # pretend Sarvam is configured and transliterate Devanagari student lines
    monkeypatch.setattr(sarvam, "enabled", lambda: True)
    monkeypatch.setattr(sarvam, "transliterate", lambda t, *a, **k: "yes, I am fine")

    ctx = client.post("/bolna/get_session_context", json={"student_id": RAHUL, "call_id": "ph-1"}, headers=H).json()
    sid = ctx["session_id"]
    assert any("English" in o for o in ctx["suggested_options"])
    assert client.post("/bolna/set_language", headers=H, json={"session_id": sid, "language": "English"}).json()["ok"]
    notes = client.post("/bolna/choose_topic", headers=H, json={"session_id": sid, "mode": "english"}).json()
    assert notes["mode"] == "english" and "one mistake" in notes["instruction"].lower()
    g = client.post("/bolna/set_goal", headers=H, json={"session_id": sid, "aim": "Speak confidently in interviews"}).json()
    assert g["ok"] and db.active_goal(RAHUL, "english")["aim"] == "Speak confidently in interviews"
    client.post("/bolna/log_confidence", headers=H, json={"session_id": sid, "phase": "after", "value": 7})
    conf = db.one("select score from skill_scores where session_id=%s and skill='english.confidence'", (sid,))
    assert conf and conf["score"] == 7                                 # self-report feeds the progress chart
    end = client.post("/bolna/end_session", headers=H, json={"session_id": sid}).json()
    assert end["ok"] and db.get_session(sid)["ended_at"]

    raw = "assistant: Namaste Rahul! Main Guru hoon.\nuser: यस, मैं ठीक हूँ।\nassistant: Great, let's start."
    r = client.post("/bolna/webhook", headers=H, json={"id": "ph-1", "status": "completed", "transcript": raw})
    assert r.json()["ok"]
    t = db.get_session(sid)["transcript"]
    assert t.splitlines() == ["Guru: Namaste Rahul! Main Guru hoon.", "Rahul: yes, I am fine", "Guru: Great, let's start."]
    assert evaluated == [sid]                                          # evaluated once the full transcript arrived
    client.post("/bolna/webhook", headers=H, json={"id": "ph-1", "status": "completed", "transcript": raw})
    # (idempotent: a review would now exist in real runs; here evaluate is stubbed)


def test_new_tools_require_secret(client):
    assert client.post("/bolna/choose_topic", json={"session_id": "x", "mode": "maths"}).status_code == 401
    assert client.post("/bolna/set_language", json={"session_id": "x", "language": "Hindi"}).status_code == 401
