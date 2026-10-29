"""Transcript -> learning facts -> Postgres (provenance) + graph. Retrieval for the next call."""
from __future__ import annotations

import logging
import re

import db
import graph
from llm import llm, prompt

log = logging.getLogger("memory")
STRATEGIES = {"step_by_step", "analogy", "worked_example", "visual", "repetition"}
MIN_CONFIDENCE = 0.4  # database-design.md §6: below this, ignored for teaching decisions

# Post-filter: nothing about mood, personality, health, family, identity or contact details.
FORBIDDEN = re.compile(
    r"\b(mood|sad|happy|upset|angry|anxious|anxiety|depress\w*|stress\w*|nervous|lonely|cry\w*|emotion\w*|"
    r"personality|introvert\w*|extrovert\w*|lazy|shy|confident person|mental|health|ill|sick|disease|doctor|"
    r"medicine|medical|diagnos\w*|adhd|autis\w*|dyslexi\w*|family|father|mother|parents?|divorce|brother|sister|"
    r"religio\w*|caste|address|phone|aadhaar|password|udaas|gussa|pareshan|bimar|ghar wale)\b", re.I)


def _clean(text: str) -> bool:
    return bool(text) and not FORBIDDEN.search(text)


def deterministic_facts(session_id: str) -> dict:
    """Facts we can prove from the attempts table alone (works with no LLM)."""
    rows = db.all_rows("""select question_id, student_answer, correct, misconception_id, hint_level, q.text
                          from attempts a join questions q on q.id=a.question_id
                          where a.session_id::text=%s order by a.created_at""", (session_id,))
    mis: dict[str, dict] = {}
    strategies: dict[str, str] = {}
    for r in rows:
        if r["misconception_id"] and r["misconception_id"] not in mis:
            mis[r["misconception_id"]] = {"id": r["misconception_id"], "confidence": 0.85,
                                          "evidence": f"{r['text']} -> {r['student_answer']}"[:120]}
        if r["correct"] and r["hint_level"] >= 2:
            strategies.setdefault("step_by_step", f"solved {r['question_id']} after doing one step together")
        elif r["correct"] and r["hint_level"] == 1:
            strategies.setdefault("worked_example", f"solved {r['question_id']} after one nudge")
    return {"misconceptions": list(mis.values()),
            "strategies": [{"id": k, "evidence": v, "confidence": 0.6} for k, v in strategies.items()],
            "goals": []}


def write_from_transcript(student_id: str, session_id: str, transcript: str) -> dict:
    facts = deterministic_facts(session_id)
    allowed = set(db.misconception_descriptions())
    extracted = llm("", prompt("extract_facts.md").replace("{allowed_ids}", ", ".join(sorted(allowed)))
                    + "\n\nTRANSCRIPT:\n" + (transcript or "")[:8000],
                    json_mode=True, max_tokens=900) if transcript else None
    if isinstance(extracted, dict):
        seen = {m["id"] for m in facts["misconceptions"]}
        for m in extracted.get("misconceptions") or []:
            if m.get("id") in allowed and m["id"] not in seen and float(m.get("confidence", 0)) >= MIN_CONFIDENCE \
                    and _clean(str(m.get("evidence", ""))):
                facts["misconceptions"].append({"id": m["id"], "confidence": float(m["confidence"]),
                                                "evidence": str(m.get("evidence", ""))[:160]})
        seen = {s["id"] for s in facts["strategies"]}
        for s in extracted.get("strategies") or []:
            if s.get("id") in STRATEGIES and s["id"] not in seen and _clean(str(s.get("evidence", ""))):
                facts["strategies"].append({"id": s["id"], "evidence": str(s.get("evidence", ""))[:160],
                                            "confidence": 0.6})
        for g in extracted.get("goals") or []:
            if _clean(str(g.get("text", ""))):
                facts["goals"].append({"text": str(g["text"])[:160]})

    for m in facts["misconceptions"]:
        db.add_fact(student_id, "misconception", {"id": m["id"], "evidence": m["evidence"]}, m["confidence"],
                    session_id)
    for s in facts["strategies"]:
        db.add_fact(student_id, "strategy", {"id": s["id"], "evidence": s["evidence"]}, s["confidence"], session_id)
        _graph(graph.add_strategy, student_id, s["id"])
    for g in facts["goals"]:
        gid = db.add_fact(student_id, "goal", {"text": g["text"]}, 0.6, session_id)
        _graph(graph.add_goal, student_id, gid, g["text"])
    return facts


def retrieve(student_id: str, topic_id: str) -> dict:
    """Compact context for get_session_context (never the whole graph). Postgres fallback if graph is down."""
    try:
        mis = [m["id"] for m in graph.active_misconceptions(student_id, topic_id)]
        strategy = graph.best_strategy(student_id)
        weak = graph.weakest_prerequisite(student_id, topic_id)
    except Exception as e:
        log.warning("graph retrieve failed, using postgres: %s", e)
        mis = [m["id"] for m in db.active_misconceptions(student_id, topic_id)][:3]
        r = db.one("""select content->>'id' as id from memory_facts where student_id::text=%s and kind='strategy'
                      and superseded_by is null and confidence >= 0.4 order by created_at desc limit 1""",
                   (student_id,))
        strategy, weak = (r["id"] if r else None), None
    return {"misconceptions": mis, "strategy": strategy or "step_by_step", "weak_prereq": weak}


def _graph(fn, *args) -> None:
    """Graph is a derived index: a failed write is logged, rebuild_graph() repairs it."""
    try:
        fn(*args)
    except Exception as e:
        log.warning("graph write %s failed: %s", fn.__name__, e)
