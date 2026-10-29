# agent.md — Guru Line (Voice Tutor Agent)

> Read this file first, then `database-design.md`, then `ui-design.md`.
> You are building **Guru Line**: a phone-call AI tutor that finds *why* a student is wrong (misconception), remembers it in a graph, and brings it back the next day. Built for the Bolna Buildathon (submit by **31 Oct 2026**).

---

## 0. Mission and non-negotiables

**One-line pitch:** "A tutor on a normal phone call that remembers every misconception a student has, and proves they improved."

**Must work in the demo (priority order):**
1. Student calls (or gives a missed call, agent calls back) → Hindi/English voice conversation.
2. Agent asks a question → student answers → backend tags the **misconception** → agent guides with a hint ladder (never gives the answer first).
3. Dashboard updates **live** while the call is happening (mastery graph, confidence vs accuracy).
4. Next-day recall call re-tests the same misconception; dashboard shows before/after.
5. Teacher gets a 3-line summary, parent gets a Hindi update.
6. Eval report: "agent identified the correct misconception in X/30 synthetic students."

**Hard rules (safety and trust):**
- Consent first. For minors, guardian consent must exist before the first call (`consents` table).
- **Never infer emotion, personality, or mental health from voice.** Confidence = self-reported (1-10) + performance only.
- If a student says something about harm, abuse, or severe distress → stop teaching, speak calmly, tell them to talk to a trusted adult/teacher now, flag `safety_events`, notify teacher. Do not diagnose.
- Never read private emails/chats. Only consented sources (see `database-design.md` → `data_sources`).
- Do not store government IDs, card numbers, or exact home address.
- Every stored memory fact has provenance (which session) and a confidence score. Student/guardian can export and delete it.

---

## 1. Stack

| Layer | Choice |
|---|---|
| Voice agent (phone) | **Bolna** agent, Hindi/English, Sarvam Bulbul voice (supported in Bolna), Sarvam/Deepgram STT |
| Backend | Python 3.11, FastAPI, Pydantic v2, httpx |
| Relational DB | Supabase Postgres (+ Realtime) |
| Graph memory | FalkorDB (docker), accessed with the `falkordb` Python client |
| LLM | Behind one function `llm()` so the provider is swappable (Claude by default) |
| Dashboard | Next.js 14 (App Router), Tailwind, framer-motion, react-force-graph-2d, Recharts |
| Hosting | One EC2 (`docker compose up -d`): FalkorDB + API + Web + Caddy (HTTPS, needed for Bolna webhooks) |

> Credit rule: develop everything against the **text simulator** (`POST /simulate`). Use real Bolna/Sarvam minutes only for final tests, the demo video, and the live demo (~60 min budget).

---

## 2. Repo layout

```
guruline/
├─ agent.md  database-design.md  ui-design.md
├─ docker-compose.yml  Caddyfile  .env.example
├─ api/
│  ├─ main.py                # FastAPI app + routes
│  ├─ config.py              # env settings
│  ├─ llm.py                 # llm(prompt, schema) wrapper
│  ├─ db.py                  # supabase/postgres helpers
│  ├─ graph.py               # FalkorDB read/write
│  ├─ mastery.py             # BKT + decay + spaced review
│  ├─ tutor.py               # hint ladder, next-question policy
│  ├─ memory.py              # transcript->facts, retrieve, consolidate
│  ├─ summaries.py           # teacher (EN) + parent (HI) summaries
│  ├─ safety.py              # distress/harm detection
│  ├─ bolna.py               # outbound call trigger + webhook verify
│  ├─ events.py              # realtime events for dashboard
│  ├─ prompts/               # all prompts as .md/.txt files
│  └─ evals/run_eval.py      # 30 synthetic students
├─ web/                      # Next.js dashboard (see ui-design.md)
├─ sql/schema.sql  sql/seed.sql
└─ tests/
```

---

