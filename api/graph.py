"""FalkorDB learning-memory graph. Postgres is truth; this is a derived, rebuildable index."""
from __future__ import annotations

from typing import Any

from falkordb import FalkorDB

from config import settings

_graph = None


def G():
    global _graph
    if _graph is None:
        db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
        _graph = db.select_graph(settings.graph_name)
    return _graph


def q(cypher: str, params: dict | None = None):
    return G().query(cypher, params or {})


def rows(cypher: str, params: dict | None = None) -> list[list[Any]]:
    return q(cypher, params).result_set or []


def ping() -> bool:
    q("RETURN 1")
    return True


def ensure_indexes() -> None:
    for label in ("Student", "Topic", "Misconception", "Strategy", "Session", "Goal"):
        try:
            q(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
        except Exception as e:  # already exists
            if "already" not in str(e).lower():
                raise


# ---------------------------------------------------------------- writes
def upsert_student(student_id: str, name: str, grade: int | None = None) -> None:
    q("MERGE (s:Student {id:$id}) SET s.name=$name, s.grade=$grade",
      {"id": student_id, "name": name, "grade": grade})


def set_mastery(student_id: str, topic_id: str, p: float, stability: float) -> None:
    q("""MATCH (s:Student {id:$sid}), (t:Topic {id:$tid})
         MERGE (s)-[m:MASTERY]->(t)
         SET m.p=$p, m.stability=$st, m.updated=timestamp()""",
      {"sid": student_id, "tid": topic_id, "p": float(p), "st": float(stability)})


def set_misconception_strength(student_id: str, mis_id: str, strength: float, n: int) -> None:
    """Write the Postgres-computed strength (keeps graph and Postgres identical)."""
    q("""MATCH (s:Student {id:$sid}), (m:Misconception {id:$mid})
         MERGE (s)-[h:HOLDS]->(m)
         ON CREATE SET h.first_seen=timestamp()
         SET h.strength=$str, h.n=$n, h.last_seen=timestamp()""",
      {"sid": student_id, "mid": mis_id, "str": float(strength), "n": int(n)})


def hold_misconception(student_id: str, mis_id: str, delta: float) -> None:
    """agent.md §5.5 — relative update, clamped to [0, 1]."""
    q("""MATCH (s:Student {id:$sid}), (m:Misconception {id:$mid})
         MERGE (s)-[h:HOLDS]->(m)
         ON CREATE SET h.strength=0.3, h.first_seen=timestamp(), h.n=0
         SET h.strength = CASE WHEN h.strength+$d>1 THEN 1.0
                               WHEN h.strength+$d<0 THEN 0.0 ELSE h.strength+$d END,
             h.last_seen=timestamp(), h.n=h.n+1""",
      {"sid": student_id, "mid": mis_id, "d": float(delta)})


def add_strategy(student_id: str, strategy_id: str) -> None:
    q("""MATCH (s:Student {id:$sid}) MERGE (st:Strategy {id:$stid})
         MERGE (s)-[r:RESPONDS_WELL_TO]->(st)
         ON CREATE SET r.evidence_n=0
         SET r.evidence_n=r.evidence_n+1, r.last_seen=timestamp()""",
      {"sid": student_id, "stid": strategy_id})


def add_goal(student_id: str, goal_id: str, text: str) -> None:
    q("""MATCH (s:Student {id:$sid}) MERGE (g:Goal {id:$gid}) SET g.text=$text
         MERGE (s)-[r:HAS_GOAL]->(g) ON CREATE SET r.created=timestamp()""",
      {"sid": student_id, "gid": goal_id, "text": text})


def add_session(student_id: str, session_id: str, topic_id: str | None,
                before_conf: int | None, after_conf: int | None, accuracy: float | None) -> None:
    q("""MATCH (s:Student {id:$sid}) MERGE (x:Session {id:$xid}) ON CREATE SET x.started=timestamp()
         MERGE (s)-[:HAD_SESSION]->(x)""", {"sid": student_id, "xid": session_id})
    if topic_id:
        q("""MATCH (x:Session {id:$xid}), (t:Topic {id:$tid}) MERGE (x)-[p:PRACTISED]->(t)
             SET p.before_conf=$b, p.after_conf=$a, p.accuracy=$acc""",
          {"xid": session_id, "tid": topic_id, "b": before_conf, "a": after_conf, "acc": accuracy})


def delete_student(student_id: str) -> None:
    q("""MATCH (s:Student {id:$i}) OPTIONAL MATCH (s)-[:HAD_SESSION]->(x:Session)
         OPTIONAL MATCH (s)-[:HAS_GOAL]->(g:Goal) DETACH DELETE x, g, s""", {"i": student_id})


# ---------------------------------------------------------------- reads
def weakest_prerequisite(student_id: str, topic_id: str) -> dict | None:
    """Root-cause query (database-design.md §5 #1)."""
    r = rows("""MATCH (p:Topic)-[:PREREQUISITE_OF*1..3]->(t:Topic {id:$tid})
                OPTIONAL MATCH (s:Student {id:$sid})-[pm:MASTERY]->(p)
                WITH DISTINCT p, coalesce(pm.p, 0.3) AS mastery
                WHERE mastery < 0.5
                RETURN p.id, p.name, mastery ORDER BY mastery ASC LIMIT 1""",
             {"sid": student_id, "tid": topic_id})
    if not r:
        return None
    return {"id": r[0][0], "name": r[0][1], "mastery": round(float(r[0][2]), 3)}


def active_misconceptions(student_id: str, topic_id: str, min_strength: float = 0.3) -> list[dict]:
    r = rows("""MATCH (s:Student {id:$sid})-[h:HOLDS]->(m:Misconception)-[:AFFECTS]->(t:Topic {id:$tid})
                WHERE h.strength > $min RETURN m.id, m.name, h.strength ORDER BY h.strength DESC LIMIT 3""",
             {"sid": student_id, "tid": topic_id, "min": min_strength})
    return [{"id": a, "name": b, "strength": round(float(c), 3)} for a, b, c in r]


def best_strategy(student_id: str) -> str | None:
    r = rows("""MATCH (s:Student {id:$sid})-[r:RESPONDS_WELL_TO]->(st:Strategy)
                RETURN st.id ORDER BY r.evidence_n DESC LIMIT 1""", {"sid": student_id})
    return r[0][0] if r else None


def class_heat(student_ids: list[str], min_strength: float = 0.4) -> list[dict]:
    r = rows("""MATCH (s:Student)-[h:HOLDS]->(x:Misconception) WHERE s.id IN $ids AND h.strength>$min
                RETURN x.id, x.name, count(s) AS students ORDER BY students DESC""",
             {"ids": student_ids, "min": min_strength})
    return [{"id": a, "name": b, "students": int(c)} for a, b, c in r]


def neighbourhood(student_id: str, limit: int = 80) -> dict:
    """Student + 2 hops, shaped for react-force-graph: {nodes, links}. Sessions/goals excluded (noise)."""
    nodes: dict[str, dict] = {}
    links: list[dict] = []
    s = rows("MATCH (s:Student {id:$sid}) RETURN s.id, s.name", {"sid": student_id})
    if not s:
        return {"nodes": [], "links": []}
    nodes[s[0][0]] = {"id": s[0][0], "label": s[0][1], "kind": "student"}

    for t_id, t_name, p, st, upd in rows(
            """MATCH (:Student {id:$sid})-[m:MASTERY]->(t:Topic)
               RETURN t.id, t.name, m.p, m.stability, m.updated""", {"sid": student_id}):
        nodes[t_id] = {"id": t_id, "label": t_name, "kind": "topic", "mastery": round(float(p), 3),
                       "stability": float(st or 3), "updated": upd}
        links.append({"source": student_id, "target": t_id, "kind": "MASTERY", "value": round(float(p), 3)})

    for m_id, m_name, strength, n, t_id in rows(
            """MATCH (:Student {id:$sid})-[h:HOLDS]->(m:Misconception)
               OPTIONAL MATCH (m)-[:AFFECTS]->(t:Topic)
               RETURN m.id, m.name, h.strength, h.n, t.id""", {"sid": student_id}):
        nodes[m_id] = {"id": m_id, "label": m_name, "kind": "misconception",
                       "strength": round(float(strength), 3), "n": int(n or 0)}
        links.append({"source": student_id, "target": m_id, "kind": "HOLDS", "value": round(float(strength), 3)})
        if t_id:
            if t_id not in nodes:
                nodes[t_id] = {"id": t_id, "label": t_id, "kind": "topic", "mastery": None}
            links.append({"source": m_id, "target": t_id, "kind": "AFFECTS"})

    for st_id, ev in rows("""MATCH (:Student {id:$sid})-[r:RESPONDS_WELL_TO]->(st:Strategy)
                             RETURN st.id, r.evidence_n""", {"sid": student_id}):
        nodes[st_id] = {"id": st_id, "label": st_id.replace("_", " "), "kind": "strategy", "n": int(ev or 0)}
        links.append({"source": student_id, "target": st_id, "kind": "RESPONDS_WELL_TO"})

    # prerequisite edges among topics, adding unmastered prereq topics so root causes are visible
    for a_id, a_name, b_id, b_name in rows(
            """MATCH (a:Topic)-[:PREREQUISITE_OF]->(b:Topic) RETURN a.id, a.name, b.id, b.name"""):
        if a_id in nodes or b_id in nodes:
            for tid, tname in ((a_id, a_name), (b_id, b_name)):
                if tid not in nodes:
                    nodes[tid] = {"id": tid, "label": tname, "kind": "topic", "mastery": None}
                elif nodes[tid]["label"] == tid:
                    nodes[tid]["label"] = tname
            links.append({"source": a_id, "target": b_id, "kind": "PREREQUISITE_OF"})

    return {"nodes": list(nodes.values())[:limit], "links": links}
