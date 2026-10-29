"""Coaching calls show up in the learning graph and drive research-ranked next steps."""
import pytest
from fastapi.testclient import TestClient

import db
import graph
import learning_graph
from config import settings

A = {"X-Admin-Key": settings.admin_key}


@pytest.fixture(scope="module", autouse=True)
def databases():
    try:
        db.ping(), graph.ping()
    except Exception as e:
        pytest.skip(f"databases not available: {e}")
    from scripts_reset import reset
    reset()


def test_coach_call_feeds_graph_and_next_steps():
    import main
    c = TestClient(main.app)
    sid = c.post("/students", headers=A, json={"first_name": "Piyush", "language": "en", "is_minor": False,
                                               "consent": True}).json()["student_id"]
    sess = db.create_session(sid, None, "web", None, "english")
    db.add_skill_scores(sid, sess["id"], None, {"english.fluency": 4, "english.grammar": 6.5}, "llm")
    db.add_skill_scores(sid, sess["id"], None, {"english.confidence": 3}, "self_report")
    db.close_session(sess["id"], "ended")
    db.save_learner_profile(sid, {"topics_covered": ["self introduction"], "next_topics": ["giving a work update"],
                                  "recurring_mistakes": ["stops mid-sentence"], "what_works": ["role-play"]}, sess["id"])
    db.add_fact(sid, "note", {"type": "resource", "kind": "book", "title": "Atomic Habits", "by": "James Clear",
                              "why": "tiny habits"}, 0.9, sess["id"])

    learning_graph.sync(sid)
    learning_graph.sync(sid)                                        # idempotent rebuild
    g = c.get(f"/students/{sid}/graph", headers=A).json()
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"student", "skill", "confidence", "pattern", "practice", "next", "resource", "works"} <= kinds
    assert len([n for n in g["nodes"] if n["kind"] == "next"]) == 1
    ids = {n["id"] for n in g["nodes"]}
    assert all((l["source"] in ids) and (l["target"] in ids) for l in g["links"])
    assert any(l["kind"] == "WEAKENS" for l in g["links"])          # mistake pattern -> weakest skill

    steps = learning_graph.next_steps(sid)
    kinds = [s["kind"] for s in steps]
    assert steps[0]["title"].startswith("Next: giving a work update")
    assert "skill" in kinds and "Fluency" in next(s for s in steps if s["kind"] == "skill")["title"]
    assert any(s["kind"] == "confidence" and "small wins" in s["title"] for s in steps)   # 3/10 vs ~5/10
    assert all(s["principle"] for s in steps)

    p = c.get(f"/students/{sid}/progress", headers=A).json()
    pt = next(x for x in p["session_points"] if x["session_id"] == sess["id"])
    assert abs(pt["accuracy"] - 0.525) < 1e-6 and pt["conf_after"] == 3
    assert p["skills"][0]["skill"] == "english.fluency" and p["next_steps"]