## 3. Environment (`.env.example`)

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
FALKORDB_HOST=falkordb
FALKORDB_PORT=6379
BOLNA_API_KEY=
BOLNA_AGENT_ID=
WEBHOOK_SECRET=change-me          # shared secret Bolna sends in a header
PUBLIC_BASE_URL=https://api.yourdomain.com
DEMO_MODE=true                    # fast fake data + big-screen UI
```

---

## 4. The voice agent (what runs on the call)

### 4.1 Bolna agent configuration
- Language: Hindi + English (Hinglish allowed). Greeting in the student's saved language.
- Voice: Sarvam Bulbul (pick a calm voice; check which model versions your Bolna plan lists).
- Keep turns **short** (1-2 sentences). Voice is not text.
- Tools (custom functions / webhooks → your backend). **Verify exact tool/webhook setup in Bolna docs for your plan before building**:
  `get_session_context`, `submit_answer`, `log_confidence`, `end_session`.
- Every webhook sends header `X-Webhook-Secret: $WEBHOOK_SECRET`.

### 4.2 Voice system prompt (paste into Bolna agent prompt)

```
You are "Guru", a warm, patient tutor on a phone call with a school student in India.
Speak simple Hinglish by default; switch fully to Hindi or English if the student does.
Keep every turn to 1-2 short sentences. Ask ONE question at a time. Never use bullet points,
markdown, or long explanations.

CALL FLOW
1. Start: greet by first name. Say you are an AI tutor and that the call is recorded for the
   student's learning, shared with their teacher and parent. Ask "kya aap theek hain, shuru karein?".
   If they say no, end politely.
2. Call get_session_context(student_id). It returns: first_name, language, today's topic,
   active misconceptions, strategy that works for this student, and the next question.
3. Before the first question of a topic, ask: "1 se 10 mein, aap is topic mein kitna confident
   feel karte ho?" Then call log_confidence(phase="before", topic, value).
4. Ask the question from the context exactly. Wait for the student's answer.
5. Call submit_answer(question_id, student_answer_text). It returns one of:
   - action="praise_next": praise the specific strategy (not "you are smart"), ask next question.
   - action="hint": say the returned hint_text in your own simple words. Do NOT reveal the answer.
   - action="explain_step": walk ONE step with the student, then ask them to do the next step.
   - action="reveal": only when instructed. Explain gently, then ask a similar question.
6. After the topic, ask the confidence question again (phase="after") and call log_confidence.
7. Close: summarise in one sentence what improved, tell them tomorrow's short practice, say bye.
   Call end_session(session_id).

TEACHING RULES
- Never say "wrong". Say "chalo check karte hain" and guide with a question.
- Praise effort and strategy: "tumne steps likhe, bahut accha".
- If the student is silent for several seconds, gently repeat the question once, then offer a hint.
- Do not ask for personal data (address, phone numbers, passwords, photos).
- Do NOT guess the student's mood, personality, or health from their voice. If you are unsure how
  they feel, ask: "aap kaisa feel kar rahe ho is question ke baare mein?"

SAFETY
- If the student mentions being hurt, unsafe, abused, or wanting to harm themselves or others:
  stop the lesson, stay calm and kind, say they are not in trouble, tell them to talk to a trusted
  adult or their teacher right now, and say you will let their teacher know. Call end_session with
  safety_flag=true. Do not ask for details and do not give advice beyond that.
- Stay on topic. If asked unrelated or inappropriate things, politely return to the lesson.
```

### 4.3 Tool contracts (JSON)

```jsonc
// get_session_context
POST /bolna/get_session_context  { "student_id": "uuid", "call_id": "str" }
→ { "session_id": "uuid", "first_name": "Rahul", "language": "hi-en",
    "topic": "Linear equations", "active_misconceptions": ["moves_term_without_sign_change"],
    "strategy": "step_by_step", "question": {"id":"q_017","text":"x + 5 = 12, x kya hoga?"} }

// submit_answer
POST /bolna/submit_answer { "session_id":"uuid","question_id":"q_017","student_answer_text":"17" }
→ { "correct": false, "misconception": "adds_instead_of_inverse", "hint_level": 1,
    "action": "hint", "hint_text": "Equal ke dusri taraf jaate hi +5 ka kya hota hai?" }

// log_confidence
POST /bolna/log_confidence { "session_id":"uuid","topic":"Linear equations","phase":"before","value":3 }
→ { "ok": true }

// end_session
POST /bolna/end_session { "session_id":"uuid","safety_flag":false }
→ { "ok": true, "next_plan": ["Negative numbers recap","3 equation problems"] }
```

---

## 5. Backend — working core code

### 5.1 `config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    bolna_api_key: str = ""
    bolna_agent_id: str = ""
    webhook_secret: str = "change-me"
    public_base_url: str = ""
    demo_mode: bool = True
    class Config:
        env_file = ".env"

settings = Settings()
```

### 5.2 `llm.py` — one swappable function
```python
import json, re
from anthropic import Anthropic
from config import settings

_client = Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-sonnet-4-5"   # change to the model your key supports

