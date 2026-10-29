"""End-to-end against real Postgres + FalkorDB (run scripts/reset_demo.py first; skipped if DBs are down).
Covers the agent.md §12 checklist items that need a database, plus the Sarvam web-call flow."""
import pytest

import db
import graph
import service
import voice_router
import webcall
from config import settings
from fastapi.testclient import TestClient

RAHUL = "11111111-1111-4111-8111-111111111111"
MEERA = "66666666-6666-4666-8666-666666666666"   # no consent


@pytest.fixture(scope="module", autouse=True)
def databases():
    try:
        db.ping(), graph.ping()
    except Exception as e:
        pytest.skip(f"databases not available: {e}")
    from scripts_reset import reset
    reset()


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    """No LLM / Sarvam / Bolna network calls in tests."""
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "sarvam_api_key", "")
    monkeypatch.setattr(settings, "bolna_api_key", "")


@pytest.fixture
def client():
    import main
    return TestClient(main.app)


H = {"X-Webhook-Secret": settings.webhook_secret}


def test_no_consent_is_refused(client):
    r = client.post("/bolna/get_session_context", json={"student_id": MEERA}, headers=H)
    assert r.status_code == 403


def test_bad_secret_rejected(client):
    assert client.post("/bolna/get_session_context", json={"student_id": RAHUL}).status_code == 401


def test_full_bolna_flow(client):
    ctx = client.post("/bolna/get_session_context", json={"student_id": RAHUL, "call_id": "t-call-1"}, headers=H).json()
    # student-led call: Guru opens with what it remembers and lets the student choose
    assert ctx["first_name"] == "Rahul" and ctx["mistakes_to_fix"] and ctx["suggested_options"]
    assert "Adds instead of using inverse" in ctx["mistakes_to_fix"][0]["name"]
    # same call id -> same session (Bolna may retry)
    again = client.post("/bolna/get_session_context", json={"student_id": RAHUL, "call_id": "t-call-1"}, headers=H).json()
    assert again["session_id"] == ctx["session_id"]
    sid = ctx["session_id"]
    lang = client.post("/bolna/set_language", headers=H, json={"session_id": sid, "language": "Hinglish"}).json()
    assert lang["language"].startswith("Hinglish") and db.student(RAHUL)["language"] == "hi-en"
    pick = client.post("/bolna/choose_topic", headers=H, json={"session_id": sid, "mode": "maths"}).json()
    assert pick["topic"] == "Linear equations" and pick["question"]
    q = pick["question"]
    assert client.post("/bolna/log_confidence", headers=H, json={"session_id": sid, "topic": "Linear equations",
                                                                  "phase": "before", "value": 3}).json()["ok"]
    qn = db.get_question(q["id"])
    wrong = next(iter(qn["wrong_answer_map"]))
    m0 = db.one("select strength from student_misconceptions where student_id=%s and misconception_id=%s",
                (RAHUL, qn["wrong_answer_map"][wrong]))
    p0, _, _ = db.get_mastery(RAHUL, qn["topic_id"])

    r1 = client.post("/bolna/submit_answer", headers=H, json={"session_id": sid, "question_id": q["id"],
                                                               "student_answer_text": wrong}).json()
    assert r1["action"] == "hint" and r1["misconception"] == qn["wrong_answer_map"][wrong]
    assert qn["answer"] not in r1["hint_text"].split()
    m1 = db.one("select strength from student_misconceptions where student_id=%s and misconception_id=%s",
                (RAHUL, r1["misconception"]))
    assert m1["strength"] > (m0["strength"] if m0 else 0)            # repeat error -> stronger

    r2 = client.post("/bolna/submit_answer", headers=H, json={"session_id": sid, "question_id": q["id"],
                                                               "student_answer_text": f"toh {qn['answer']}"}).json()
    assert r2["correct"] and r2["action"] == "praise_next" and r2["next_question"]
    m2 = db.one("select strength from student_misconceptions where student_id=%s and misconception_id=%s",
                (RAHUL, r1["misconception"]))
    assert m2["strength"] < m1["strength"]                            # correct use -> weaker
    assert db.get_mastery(RAHUL, qn["topic_id"])[0] != p0

    end = service.end_session(sid, wait=True)
    assert end["ok"] and end["next_plan"]
    assert service.end_session(sid)["already_ended"]                  # idempotent
    assert db.one("select count(*) n from summaries where session_id=%s", (sid,))["n"] == 2
    assert db.one("select count(*) n from live_events where student_id=%s", (RAHUL,))["n"] >= 4
    edges = graph.rows("MATCH (:Student {id:$s})-[h:HOLDS]->(m:Misconception {id:$m}) RETURN h.strength",
                       {"s": RAHUL, "m": r1["misconception"]})
    assert abs(edges[0][0] - m2["strength"]) < 1e-6                   # graph mirrors Postgres


