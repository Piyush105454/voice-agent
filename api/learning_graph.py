"""Coaching side of the learning graph + "next best steps".

After every call the student's coaching state is mirrored into FalkorDB so the Advanced view shows it:
goal -> next steps, skills (score + trend), self-reported confidence, topics practised, mistake patterns,
what works for them, resources suggested. Postgres stays the truth; these nodes are rebuilt on each sync.

next_steps() ranks what to do next with well-established learning research, each step carrying its reason:
- spacing effect (review a skill just as it fades: Ebbinghaus 1885; Cepeda et al. 2006), Leitner-style intervals,
- deliberate practice on the weakest sub-skill (Ericsson et al. 1993),
- zone of proximal development: the next topic just beyond current level (Vygotsky),
- self-efficacy from small wins when confidence lags ability (Bandura 1977),
- calibration by self-testing when confidence runs ahead of ability (Kornell & Bjork),
- focused feedback on one error pattern at a time (Hattie & Timperley 2007)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import db
import graph

log = logging.getLogger("learning_graph")

OWNED_KINDS = ("confidence", "pattern", "practice", "next", "resource", "works", "challenge")


def challenge_status(text: str) -> tuple[str, float]:
    """'problem; root cause; next action; status improving' -> ('problem', 0.5). new 0, improving 0.5, solved 1."""
    low = text.lower()
    value = 1.0 if "solved" in low else 0.5 if "improving" in low else 0.0
    return text.split(";")[0].strip(), value
INTERVALS = [1, 2, 4, 7, 15, 30]          # days between reviews after 0..5 good sessions (Leitner-style)
SKILL_NAMES = {"fluency": "Fluency", "grammar": "Grammar", "vocabulary": "Vocabulary", "participation": "Participation",
               "understanding": "Understanding", "application": "Application", "clarity": "Clarity"}


def _short(text: str, n: int = 34) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def skills(student_id: str) -> list[dict]:
    """Latest score, 30-day trend, sessions and days since practice for every measured skill (0-10)."""
    rows = db.all_rows("""select skill, score, created_at from skill_scores where student_id::text=%s
                          and source='llm' order by created_at""", (student_id,))
    out: dict[str, dict] = {}
    now = datetime.now(timezone.utc)
    for r in rows:
        s = out.setdefault(r["skill"], {"skill": r["skill"], "first": r["score"], "n": 0, "good": 0})
        s["n"] += 1
        s["good"] += r["score"] >= 7
        s["score"], s["last"] = r["score"], r["created_at"]
    for s in out.values():
        s["trend"] = round(s["score"] - s.pop("first"), 1)
        s["days_since"] = (now - s["last"]).days
        area, _, name = s["skill"].partition(".")
        s["label"] = f"{SKILL_NAMES.get(name, name.title())} ({'English' if area == 'english' else area})"
    return sorted(out.values(), key=lambda s: s["score"])


def confidence(student_id: str) -> dict | None:
    rows = db.all_rows("""select score, created_at from skill_scores where student_id::text=%s and source='self_report'
                          order by created_at""", (student_id,))
    if not rows:
        return None
    return {"value": round(rows[-1]["score"]), "trend": round(rows[-1]["score"] - rows[0]["score"], 1), "n": len(rows)}


def next_steps(student_id: str, limit: int = 5) -> list[dict]:
    prof = db.learner_profile(student_id) or {}
    sk = skills(student_id)
    conf = confidence(student_id)
    steps: list[dict] = []

    open_ch = [c for c in (prof.get("challenges") or []) if challenge_status(c)[1] < 1]
    for c in open_ch[:1]:
        problem, value = challenge_status(c)
        parts = [x.strip() for x in c.split(";")]
        step = parts[2] if len(parts) > 2 else ""
        steps.append({"kind": "follow_up", "title": f"Follow up: {_short(problem, 60)}", "priority": 0.9 - 0.1 * value,
                      "why": (f"Check the step agreed last time: {_short(step, 90)}. " if step else "")
                             + "Planning when and how, then checking back, makes people actually do it.",
                      "principle": "Implementation intentions and follow-up (Gollwitzer 1999)"})
    for t in (prof.get("next_topics") or [])[:1]:
        steps.append({"kind": "new", "title": f"Next: {t}", "priority": 0.8,
                      "why": "The next step just beyond what you can do now is where learning is fastest.",
                      "principle": "Zone of proximal development (Vygotsky)"})
    if not prof.get("next_topics"):
        g = next((g for g in db.list_goals(student_id) if g["status"] == "active"), None)
        weeks = ((g or {}).get("plan") or {}).get("weeks") or []
        if weeks:
            from coach import _week_index
            w = weeks[min(len(weeks) - 1, _week_index(g))]
            steps.append({"kind": "new", "title": f"This week: {w['focus']}", "priority": 0.75,
                          "why": f"Milestone: {w['milestone']}", "principle": "Zone of proximal development (Vygotsky)"})

    for s in sk:
        interval = INTERVALS[min(s["good"], len(INTERVALS) - 1)]
        if s["days_since"] >= interval:
            overdue = s["days_since"] / interval
            steps.append({"kind": "review", "title": f"Review {s['label']}", "priority": min(0.9, 0.5 + 0.1 * overdue),
                          "why": f"Last practised {s['days_since']} days ago; a review now, just as it fades, makes it last.",
                          "principle": "Spacing effect (Ebbinghaus; Cepeda et al. 2006)"})
    weak = [s for s in sk if s["score"] < 7 and not s["skill"].endswith(".confidence")]
    if weak:
        s = weak[0]
        steps.append({"kind": "skill", "title": f"Strengthen {s['label']}: {s['score']:g}/10",
                      "priority": 0.4 + 0.5 * (10 - s["score"]) / 10 + (0.15 if s["trend"] < 0 else 0),
                      "why": "Focused practice on your weakest sub-skill, with feedback, gives the biggest gain.",
                      "principle": "Deliberate practice (Ericsson et al. 1993)"})
    avg = sum(s["score"] for s in sk) / len(sk) if sk else None
    if conf is None:
        steps.append({"kind": "confidence", "title": "Rate your confidence 1-10 on each call", "priority": 0.45,
                      "why": "Saying how sure you feel, then checking, trains you to know what you really know.",
                      "principle": "Metacognitive monitoring (Dunlosky et al. 2013)"})
    elif avg is not None and conf["value"] < avg - 1.5:
        steps.append({"kind": "confidence", "title": "Build confidence with small wins", "priority": 0.7,
                      "why": f"You rate yourself {conf['value']}/10 but perform near {avg:.0f}/10: you can do more than you feel.",
                      "principle": "Self-efficacy from mastery experiences (Bandura 1977)"})
    elif avg is not None and conf["value"] > avg + 1.5:
        steps.append({"kind": "confidence", "title": "Test yourself before moving on", "priority": 0.6,
                      "why": f"You feel {conf['value']}/10 but perform near {avg:.0f}/10: recall without help to check.",
                      "principle": "Calibration through self-testing (Kornell & Bjork)"})
    for m in (prof.get("recurring_mistakes") or [])[:1]:
        steps.append({"kind": "pattern", "title": f"Fix one pattern: {_short(m, 60)}", "priority": 0.6,
                      "why": "Feedback on one error at a time, then a fresh try, changes habits fastest.",
                      "principle": "Focused feedback (Hattie & Timperley 2007)"})
    steps.sort(key=lambda x: -x["priority"])
    return [{**s, "priority": round(s["priority"], 2)} for s in steps[:limit]]


def sync(student_id: str) -> None:
    """Rebuild the student's coaching nodes in the graph from Postgres + Guru's notes."""
    st = db.student(student_id)
    if not st:
        return
    prof = db.learner_profile(student_id) or {}
    sid = student_id
    graph.q("MERGE (s:Student {id:$sid}) SET s.name=coalesce(s.name, $n)", {"sid": sid, "n": st["first_name"]})
    graph.q("MATCH (n {owner:$sid}) DETACH DELETE n", {"sid": sid})

    def node(nid: str, kind: str, label: str, rel: str, src: str = sid, value: float | None = None,
             detail: str | None = None) -> None:
        graph.q(f"""MATCH (a {{id:$src}}) MERGE (n:Coach {{id:$id}})
                    SET n.owner=$sid, n.kind=$kind, n.label=$label, n.value=$value, n.detail=$detail
                    MERGE (a)-[:{rel}]->(n)""",
                {"src": src, "id": nid, "sid": sid, "kind": kind, "label": label, "value": value,
                 "detail": detail or label})

    goals = [g for g in db.list_goals(sid) if g["status"] == "active"]
    for g in db.list_goals(sid):
        graph.q("""MATCH (s:Student {id:$sid}) MERGE (g:Goal {id:$gid}) SET g.text=$t, g.active=$a
                   MERGE (s)-[:HAS_GOAL]->(g)""", {"sid": sid, "gid": g["id"], "t": g["aim"], "a": g["status"] == "active"})
    anchor = goals[0]["id"] if goals else sid
    for i, t in enumerate((prof.get("next_topics") or [])[:3]):
        node(f"nx:{sid}:{i}", "next", _short(t), "NEXT_STEP", anchor, float(i + 1), t)
    for i, t in enumerate((prof.get("topics_covered") or [])[:8]):
        node(f"pr:{sid}:{i}", "practice", _short(t), "PRACTISED", detail=t)

    sk = skills(sid)
    for s in sk:
        graph.q("""MATCH (st:Student {id:$sid}) MERGE (k:Skill {id:$k}) SET k.name=$name
                   MERGE (st)-[r:SKILL]->(k) SET r.score=$v, r.trend=$tr, r.updated=timestamp()""",
                {"sid": sid, "k": s["skill"], "name": s["label"], "v": float(s["score"]), "tr": float(s["trend"])})
    weakest = next((s["skill"] for s in sk if not s["skill"].endswith(".confidence")), None)
    for i, m in enumerate((prof.get("recurring_mistakes") or [])[:3]):
        node(f"pat:{sid}:{i}", "pattern", _short(m), "HAS_PATTERN", detail=m)
        if weakest:
            graph.q("MATCH (p {id:$p}), (k:Skill {id:$k}) MERGE (p)-[:WEAKENS]->(k)", {"p": f"pat:{sid}:{i}", "k": weakest})
    for i, c in enumerate((prof.get("challenges") or [])[:4]):
        problem, value = challenge_status(c)
        node(f"ch:{sid}:{i}", "challenge", _short(problem), "FACES", value=value, detail=c)
    for i, w in enumerate((prof.get("what_works") or [])[:3]):
        node(f"ww:{sid}:{i}", "works", _short(w), "RESPONDS_WELL_TO", detail=w)
    for i, r in enumerate(db.recent_resources(sid, 4)):
        node(f"res:{sid}:{i}", "resource", _short(r["title"]), "SUGGESTED", detail=f"{r['title']}"
             + (f" by {r['by']}" if r.get("by") else "") + (f": {r['why']}" if r.get("why") else ""))
    c = confidence(sid)
    if c:
        node(f"conf:{sid}", "confidence", f"Confidence {c['value']}/10", "FEELS", value=float(c["value"]),
             detail=f"Self-reported {c['value']}/10 over {c['n']} answer(s); change {c['trend']:+g}")


def sync_safely(student_id: str) -> None:
    try:
        sync(student_id)
    except Exception as e:
        log.warning("learning graph sync failed for %s: %s", student_id, e)


def nodes_for(student_id: str) -> tuple[list[dict], list[dict]]:
    """Coaching nodes + links for the Advanced graph."""
    nodes: list[dict] = []
    links: list[dict] = []
    for gid, text in graph.rows("""MATCH (:Student {id:$sid})-[:HAS_GOAL]->(g:Goal) WHERE g.active = true
                                   RETURN g.id, g.text""", {"sid": student_id}):
        nodes.append({"id": gid, "label": _short(text, 40), "kind": "goal", "detail": text})
        links.append({"source": student_id, "target": gid, "kind": "HAS_GOAL"})
    for kid, name, score, trend in graph.rows("""MATCH (:Student {id:$sid})-[r:SKILL]->(k:Skill)
                                                 RETURN k.id, k.name, r.score, r.trend""", {"sid": student_id}):
        nodes.append({"id": kid, "label": name or kid, "kind": "skill", "score": float(score or 0),
                      "trend": float(trend or 0)})
        links.append({"source": student_id, "target": kid, "kind": "SKILL", "value": float(score or 0) / 10})
    for nid, kind, label, value, detail in graph.rows("""MATCH (n:Coach {owner:$sid})
                                                         RETURN n.id, n.kind, n.label, n.value, n.detail""",
                                                      {"sid": student_id}):
        nodes.append({"id": nid, "label": label, "kind": kind, "value": value, "detail": detail})
    for a, b, rel in graph.rows("""MATCH (a)-[r]->(n:Coach {owner:$sid}) RETURN a.id AS s, n.id AS t, type(r) AS k
                                   UNION MATCH (n:Coach {owner:$sid})-[r]->(b:Skill)
                                   RETURN n.id AS s, b.id AS t, type(r) AS k""",
                                {"sid": student_id}):
        links.append({"source": a, "target": b, "kind": rel})
    return nodes, links
