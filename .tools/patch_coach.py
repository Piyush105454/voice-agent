from pathlib import Path
p = Path("coach.py"); s = p.read_text(encoding="utf-8")

# 1) memory includes the learner profile
old = '''    given = db.recent_resources(sid, 6)
    if given:
        lines.append("ALREADY SUGGESTED (do not repeat): " + "; ".join(r["title"] for r in given))
    return "\\n".join(lines)'''
new = '''    given = db.recent_resources(sid, 6)
    if given:
        lines.append("ALREADY SUGGESTED (do not repeat): " + "; ".join(r["title"] for r in given))
    prof = db.learner_profile(sid)
    if prof:
        lines.append("WHAT YOU KNOW ABOUT THEM (your notes from past calls):")
        for key, label in PROFILE_LABELS:
            v = prof.get(key)
            if isinstance(v, list):
                v = "; ".join(str(x) for x in v[:4])
            if v:
                lines.append(f"- {label}: {v}")
    return "\\n".join(lines)'''
assert old in s; s = s.replace(old, new)

anchor = "# ---------------------------------------------------------------- progress feedback (day / week / month)"
add = Path("../.tools/coach_profile_block.py").read_text(encoding="utf-8")
assert anchor in s; s = s.replace(anchor, add + "\n\n" + anchor)

old3 = '''def _evaluate_safely(session_id: str) -> None:
    try:
        evaluate(session_id)
    except Exception:
        if db.get_session(session_id) is not None:
            log.exception("evaluation failed for %s", session_id)'''
new3 = '''def _evaluate_safely(session_id: str) -> None:
    after_call(session_id)'''
assert old3 in s; s = s.replace(old3, new3)
p.write_text(s, encoding="utf-8"); print("ok")
