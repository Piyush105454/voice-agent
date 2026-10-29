from pathlib import Path

# coach: sync graph after the profile; memory carries the research-ranked next steps
p = Path("api/coach.py"); s = p.read_text(encoding="utf-8")
old = '''    try:
        update_profile(session_id)
    except Exception:
        if db.get_session(session_id) is not None:
            log.exception("profile update failed for %s", session_id)'''
new = '''    try:
        update_profile(session_id)
    except Exception:
        if db.get_session(session_id) is not None:
            log.exception("profile update failed for %s", session_id)
    import learning_graph
    learning_graph.sync_safely(sess["student_id"])
    events.emit(sess["student_id"], "profile_updated", {"session_id": session_id, "graph": True})'''
assert old in s; s = s.replace(old, new)
old2 = '''    mis = db.active_misconceptions(sid, None, 0.5)
    if mis:
        lines.append("OPEN MATHS MISCONCEPTIONS: " + ", ".join(m["name"] for m in mis[:2]))
    trend = db.skill_trend(sid)'''
new2 = '''    if days:
        import learning_graph
        steps = learning_graph.next_steps(sid, 3)
        if steps:
            lines.append("NEXT BEST STEPS (ranked from their data; use one, explain why it works in simple words): "
                         + "; ".join(f"{x['title']} ({x['principle']})" for x in steps))
    mis = db.active_misconceptions(sid, None, 0.5)
    if mis:
        lines.append("OPEN MATHS MISCONCEPTIONS: " + ", ".join(m["name"] for m in mis[:2]))
    trend = db.skill_trend(sid)'''
assert old2 in s; s = s.replace(old2, new2)
p.write_text(s, encoding="utf-8")

# main: graph + progress endpoints, startup backfill
m = Path("api/main.py"); u = m.read_text(encoding="utf-8")
old = '''def student_graph(sid: str):
    return graph.neighbourhood(sid, 80)'''
new = '''def student_graph(sid: str):
    import learning_graph
    g = graph.neighbourhood(sid, 80)
    if not g["nodes"]:
        return g
    try:
        nodes, links = learning_graph.nodes_for(sid)
    except Exception:
        nodes, links = [], []
    have = {n["id"] for n in g["nodes"]}
    g["nodes"] += [n for n in nodes if n["id"] not in have]
    g["links"] += links
    return g'''
assert old in u; u = u.replace(old, new)
old = '''def progress(sid: str):
    return db.progress_series(sid)'''
new = '''def progress(sid: str):
    """Maths series + the coaching view: skills, self-reported confidence, research-ranked next steps, and
    per-call points (AI-judged skill average vs self-reported confidence) for the confidence chart."""
    import learning_graph
    out = db.progress_series(sid)
    coach_pts = db.all_rows("""select s.id::text as session_id, s.started_at, s.topic_id,
                                 (select avg(score)/10.0 from skill_scores k where k.session_id=s.id and k.source='llm')
                                   as accuracy,
                                 null::int as conf_before,
                                 (select round(score)::int from skill_scores k where k.session_id=s.id
                                   and k.source='self_report' limit 1) as conf_after
                               from sessions s where s.student_id::text=%s and s.mode in ('coach','english','topic')
                               order by s.started_at""", (sid,))
    seen = {p["session_id"] for p in out["session_points"] if p["accuracy"] is not None}
    out["session_points"] = sorted([p for p in out["session_points"] if p["session_id"] not in
                                    {c["session_id"] for c in coach_pts}] +
                                   [c for c in coach_pts if c["session_id"] not in seen],
                                   key=lambda p: p["started_at"])
    out["skills"] = [{k: v for k, v in s.items() if k != "last"} for s in learning_graph.skills(sid)]
    out["self_confidence"] = learning_graph.confidence(sid)
    out["next_steps"] = learning_graph.next_steps(sid)
    return out'''
assert old in u; u = u.replace(old, new)
old = '''    def recover():
        try:'''
new = '''    def recover():
        try:
            import learning_graph
            for r in db.all_rows("select distinct student_id::text as id from session_reviews"):
                learning_graph.sync_safely(r["id"])
        except Exception as e:
            logging.getLogger("bolna").warning("learning graph backfill skipped: %s", e)
        try:'''
assert old in u; u = u.replace(old, new)
m.write_text(u, encoding="utf-8")
print("ok")