def llm(system: str, user: str, json_mode: bool = False, max_tokens: int = 800):
    msg = _client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    if not json_mode:
        return text
    m = re.search(r"\{.*\}|\[.*\]", text, re.S)
    return json.loads(m.group(0)) if m else {}
```

### 5.3 `mastery.py` — Bayesian Knowledge Tracing + forgetting
```python
import math
from datetime import datetime, timezone

P_LEARN, P_GUESS, P_SLIP = 0.15, 0.20, 0.10

def bkt_update(p_known: float, correct: bool, hints_used: int = 0) -> float:
    """Update P(known). Hints reduce the evidence that the student knows it."""
    p = p_known
    if correct:
        num = p * (1 - P_SLIP)
        den = num + (1 - p) * P_GUESS
    else:
        num = p * P_SLIP
        den = num + (1 - p) * (1 - P_GUESS)
    posterior = num / den if den else p
    new_p = posterior + (1 - posterior) * P_LEARN
    if correct and hints_used > 0:                 # guided success counts less
        new_p = p_known + (new_p - p_known) * (1 / (1 + hints_used))
    return max(0.01, min(0.99, new_p))

def decayed(p_known: float, last_updated: datetime, stability_days: float = 5.0) -> float:
    """Exponential forgetting. stability grows with successful reviews."""
    dt = (datetime.now(timezone.utc) - last_updated).total_seconds() / 86400
    return p_known * math.exp(-dt / max(stability_days, 0.5))

def next_review_days(p_known: float, stability_days: float) -> float:
    """Review when predicted recall falls to ~0.7."""
    return max(0.5, -stability_days * math.log(0.7 / max(p_known, 0.71)))

def calibration_gap(confidence_1_10: int, accuracy_0_1: float) -> float:
    """>0 overconfident, <0 underconfident. Metacognitive calibration."""
    return (confidence_1_10 / 10) - accuracy_0_1
```

### 5.4 `tutor.py` — hint ladder and next action
```python
HINT_LADDER = ["nudge", "hint", "worked_step", "reveal"]

def decide_action(correct: bool, hint_level: int):
    if correct:
        return {"action": "praise_next", "hint_level": 0}
    nxt = min(hint_level + 1, 3)
    action = {1: "hint", 2: "explain_step", 3: "reveal"}[nxt] if nxt >= 1 else "hint"
    return {"action": action, "hint_level": nxt}
```

### 5.5 `graph.py` — FalkorDB
```python
from falkordb import FalkorDB
from config import settings

_db = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
G = _db.select_graph("guruline")

def q(cypher: str, params: dict | None = None):
    return G.query(cypher, params or {})

def upsert_student(student_id: str, name: str):
    q("MERGE (s:Student {id:$id}) SET s.name=$name", {"id": student_id, "name": name})

def set_mastery(student_id: str, topic_id: str, p: float, stability: float):
    q("""MATCH (s:Student {id:$sid}), (t:Topic {id:$tid})
         MERGE (s)-[m:MASTERY]->(t)
         SET m.p=$p, m.stability=$st, m.updated=timestamp()""",
      {"sid": student_id, "tid": topic_id, "p": p, "st": stability})

def hold_misconception(student_id: str, mis_id: str, delta: float):
    q("""MATCH (s:Student {id:$sid}), (m:Misconception {id:$mid})
         MERGE (s)-[h:HOLDS]->(m)
         ON CREATE SET h.strength=0.3, h.first_seen=timestamp(), h.n=0
         SET h.strength = CASE WHEN h.strength+$d>1 THEN 1.0
                               WHEN h.strength+$d<0 THEN 0.0 ELSE h.strength+$d END,
             h.last_seen=timestamp(), h.n=h.n+1""",
      {"sid": student_id, "mid": mis_id, "d": delta})

def weakest_prerequisite(student_id: str, topic_id: str):
    r = q("""MATCH (p:Topic)-[:PREREQUISITE_OF*1..3]->(t:Topic {id:$tid})
             OPTIONAL MATCH (s:Student {id:$sid})-[pm:MASTERY]->(p)
             WITH p, coalesce(pm.p, 0.3) AS mastery
             WHERE mastery < 0.5
             RETURN p.id, p.name, mastery ORDER BY mastery ASC LIMIT 1""",
          {"sid": student_id, "tid": topic_id})
    return r.result_set[0] if r.result_set else None

