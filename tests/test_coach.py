"""Coach modes (English speaking / any topic) end to end with the LLM mocked: goal capture, review, skill scores,
day/week/month progress, and graceful fallback when no LLM answers. Needs Postgres + FalkorDB."""
import pytest
from fastapi.testclient import TestClient

import coach
import db
import graph
import voice_router
import webcall
from config import settings

RAHUL = "11111111-1111-4111-8111-111111111111"
A = {"X-Admin-Key": settings.admin_key}


@pytest.fixture(scope="module", autouse=True)
def databases():
    try:
        db.ping(), graph.ping()
    except Exception as e:
        pytest.skip(f"databases not available: {e}")
    from scripts_reset import reset
    reset()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(settings, "sarvam_api_key", "")      # no TTS/STT/LLM network calls
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(coach, "_background", lambda fn, *a: fn(*a))   # run plan/evaluation synchronously


def _fake_chat(script):
    """Turn replies in order; evaluation/plan schemas get canned structured answers."""
    turns = iter(script)

    def chat(system, messages, schema=None, **kw):
        props = (schema or {}).get("properties", {})
        if "say" in props:
            return next(turns)
        if "weeks" in props:
            return {"summary": "4 weeks", "weeks": [{"week": 1, "focus": "Introduce yourself", "milestone": "1 minute talk",
                                                     "practice": ["self intro"]}]}
        if "scores" in props:
            return {"summary": "You spoke in full sentences.", "strengths": ["Full sentences"],
                    "improvements": ["Use past tense: 'I went', not 'I go'"], "next_steps": ["Describe your day"],
                    "scores": {"fluency": 6, "grammar": 5, "vocabulary": 6.5, "participation": 8},
                    "self_confidence": 7, "quiz_correct": 0, "quiz_total": 0, "aim": None,
                    "teacher_summary": "Improved: full sentences.\nStill weak: past tense.\nClass action: past-tense drill.",
                    "parent_summary_hi": "आज राहुल ने अंग्रेज़ी बोलने का अभ्यास किया।"}
        return None
    return chat


def test_english_call_goal_review_and_progress(monkeypatch):
    monkeypatch.setattr(coach, "chat", _fake_chat([
        {"say": "Hi Rahul! What is your English goal?", "goal": None, "end_call": False},
        {"say": "Great goal! Tell me about yesterday.", "goal": "Speak English confidently in interviews", "end_call": False},
        {"say": "Nice! A better way is: I went to school. Bye!", "goal": None, "end_call": True},
    ]))
    token = voice_router.make_token(RAHUL)
    g = webcall.start(token, RAHUL, "english")                    # Guru opens straight away (no yes/no gate)
    assert g["state"] == "coach" and "English goal" in g["reply_text"] and "record" not in g["reply_text"].lower()
    r2 = webcall.turn(token, text="I want to speak English confidently in interviews")
    assert r2["state"] == "coach"
    goal = db.active_goal(RAHUL, "english")
    assert goal and "interviews" in goal["aim"] and goal["plan"]["weeks"]          # captured + planned
    r3 = webcall.turn(token, text="yesterday I go to school")
    assert r3["done"]
    sid = r3["session_id"]
    sess = db.get_session(sid)
    assert sess["mode"] == "english" and sess["goal_id"] == goal["id"] and sess["ended_at"]
    review = db.session_review(sid)
    assert review["improvements"] and "past tense" in review["improvements"][0]
    scores = {r["skill"]: r["score"] for r in db.all_rows(
        "select skill, score from skill_scores where session_id=%s", (sid,))}
    assert scores["english.fluency"] == 6 and scores["english.confidence"] == 7     # self-report kept separate
    assert db.one("select count(*) n from summaries where session_id=%s", (sid,))["n"] == 2

    import main
    c = TestClient(main.app)
    sk = c.get(f"/students/{RAHUL}/skills?period=day", headers=A).json()
    assert any(r["skill"] == "english.grammar" for r in sk["series"]) and sk["reviews"]
    assert c.get(f"/students/{RAHUL}/skills?period=year", headers=A).status_code == 422
    feed = c.get(f"/sessions/{sid}/feed", headers=A).json()
    assert feed["mode"] == "english" and feed["review"]["summary"]


def test_no_llm_still_works(monkeypatch):
    """No Claude, no Sarvam: scripted coach lines, review from transcript stats, deterministic progress feedback."""
    token = voice_router.make_token(RAHUL)
    r = webcall.start(token, RAHUL, "topic")
    assert r["state"] == "coach" and r["reply_text"]
    for _ in range(5):
        if r["done"]:
            break
        r = webcall.turn(token, text="photosynthesis kya hai")
    assert r["done"]
    assert db.session_review(r["session_id"])["summary"]
    fb = coach.progress_feedback(RAHUL, "week")
    assert fb["headline"] and fb["focus_next"]


