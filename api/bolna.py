"""Bolna: outbound call trigger, error classification, agent/tool config (docs/bolna-notes.md)."""
from __future__ import annotations

import re

import httpx

from config import settings

API = "https://api.bolna.ai"
BOLNA_IPS = {"13.203.39.153", "13.126.9.249", "13.202.133.53"}
# Bolna does not document its out-of-credit error shape, so classify by status + message text.
_LIMIT_RX = re.compile(r"credit|balance|wallet|insufficient|recharge|top.?up|quota|limit|exhaust|"
                       r"concurren|minutes|plan|billing|payment", re.I)


class BolnaError(Exception):
    def __init__(self, status: int | None, message: str, limit: bool, recipient: bool = False):
        super().__init__(f"bolna {status}: {message}")
        self.status, self.message, self.limit = status, message, limit
        self.recipient = recipient   # problem with this phone number only (e.g. trial: unverified number)


def enabled() -> bool:
    return bool(settings.bolna_api_key and settings.bolna_agent_id)


_RECIPIENT_RX = re.compile(r"verified|recipient|invalid.{0,20}(phone|number)|not a valid (phone|number)", re.I)


def classify(status: int | None, body: str) -> BolnaError:
    recipient = status is not None and 400 <= status < 500 and bool(_RECIPIENT_RX.search(body or ""))
    limit = not recipient and (status in (402, 429) or
                               (status in (400, 401, 403, 409, 422) and bool(_LIMIT_RX.search(body or ""))))
    return BolnaError(status, (body or "")[:300], limit, recipient)


def agent_for(language: str | None) -> str:
    """English speakers get the agent that listens in English (the Hindi transcriber breaks English speech)."""
    return settings.bolna_agent_id_en if language == "en" and settings.bolna_agent_id_en else settings.bolna_agent_id


def trigger_call(phone_e164: str, student_id: str, extra: dict | None = None, language: str | None = None) -> dict:
    body = {"agent_id": agent_for(language), "recipient_phone_number": phone_e164,
            "user_data": {"student_id": student_id, **(extra or {})}}
    if settings.bolna_from_number:
        body["from_phone_number"] = settings.bolna_from_number
    try:
        r = httpx.post(f"{API}/call", headers={"Authorization": f"Bearer {settings.bolna_api_key}"},
                       json=body, timeout=20)
    except httpx.HTTPError as e:
        raise BolnaError(None, f"network: {e}", limit=False) from e
    if r.status_code >= 400:
        raise classify(r.status_code, r.text)
    out = r.json()
    if str(out.get("status", "")).lower() in ("error", "failed"):
        raise classify(200, str(out))
    return out


def recent_executions(limit: int = 20) -> list[dict]:
    """The agent's latest calls (transcripts included), newest first: used to recover missed webhooks."""
    out: list[dict] = []
    for agent in filter(None, {settings.bolna_agent_id, settings.bolna_agent_id_en}):
        r = httpx.get(f"{API}/v2/agent/{agent}/executions",
                      headers={"Authorization": f"Bearer {settings.bolna_api_key}"},
                      params={"page_size": limit}, timeout=30)
        r.raise_for_status()
        d = r.json()
        out += (d.get("data") if isinstance(d, dict) else d) or []
    return sorted(out, key=lambda e: str(e.get("created_at") or ""), reverse=True)


# ---------------------------------------------------------------- agent config (Phase 4 helper)

def _tool(name: str, description: str, props: dict, required: list[str], pre_call: str) -> tuple[dict, dict]:
    # integers -> %(x)i; strings and booleans -> %(x)s (the API coerces "True"/"false" to bool)
    param = {k: f"%({k})i" if v.get("type") == "integer" else f"%({k})s" for k, v in props.items()}
    spec = {"key": "custom_task", "name": name, "description": description, "pre_call_message": pre_call,
            "parameters": {"type": "object", "properties": props, "required": required}}
    params = {"url": f"{settings.public_base_url.rstrip('/')}/bolna/{name}", "method": "POST",
              "param": param, "headers": {"Content-Type": "application/json",
                                          "X-Webhook-Secret": settings.webhook_secret}}
    return spec, params


def tools_config() -> dict:
    s, i, b = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
    defs = [
        _tool("get_session_context", "Start the call: returns session_id and what Guru remembers about the student "
              "(last call, goals, confidence, weekly progress, mistakes to fix, suggested options).",
              {"student_id": s, "call_id": s}, ["student_id"], "Hmm."),
        _tool("set_language", "Save the language the student wants to talk in today (Hindi, English or Hinglish).",
              {"session_id": s, "language": {"type": "string", "enum": ["Hindi", "English", "Hinglish"]}},
              ["session_id", "language"], "Okay."),
        _tool("choose_topic", "The student chose what to work on. mode: coach (anything: subjects, exams, skills, "
              "goals, study habits; the default), maths (misconception drills) or english (spoken English). "
              "Returns the first question (maths) or coaching notes.",
              {"session_id": s, "mode": {"type": "string", "enum": ["coach", "maths", "english"]}, "topic": s},
              ["session_id", "mode"], "Okay."),
        _tool("save_suggestion", "Save a real book, a correctly attributed quote, or a proven study method you just "
              "suggested, so the student can see it on their platform.",
              {"session_id": s, "kind": {"type": "string", "enum": ["book", "quote", "method"]}, "title": s, "by": s,
               "why": s}, ["session_id", "kind", "title", "why"], "Okay."),
        _tool("set_goal", "Save a bigger goal the student just stated (e.g. 'become an AI engineer').",
              {"session_id": s, "aim": s}, ["session_id", "aim"], "Great goal."),
        _tool("submit_answer", "Grade the student's answer to the current question.",
              {"session_id": s, "question_id": s, "student_answer_text": s},
              ["session_id", "question_id", "student_answer_text"], "Hmm."),
        _tool("log_confidence", "Save the student's self-reported confidence (1-10).",
              {"session_id": s, "topic": s, "phase": {"type": "string", "enum": ["before", "after"]}, "value": i},
              ["session_id", "phase", "value"], "Okay."),
        _tool("end_session", "End the lesson and get tomorrow's practice plan.",
              {"session_id": s, "safety_flag": b}, ["session_id"], "Okay."),
    ]
    return {"tools": [d[0] for d in defs], "tools_params": {d[0]["name"]: d[1] for d in defs}}