def test_hint_ladder_reaches_reveal_only_at_3():
    ctx = service.get_context(RAHUL, channel="simulator")
    q = db.get_question(ctx["question"]["id"])
    actions = [service.submit_answer(ctx["session_id"], q["id"], "pata nahi")["action"] for _ in range(3)]
    assert actions == ["hint", "explain_step", "reveal"]
    service.end_session(ctx["session_id"], wait=True)


def test_safety_phrase_stops_and_flags():
    ctx = service.get_context(RAHUL, channel="simulator")
    n0 = db.one("select count(*) n from safety_events")["n"]
    r = service.submit_answer(ctx["session_id"], ctx["question"]["id"], "mere papa beat me every day")
    assert r["action"] == "safety_stop"
    assert db.one("select count(*) n from safety_events")["n"] == n0 + 1
    assert db.get_session(ctx["session_id"])["status"] == "safety_stop"


def test_sarvam_web_call_flow_by_text():
    """The browser fallback, driven with text turns (no Sarvam credits used)."""
    token = voice_router.make_token(RAHUL)
    start = webcall.start(token, RAHUL, "maths")
    # no scripted notice and no "shall we start?": straight to today's topic + confidence
    assert "Rahul" in start["reply_text"] and start["state"] == "confidence_before"
    assert "record" not in start["reply_text"].lower()
    r = webcall.turn(token, text="3")
    assert r["state"] == "question" and r["question"]
    for _ in range(12):                                   # answer everything correctly
        if r["state"] != "question":
            break
        r = webcall.turn(token, text=db.get_question(r["question"]["id"])["answer"])
    assert r["state"] == "confidence_after"
    end = webcall.turn(token, text="6")
    assert end["done"] and "Shabaash" in end["reply_text"]
    sess = db.get_session(end["session_id"])
    assert sess["channel"] == "web" and "Student: 3" in sess["transcript"]


def test_delete_memory(client):
    r = client.delete(f"/students/{RAHUL}/memory", headers={"X-Admin-Key": settings.admin_key})
    assert r.json()["deleted"]
    assert db.one("select count(*) n from mastery where student_id=%s", (RAHUL,))["n"] == 0
    assert db.one("select count(*) n from sessions where student_id=%s", (RAHUL,))["n"] == 0
    assert not graph.rows("MATCH (:Student {id:$s})-[r]->() RETURN r", {"s": RAHUL})


def test_rahul_replay_arc():
    """The demo replay goes through the real tutor core and lands on the before/after story."""
    from scripts_reset import reset
    import demo
    reset()
    q = "select strength from student_misconceptions where student_id=%s and misconception_id='adds_instead_of_inverse'"
    p0, m0 = db.get_mastery(RAHUL, "alg_linear_eq")[0], db.one(q, (RAHUL,))["strength"]
    sid = demo.replay(delay=0, wait=True)["session_id"]
    p1, m1 = db.get_mastery(RAHUL, "alg_linear_eq")[0], db.one(q, (RAHUL,))["strength"]
    assert abs(p0 - 0.30) < 1e-6 and abs(m0 - 0.80) < 1e-6
    assert 0.55 <= p1 <= 0.70, p1            # target ~0.62
    assert 0.30 <= m1 <= 0.50, m1            # target ~0.35
    assert db.session_confidence(sid) == {"before": 3, "after": 6}
    assert "Rahul: 3" in db.get_session(sid)["transcript"]


def test_dashboard_endpoints(client):
    A = {"X-Admin-Key": settings.admin_key}
    for path in (f"/students/{RAHUL}/overview", f"/parent/{RAHUL}", f"/privacy/{RAHUL}", "/teacher/overview",
                 "/proof", f"/live/current?student_id={RAHUL}", f"/students/{RAHUL}/graph"):
        r = client.get(path, headers=A)
        assert r.status_code == 200, (path, r.text)
        assert client.get(path).status_code == 401           # admin key required
    ov = client.get(f"/students/{RAHUL}/overview", headers=A).json()
    assert ov["topics"] and ov["memory"] and "next_review_days" in ov["topics"][0]
    sid = client.get(f"/live/current?student_id={RAHUL}", headers=A).json()["session"]["id"]
    feed = client.get(f"/sessions/{sid}/feed", headers=A).json()
    assert feed["lines"] and feed["first_name"] == "Rahul"
    heat = client.get("/teacher/overview", headers=A).json()["heatmap"]
    assert len(heat["misconceptions"]) == 6 and heat["cells"]
    proof = client.get("/proof", headers=A).json()
    assert all(c["first_name"] for c in proof["pilot"])       # seeded sessions never count as pilot


def test_replay_feed_arc(client):
    from scripts_reset import reset
    import demo
    reset()
    sid = demo.replay(delay=0, wait=True)["session_id"]
    arc = client.get(f"/sessions/{sid}/feed", headers={"X-Admin-Key": settings.admin_key}).json()["arc"]
    assert arc["mastery_before"] == 0.3 and arc["mastery_after"] > 0.55
    assert arc["misconception"] == "adds_instead_of_inverse" and arc["mis_before"] == 0.8 and arc["mis_after"] < 0.5
    assert arc["conf_before"] == 3 and arc["conf_after"] == 6