def neighbourhood(student_id: str, limit: int = 25):
    """Compact subgraph for the dashboard and for LLM context."""
    r = q("""MATCH (s:Student {id:$sid})-[r]->(n)
             RETURN type(r), labels(n)[0], n.id, n.name, properties(r) LIMIT $lim""",
          {"sid": student_id, "lim": limit})
    return r.result_set
```

### 5.6 `memory.py` — transcript → facts → graph
```python
import json
from llm import llm
from graph import hold_misconception, set_mastery, q

EXTRACT_SYS = open("prompts/extract_facts.md").read()

def write_from_transcript(student_id: str, session_id: str, transcript: str):
    facts = llm(EXTRACT_SYS, transcript, json_mode=True, max_tokens=1200)
    for f in facts.get("misconceptions", []):
        hold_misconception(student_id, f["id"], +0.15 * float(f.get("confidence", 0.5)))
    for s in facts.get("strategies", []):
        q("""MATCH (s:Student {id:$sid}) MERGE (st:Strategy {id:$stid})
             MERGE (s)-[r:RESPONDS_WELL_TO]->(st)
             ON CREATE SET r.evidence_n=0 SET r.evidence_n=r.evidence_n+1, r.last_seen=timestamp()""",
          {"sid": student_id, "stid": s["id"]})
    return facts

def retrieve(student_id: str, topic_id: str) -> dict:
    """Compact context for get_session_context (never dump the whole graph)."""
    from graph import weakest_prerequisite
    mis = q("""MATCH (s:Student {id:$sid})-[h:HOLDS]->(m:Misconception)-[:AFFECTS]->(t:Topic {id:$tid})
               WHERE h.strength>0.3 RETURN m.id, m.name, h.strength ORDER BY h.strength DESC LIMIT 3""",
            {"sid": student_id, "tid": topic_id}).result_set
    strat = q("""MATCH (s:Student {id:$sid})-[r:RESPONDS_WELL_TO]->(st:Strategy)
                 RETURN st.id ORDER BY r.evidence_n DESC LIMIT 1""", {"sid": student_id}).result_set
    return {"misconceptions": [m[0] for m in mis],
            "strategy": strat[0][0] if strat else "step_by_step",
            "weak_prereq": weakest_prerequisite(student_id, topic_id)}
```

### 5.7 `main.py` — routes (Bolna tools + simulator + dashboard feed)
```python
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from config import settings
import db, graph, mastery, tutor, memory, summaries, safety, events, bolna

app = FastAPI(title="Guru Line API")

def verify(x_webhook_secret: str = Header(default="")):
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(401, "bad secret")

class CtxIn(BaseModel):  student_id: str; call_id: str | None = None
class AnsIn(BaseModel):  session_id: str; question_id: str; student_answer_text: str
class ConfIn(BaseModel): session_id: str; topic: str; phase: str; value: int
class EndIn(BaseModel):  session_id: str; safety_flag: bool = False

@app.post("/bolna/get_session_context", dependencies=[Depends(verify)])
def get_ctx(b: CtxIn):
    if not db.has_consent(b.student_id):
        raise HTTPException(403, "no consent on file")
    s = db.create_session(b.student_id, b.call_id)
    topic = db.pick_topic(b.student_id)                 # spaced-review aware
    ctx = memory.retrieve(b.student_id, topic["id"])
    q = db.next_question(b.student_id, topic["id"], ctx["misconceptions"])
    events.emit(b.student_id, "session_started", {"session_id": s["id"], "topic": topic["name"]})
    return {"session_id": s["id"], "first_name": db.first_name(b.student_id),
            "language": db.language(b.student_id), "topic": topic["name"],
            "active_misconceptions": ctx["misconceptions"], "strategy": ctx["strategy"],
            "question": {"id": q["id"], "text": q["text"]}}

@app.post("/bolna/submit_answer", dependencies=[Depends(verify)])
def submit(b: AnsIn):
    sess = db.get_session(b.session_id)
    qn = db.get_question(b.question_id)
    judged = tutor_judge(qn, b.student_answer_text)     # LLM: correct? + misconception id
    prior_hints = db.hints_used(b.session_id, b.question_id)
    act = tutor.decide_action(judged["correct"], prior_hints)
    db.log_attempt(b.session_id, b.question_id, b.student_answer_text,
                   judged["correct"], judged.get("misconception"), act["hint_level"])
    p_old, st = db.get_mastery(sess["student_id"], qn["topic_id"])
    p_new = mastery.bkt_update(p_old, judged["correct"], prior_hints)
    db.set_mastery(sess["student_id"], qn["topic_id"], p_new)
    graph.set_mastery(sess["student_id"], qn["topic_id"], p_new, st)
    if judged.get("misconception"):
        graph.hold_misconception(sess["student_id"], judged["misconception"], +0.2)
    elif judged["correct"]:
        for m in db.active_misconceptions(sess["student_id"], qn["topic_id"]):
            graph.hold_misconception(sess["student_id"], m, -0.1)   # evidence it is fading
    events.emit(sess["student_id"], "attempt", {"correct": judged["correct"],
                "misconception": judged.get("misconception"), "mastery": p_new})
    hint = tutor_hint(qn, judged, act["hint_level"]) if act["action"] != "praise_next" else None
    return {"correct": judged["correct"], "misconception": judged.get("misconception"),
            "hint_level": act["hint_level"], "action": act["action"], "hint_text": hint}

