"""Teacher summary (EN, 3 lines) + parent update (HI or EN, 3 sentences). LLM with template fallback."""
from __future__ import annotations

import db
import events
from llm import llm, prompt

ACTION = {
    "adds_instead_of_inverse": 'a 5-minute "balance scale" warm-up on undoing + and -',
    "sign_not_flipped": "move-the-term drills saying the new sign out loud",
    "coefficient_ignored": 'read "5x" aloud as "5 times x" before solving',
    "neg_number_confusion": "number-line jumps with signed steps",
    "distributes_partially": '"arrow from the outside number to every term" drill',
    "equals_as_answer": "true/false equations like 7 = 5 + 2",
}
TOPIC_HI = {
    "num_negatives": "ऋणात्मक संख्याओं", "alg_expressions": "चर और व्यंजकों", "alg_linear_eq": "समीकरणों",
    "alg_distribution": "कोष्ठक (वितरण नियम)", "alg_multistep": "बहु-चरण समीकरणों",
}
HOME_HI = {
    "adds_instead_of_inverse": 'घर पर पूछिए: "+5 को दूसरी तरफ़ ले जाएँ तो क्या होता है?"',
    "sign_not_flipped": 'घर पर पूछिए: "-3 को दूसरी तरफ़ ले जाएँ तो उसका चिह्न क्या होगा?"',
    "coefficient_ignored": 'घर पर पूछिए: "5x का मतलब क्या है?"',
    "neg_number_confusion": "घर पर सीढ़ियों पर ऊपर-नीचे गिनती का खेल खेलिए।",
    "distributes_partially": 'घर पर पूछिए कि 3(x + 2) और 3x + 2 में क्या फ़र्क है।',
    "equals_as_answer": 'घर पर पूछिए: "क्या 7 = 5 + 2 सही है?"',
    None: "घर पर उसे अपने स्टेप्स बोलकर समझाने को कहिए।",
}
HOME_EN = {
    "adds_instead_of_inverse": 'At home, ask: "what happens to +5 when it moves to the other side?"',
    "sign_not_flipped": 'At home, ask: "what sign does -3 get on the other side?"',
    "coefficient_ignored": 'At home, ask what "5x" means.',
    "neg_number_confusion": "At home, play a counting game going up and down the stairs.",
    "distributes_partially": "At home, ask why 3(x + 2) is not 3x + 2.",
    "equals_as_answer": 'At home, ask: "is 7 = 5 + 2 true?"',
    None: "At home, ask them to explain their steps out loud.",
}


def _facts(student_id: str, session_id: str) -> dict:
    s = db.student(student_id)
    sess = db.get_session(session_id)
    stats = db.session_stats(session_id)
    conf = db.session_confidence(session_id)
    mis = db.session_misconceptions(session_id)
    topic_id = sess["topic_id"] or "alg_linear_eq"
    return {"name": s["first_name"], "topic_id": topic_id, "topic": db.topic_names().get(topic_id, topic_id),
            "questions": int(stats["questions"] or 0), "correct": int(stats["correct_n"] or 0),
            "before": conf.get("before"), "after": conf.get("after"),
            "misconception": mis[0] if mis else None,
            "misconception_name": db.misconception_names().get(mis[0]) if mis else None}


def template(f: dict, parent_lang: str) -> tuple[str, str]:
    improved = (f"answered {f['correct']} of {f['questions']} {f['topic'].lower()} questions correctly"
                if f["correct"] else f"worked through {f['questions']} {f['topic'].lower()} questions with hints")
    if f["before"] and f["after"]:
        improved += f"; self-reported confidence {f['before']} -> {f['after']}"
    weak = f["misconception_name"] or "no recurring misconception this session"
    action = ACTION.get(f["misconception"], "a short mixed-review warm-up on this topic")
    teacher = f"Improved: {improved}.\nStill weak: {weak}.\nClass action: {action}."
    if parent_lang == "en":
        did = (f"{f['name']} got {f['correct']} questions right." if f["correct"]
               else f"{f['name']} kept trying with hints.")
        parent = f"Today {f['name']} practised {f['topic'].lower()}.\n{did}\n{HOME_EN[f['misconception']]}"
    else:
        did = f"{f['correct']} सवाल सही किए गए।" if f["correct"] else "हिंट के साथ पूरी कोशिश की गई।"
        parent = (f"आज {f['name']} ने {TOPIC_HI.get(f['topic_id'], f['topic'])} का अभ्यास किया।\n{did}\n"
                  f"{HOME_HI[f['misconception']]}")
    return teacher, parent


def create_all(student_id: str, session_id: str) -> dict:
    f = _facts(student_id, session_id)
    g = db.guardian(student_id)
    parent_lang = "en" if g and g["preferred_language"] == "en" else "hi"
    teacher, parent = template(f, parent_lang)
    out = llm("", prompt("summaries.md").replace("{parent_language_name}",
                                                  "English" if parent_lang == "en" else "Hindi (Devanagari)")
              + "\n\nSESSION FACTS (use only these):\n" + str(f), json_mode=True, max_tokens=500)
    if isinstance(out, dict) and out.get("teacher") and out.get("parent"):
        teacher, parent = str(out["teacher"]).strip(), str(out["parent"]).strip()
    db.save_summary(session_id, "teacher", "en", teacher)
    db.save_summary(session_id, "parent", parent_lang, parent)
    return {"teacher": teacher, "parent": parent}


def notify_teacher_safety(student_id: str, session_id: str | None) -> str:
    """Records the event and pushes it to the teacher dashboard. No transcript content in the payload."""
    eid = db.log_safety_event(student_id, session_id, teacher_notified=True)
    events.emit(student_id, "safety", {"safety_event_id": eid, "session_id": session_id})
    db.audit("system", "safety_teacher_notified", "safety_event", eid)
    return eid