def test_manual_goal_endpoint(monkeypatch):
    monkeypatch.setattr(coach, "chat", _fake_chat([]))
    import main
    c = TestClient(main.app)
    r = c.post(f"/students/{RAHUL}/goals", headers=A, json={"mode": "topic", "aim": "Become an AI engineer"})
    assert r.status_code == 200
    goals = c.get(f"/students/{RAHUL}/goals", headers=A).json()
    assert goals[0]["aim"] == "Become an AI engineer" and goals[0]["plan"]["weeks"]
    assert c.post(f"/students/{RAHUL}/goals", headers=A, json={"mode": "cooking", "aim": "xyz abc"}).status_code == 422


def test_open_coaching_remembers_and_suggests(monkeypatch):
    """Default 'coach' mode: memory recap in the prompt, language asked once, resources saved to the journal."""
    import db as _db
    from scripts_reset import reset
    reset()
    st = {**_db.student(RAHUL), "id": RAHUL}
    first = coach.system_prompt(st, "coach")
    assert "LANGUAGE: unknown" in first and "first call" in first          # nothing remembered yet

    monkeypatch.setattr(coach, "chat", _fake_chat([
        {"say": "Namaste Rahul! Hindi, English ya mix?", "goal": None, "language": None, "resource": None, "end_call": False},
        {"say": "Theek hai, Hinglish. Aaj kya improve karna hai?", "goal": None, "language": "hi-en", "resource": None, "end_call": False},
        {"say": "Try the Feynman technique: explain it as if to a friend.", "goal": "Score 90 in science",
         "language": None, "resource": {"kind": "method", "title": "Feynman technique", "by": None,
                                        "why": "Explaining simply shows what you have not understood yet."}, "end_call": False},
        {"say": "Shabaash! Kal yeh dobara try karna. Bye!", "goal": None, "language": None, "resource": None, "end_call": True},
    ]))
    token = voice_router.make_token(RAHUL)
    g = webcall.start(token, RAHUL)                                         # default mode = open coaching
    assert "Hindi, English ya mix" in g["reply_text"] and "record" not in g["reply_text"].lower()
    webcall.turn(token, text="Hinglish")
    webcall.turn(token, text="mujhe science mein 90 laane hain")
    end = webcall.turn(token, text="ok bye")
    assert end["done"]

    assert _db.language_known(RAHUL)                                        # not asked again next call
    later = coach.system_prompt(st, "coach")
    assert "LANGUAGE: Hinglish" in later and "MEMORY (most recent first)" in later
    assert "Feynman technique" in later                                     # won't be repeated
    import main
    j = TestClient(main.app).get(f"/students/{RAHUL}/journal", headers=A).json()
    assert j["resources"][0]["title"] == "Feynman technique"
    assert any(d["resources"] for d in j["days"])
    assert _db.active_goal(RAHUL, "topic")["aim"] == "Score 90 in science"   # coach goals live with general goals


def test_phone_save_suggestion_and_open_choice():
    import main
    c = TestClient(main.app)
    H = {"X-Webhook-Secret": settings.webhook_secret}
    ctx = c.post("/bolna/get_session_context", headers=H, json={"student_id": RAHUL, "call_id": "ph-sugg"}).json()
    assert "recent_days" in ctx and "already_suggested" in ctx
    notes = c.post("/bolna/choose_topic", headers=H, json={"session_id": ctx["session_id"], "mode": "coach"}).json()
    assert notes["mode"] == "coach" and "save_suggestion" in notes["instruction"]
    r = c.post("/bolna/save_suggestion", headers=H, json={"session_id": ctx["session_id"], "kind": "book",
                                                          "title": "Wings of Fire", "by": "A.P.J. Abdul Kalam",
                                                          "why": "A real story of learning step by step."})
    assert r.json()["ok"]
    assert c.get(f"/students/{RAHUL}/journal", headers=A).json()["resources"][0]["title"] == "Wings of Fire"


def test_sign_up_new_student_then_call():
    """A new user joins with consent once, and their very first call opens naturally (no recording notice)."""
    import main
    c = TestClient(main.app)
    assert c.post("/students", headers=A, json={"first_name": "Asha", "grade": 9, "consent": False}).status_code == 422
    r = c.post("/students", headers=A, json={"first_name": "Asha", "grade": 9, "consent": True, "phone": "+919812345678"})
    sid = r.json()["student_id"]
    assert db.has_consent(sid) and not db.language_known(sid)         # language: Guru asks on the first call
    r2 = c.post("/students", headers=A, json={"first_name": "Ben", "language": "en", "is_minor": False, "consent": True})
    assert db.language_known(r2.json()["student_id"])                   # chosen at sign-up: never asked
    assert c.post("/students", headers=A, json={"first_name": "X", "consent": True, "phone": "12345"}).status_code == 422
    st = {**db.student(sid), "id": sid}
    assert "first call" in coach.system_prompt(st, "coach")             # brand-new memory