@app.post("/bolna/log_confidence", dependencies=[Depends(verify)])
def log_conf(b: ConfIn):
    db.log_confidence(b.session_id, b.topic, b.phase, b.value)
    events.emit(db.get_session(b.session_id)["student_id"], "confidence", b.model_dump())
    return {"ok": True}

@app.post("/bolna/end_session", dependencies=[Depends(verify)])
def end(b: EndIn):
    sess = db.get_session(b.session_id)
    transcript = db.get_transcript(b.session_id)
    if b.safety_flag or safety.scan(transcript):
        db.log_safety_event(sess["student_id"], b.session_id)
        summaries.notify_teacher_safety(sess["student_id"])
    memory.write_from_transcript(sess["student_id"], b.session_id, transcript)
    plan = db.generate_plan(sess["student_id"])                   # next-day mini plan
    summaries.create_all(sess["student_id"], b.session_id)        # teacher EN + parent HI
    db.close_session(b.session_id)
    events.emit(sess["student_id"], "session_ended", {"plan": plan})
    return {"ok": True, "next_plan": plan}

# ---- text simulator: same logic, zero voice credits -------------------------
class SimIn(BaseModel): student_id: str; message: str; session_id: str | None = None; question_id: str | None = None
@app.post("/simulate")
def simulate(b: SimIn):
    if not b.session_id:
        return get_ctx(CtxIn(student_id=b.student_id))
    return submit(AnsIn(session_id=b.session_id, question_id=b.question_id,
                        student_answer_text=b.message))

# ---- dashboard feed ----------------------------------------------------------
@app.get("/students/{sid}/graph")
def student_graph(sid: str): return graph.neighbourhood(sid, 60)

@app.get("/students/{sid}/progress")
def progress(sid: str): return db.progress_series(sid)

@app.delete("/students/{sid}/memory")           # guardian right to delete
def delete_memory(sid: str):
    db.delete_student_memory(sid); graph.q("MATCH (s:Student {id:$i}) DETACH DELETE s", {"i": sid})
    return {"deleted": True}
```

> `tutor_judge`, `tutor_hint`, and the `db.*` helpers are small functions you (or the coding agent) write using the prompts in §6 and the schema in `database-design.md`.

---

## 6. LLM prompts (store in `api/prompts/`)

### `judge_answer.md`
```
You grade a student's spoken answer. The transcript may contain Hinglish, filler words and speech-to-text errors.
Question: {question_text}
Correct answer: {correct_answer}
Known misconceptions for this question (id: description): {misconception_list}
Student said: "{student_answer_text}"
Return ONLY JSON: {"correct": bool, "misconception": "<id or null>", "reasoning": "<=20 words"}
Rules: be lenient on pronunciation/STT noise. Only tag a misconception if the answer or reasoning clearly matches one.
If unsure, misconception=null.
```

### `hint_writer.md`
```
Write ONE spoken hint in simple Hinglish (max 20 words). Level: {hint_level}
(1=nudge question, 2=point to the exact step, 3=reveal and explain gently).
Misconception: {misconception_desc}. Never say "wrong". Never give the final answer at levels 1-2.
Strategy that works for this student: {strategy}. Output the hint text only.
```

### `extract_facts.md`
```
From this tutoring transcript, extract facts about the STUDENT'S LEARNING only.
Return ONLY JSON:
{"misconceptions":[{"id":"<from allowed list>","confidence":0-1,"evidence":"short quote"}],
 "strategies":[{"id":"step_by_step|analogy|worked_example|visual|repetition","evidence":"..."}],
 "goals":[{"text":"..."}]}
