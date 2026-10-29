"""Create or update the Guru Line agent in Bolna from code (prompt, 4 tools, webhook, Sarvam voice/STT).
    python scripts/bolna_sync_agent.py            # create if BOLNA_AGENT_ID is empty, else full update (PUT)
    python scripts/bolna_sync_agent.py --dry-run  # print the payload only
Saves a newly created agent id to .env. Re-run whenever PUBLIC_BASE_URL changes (e.g. a new tunnel URL)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from bolna import API, tools_config  # noqa: E402
from config import settings  # noqa: E402

AGENT_NAME = "Guru Line tutor"
# one agent per "ear": Sarvam STT set to Hindi writes English speech as broken Devanagari fragments,
# so students who chose English get an agent whose transcriber listens in English.
AGENTS = {"hi": ("BOLNA_AGENT_ID", "bolna_agent_id", ""), "en": ("BOLNA_AGENT_ID_EN", "bolna_agent_id_en", " (English)")}


def llm_config() -> dict:
    """Bolna's built-in gpt-5.4-mini, or a custom OpenAI-compatible model registered in Bolna (e.g. Qwen on Groq)."""
    if settings.bolna_llm == "custom":
        return {"provider": "custom", "model": settings.bolna_llm_model,
                "base_url": settings.bolna_llm_base_url.removesuffix("/chat/completions"),
                "family": settings.bolna_llm_family or "openai", "max_tokens": 300, "temperature": 0.3,
                # Qwen3 thinks before answering by default: on a phone call that adds delay, and on Groq the
                # thinking would otherwise come back inside the reply. Answer directly.
                "extra_body": {"reasoning_effort": "none"}}
    return {"provider": "openai", "model": "gpt-5.4-mini", "max_tokens": 150,
            "temperature": 1}   # gpt-5.4-mini is a reasoning model: Bolna requires 1


def payload(lang: str = "hi") -> dict:
    base = settings.public_base_url.rstrip("/")
    return {
        "agent_config": {
            "agent_name": AGENT_NAME + AGENTS[lang][2],
            # per-call opening from user_data (greeting -> language question, or a link to the last call)
            "agent_welcome_message": "{greeting}",
            "webhook_url": f"{base}/bolna/webhook?key={settings.webhook_secret}",
            "call_summary_enabled": False,
            "tasks": [{
                "task_type": "conversation",
                "tools_config": {
                    "llm_agent": {
                        "agent_type": "simple_llm_agent", "agent_flow_type": "streaming",
                        "llm_config": llm_config(),
                    },
                    "synthesizer": {
                        "provider": "sarvam", "stream": True, "buffer_size": 250, "audio_format": "wav",
                        # speed 0.9: students said Guru spoke too fast
                        "provider_config": {"voice": "Priya", "voice_id": "priya", "model": "bulbul:v3",
                                            "language": lang, "speed": 0.9},
                    },
                    # endpointing 1200 ms: learners pause mid-sentence; shorter values cut "I can do this, and I will
                    # help" into fragments and let Guru talk over students who were still thinking
                    "transcriber": {"provider": "sarvam", "model": "saaras:v4", "language": lang, "stream": True,
                                    "encoding": "linear16", "sampling_rate": 8000, "endpointing": 1200},
                    "input": {"provider": "plivo", "format": "wav"},
                    "output": {"provider": "plivo", "format": "wav"},
                    "api_tools": tools_config(),
                },
                "toolchain": {"execution": "parallel", "pipelines": [["transcriber", "llm", "synthesizer"]]},
                "task_config": {"call_terminate": 600, "hangup_after_silence": 20,
                                "number_of_words_for_interruption": 2,   # coughs/"haan" don't cut Guru off
                                "incremental_delay": 700,                # wait a little longer before replying
                                "hangup_after_LLMCall": True,
                                "call_cancellation_prompt": "End the call when the student clearly says bye, "
                                    "asks to cut or end the call, or after Guru has said its closing goodbye."},
            }],
        },
        "agent_prompts": {"task_1": {"system_prompt": (ROOT / "api" / "prompts" / "voice_system_prompt.md")
                                     .read_text(encoding="utf-8")}},
    }


def save_agent_id(env_key: str, agent_id: str) -> None:
    env = ROOT / ".env"
    s = env.read_text(encoding="utf-8")
    if re.search(rf"(?m)^{env_key}=", s):
        s = re.sub(rf"(?m)^{env_key}=.*$", f"{env_key}={agent_id}", s)
    else:
        s = s.rstrip("\n") + f"\n{env_key}={agent_id}\n"
    env.write_text(s, encoding="utf-8")


def main() -> None:
    base = settings.public_base_url
    if not base.startswith("https://") or "yourdomain" in base:
        sys.exit("PUBLIC_BASE_URL must be your public https URL (run scripts/dev_tunnel.py or set it in .env)")
    headers = {"Authorization": f"Bearer {settings.bolna_api_key}"}
    for lang, (env_key, attr, _) in AGENTS.items():
        body = payload(lang)
        if "--dry-run" in sys.argv:
            print(json.dumps(body, indent=2, ensure_ascii=False))
            continue
        agent_id = getattr(settings, attr)
        if agent_id:
            r = httpx.put(f"{API}/v2/agent/{agent_id}", headers=headers, json=body, timeout=30)
            action = "updated"
        else:
            r = httpx.post(f"{API}/v2/agent", headers=headers, json=body, timeout=30)
            action = "created"
        if r.status_code >= 400:
            sys.exit(f"Bolna {r.status_code} ({lang}): {r.text[:500]}")
        out = r.json()
        if action == "created":
            agent_id = out["agent_id"]
            save_agent_id(env_key, agent_id)
            setattr(settings, attr, agent_id)
        print(f"agent {action} [{lang}]: {agent_id} -> tools at {base}/bolna/*")


if __name__ == "__main__":
    main()
