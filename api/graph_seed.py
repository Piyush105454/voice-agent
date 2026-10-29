"""Rebuild the FalkorDB graph from Postgres (database-design.md §4). Batched with UNWIND: < 1 s for the demo set."""
from __future__ import annotations

import time

import db
from graph import ensure_indexes, q


def rebuild_graph() -> dict:
    t0 = time.perf_counter()
    q("MATCH (n) DETACH DELETE n")
    ensure_indexes()

    topics = db.all_topics()
    q("UNWIND $rows AS r MERGE (t:Topic {id:r.id}) SET t.name=r.name, t.subject=r.subject", {"rows": topics})

    q("""UNWIND $rows AS r MATCH (a:Topic {id:r.prereq_id}), (b:Topic {id:r.topic_id})
         MERGE (a)-[:PREREQUISITE_OF]->(b)""", {"rows": db.all_prereqs()})

    mis = [{"id": m["id"], "name": m["name"], "topic_id": m["topic_id"]} for m in db.all_misconceptions()]
    q("""UNWIND $rows AS r MERGE (x:Misconception {id:r.id}) SET x.name=r.name, x.topic_id=r.topic_id
         WITH x, r MATCH (t:Topic {id:r.topic_id}) MERGE (x)-[:AFFECTS]->(t)""", {"rows": mis})

    students = db.all_students()
    q("UNWIND $rows AS r MERGE (s:Student {id:r.id}) SET s.name=r.first_name, s.grade=r.grade",
      {"rows": students})

    mastery = [{**r, "p_known": float(r["p_known"]), "stability_days": float(r["stability_days"])}
               for r in db.all_mastery()]
    q("""UNWIND $rows AS r MATCH (s:Student {id:r.student_id}), (t:Topic {id:r.topic_id})
         MERGE (s)-[m:MASTERY]->(t) SET m.p=r.p_known, m.stability=r.stability_days, m.updated=r.updated_ms""",
      {"rows": mastery})

    holds = [{**r, "strength": float(r["strength"])} for r in db.all_student_misconceptions()]
    q("""UNWIND $rows AS r MATCH (s:Student {id:r.student_id}), (m:Misconception {id:r.misconception_id})
         MERGE (s)-[h:HOLDS]->(m) SET h.strength=r.strength, h.n=r.evidence_n,
             h.first_seen=r.first_ms, h.last_seen=r.last_ms""", {"rows": holds})

    q("""UNWIND $rows AS r MATCH (s:Student {id:r.student_id}) MERGE (st:Strategy {id:r.strategy_id})
         MERGE (s)-[x:RESPONDS_WELL_TO]->(st) SET x.evidence_n=r.n""", {"rows": db.all_strategy_facts()})

    q("""UNWIND $rows AS r MATCH (s:Student {id:r.student_id}) MERGE (g:Goal {id:r.id}) SET g.text=r.text
         MERGE (s)-[:HAS_GOAL]->(g)""", {"rows": db.all_goal_facts()})

    sess = [{**r, "accuracy": float(r["accuracy"]) if r["accuracy"] is not None else None}
            for r in db.all_session_topics()]
    q("""UNWIND $rows AS r MATCH (s:Student {id:r.student_id}) MERGE (x:Session {id:r.session_id})
         MERGE (s)-[:HAD_SESSION]->(x)
         WITH x, r MATCH (t:Topic {id:r.topic_id})
         MERGE (x)-[p:PRACTISED]->(t) SET p.before_conf=r.before_conf, p.after_conf=r.after_conf,
             p.accuracy=r.accuracy""", {"rows": sess})

    return {"seconds": round(time.perf_counter() - t0, 3), "students": len(students),
            "topics": len(topics), "misconceptions": len(mis), "mastery_edges": len(mastery),
            "holds_edges": len(holds)}


if __name__ == "__main__":
    print(rebuild_graph())