Forbidden: mood, personality, mental health, family or medical details, anything not about learning.
Only include items with direct evidence in the transcript.
```

### `plan_writer.md`
```
Create a 3-day mini plan. Inputs: mastery per topic, active misconceptions, weakest prerequisite,
spaced-review due list, student goal, available minutes/day: {minutes}.
Rules: fix the weakest prerequisite first; keep difficulty slightly above current mastery;
include one retrieval-practice item from yesterday; include a self-confidence check each day.
Return JSON: [{"day":1,"activities":[{"topic":"","type":"guided|independent|review","n_questions":3}]}]
```

### `summaries.md`
```
Teacher summary (English, exactly 3 lines): what improved, what is still weak (misconception name), one suggested classroom action.
Parent update (Hindi, 3 short sentences, warm, no jargon): what was practised, one improvement, one thing to encourage at home.
Never include scores as rankings or comparisons with other students.
```

---

## 7. Misconception library (seed 6 for algebra)

| id | name | example |
|---|---|---|
| `adds_instead_of_inverse` | Adds instead of using inverse | x+5=12 → 17 |
| `sign_not_flipped` | Forgets sign flips when moving a term | x-3=7 → 4 |
| `coefficient_ignored` | Ignores coefficient | 3x=12 → 12 |
| `neg_number_confusion` | Negative number rules | -2-3 → -1 |
| `distributes_partially` | Partial distribution | 2(x+3) → 2x+3 |
| `equals_as_answer` | Treats "=" as "answer comes next" | 3+4=7+2 |

Each question row stores which misconceptions its common wrong answers map to.

---

## 8. Eval harness (your differentiator)

`api/evals/run_eval.py`
1. Create 30 synthetic students: each = (target misconception, noise level, language style).
2. A "student simulator" LLM answers the 40 seed questions **as if** holding that misconception (with Hinglish + noise).
3. Run each through `/simulate`; record the tagged misconception.
4. Report: accuracy of tagging, false-positive rate, avg hints to reach correct answer, and mastery gain over 3 simulated days.
5. Save `eval_report.json` + chart; show "X/30" on the dashboard Eval page and in the pitch.

> Be honest on the slide: these are **synthetic** students. Add real-student results separately (n=3-5, with consent).

---

## 9. Nightly consolidation job (cron / APScheduler)

- Apply forgetting decay to all `MASTERY` edges.
- Merge duplicate `Misconception` evidence; weaken edges with no evidence for 14 days.
- Resolve contradictions (newer evidence wins).
- Compute next-review dates and queue "recall call" triggers.
- Trigger Bolna outbound calls for students due today (respect quiet hours 9:00-19:00 and guardian consent).

---

## 10. Outbound call + missed-call flow (`bolna.py`)

```python
import httpx
from config import settings

def trigger_call(student_phone: str, student_id: str):
    # Verify the exact request body in Bolna's outbound-call API docs for your plan.
    r = httpx.post("https://api.bolna.ai/call",
        headers={"Authorization": f"Bearer {settings.bolna_api_key}"},
        json={"agent_id": settings.bolna_agent_id,
              "recipient_phone_number": student_phone,
              "user_data": {"student_id": student_id}}, timeout=20)
    r.raise_for_status()
    return r.json()
```
Missed-call: use your telephony number's missed-call/callback hook (Exotel/Plivo) → hits `/missed_call` → `trigger_call()`.

---

## 11. Build order (one day)

1. `docker compose up` (FalkorDB + API). Run `sql/schema.sql`, `sql/seed.sql`, graph seed.
2. Implement routes + `/simulate`; pass `tests/test_flow.py` (create session → wrong answer → hint → right answer → mastery up).
3. Dashboard with live events (see `ui-design.md`).
4. Create Bolna agent with §4.2 prompt; wire tools; test ~5-10 minutes.
5. Eval harness → get your number.
6. Real consented students (3-5) → before/after.
7. Record 2-min demo + backup demo video. Submit.

## 12. Acceptance checklist

- [ ] A call with no consent record is refused.
- [ ] Wrong answer never reveals the answer before hint level 3.
- [ ] Misconception edge strength rises on repeat error and falls on correct use.
- [ ] Mastery decays when not practised (visible on dashboard).
- [ ] Dashboard updates within ~1s of each answer.
- [ ] Safety phrase triggers stop + teacher notification.
- [ ] `/students/{id}/memory` DELETE removes Postgres rows and the graph node.
- [ ] Eval report generated and shown.
- [ ] Backup demo video exists.

> Do not claim things the product does not measure. Say "self-reported confidence + quiz accuracy", never "emotion detection".
