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


def payload() -> dict:
    base = settings.public_base_url.rstrip("/")
    return {
        "agent_config": {
            "agent_name": AGENT_NAME,
            "agent_welcome_message": "Namaste {first_name}! Main Guru hoon, aapka AI learning coach.",
            "webhook_url": f"{base}/bolna/webhook?key={settings.webhook_secret}",
            "call_summary_enabled": False,
            "tasks": [{
                "task_type": "conversation",
                "tools_config": {
                    "llm_agent": {
                        "agent_type": "simple_llm_agent", "agent_flow_type": "streaming",
                        "llm_config": {"provider": "openai", "model": "gpt-5.4-mini", "max_tokens": 150,
                                       "temperature": 1},
                    },
                    "synthesizer": {
                        "provider": "sarvam", "stream": True, "buffer_size": 250, "audio_format": "wav",
                        "provider_config": {"voice": "Priya", "voice_id": "priya", "model": "bulbul:v3",
                                            "language": "hi", "speed": 1},
                    },
                    "transcriber": {"provider": "sarvam", "model": "saaras:v4", "language": "hi", "stream": True,
                                    "encoding": "linear16", "sampling_rate": 8000, "endpointing": 500},
                    "input": {"provider": "plivo", "format": "wav"},
                    "output": {"provider": "plivo", "format": "wav"},
                    "api_tools": tools_config(),
                },
                "toolchain": {"execution": "parallel", "pipelines": [["transcriber", "llm", "synthesizer"]]},
                "task_config": {"call_terminate": 600, "hangup_after_silence": 20},
            }],
        },
        "agent_prompts": {"task_1": {"system_prompt": (ROOT / "api" / "prompts" / "voice_system_prompt.md")
                                     .read_text(encoding="utf-8")}},
    }


def save_agent_id(agent_id: str) -> None:
    env = ROOT / ".env"
    s = env.read_text(encoding="utf-8")
    s = re.sub(r"(?m)^BOLNA_AGENT_ID=.*$", f"BOLNA_AGENT_ID={agent_id}", s)
    env.write_text(s, encoding="utf-8")


def main() -> None:
    base = settings.public_base_url
    if not base.startswith("https://") or "yourdomain" in base:
        sys.exit("PUBLIC_BASE_URL must be your public https URL (run scripts/dev_tunnel.py or set it in .env)")
    body = payload()
    if "--dry-run" in sys.argv:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return
    headers = {"Authorization": f"Bearer {settings.bolna_api_key}"}
    if settings.bolna_agent_id:
        r = httpx.put(f"{API}/v2/agent/{settings.bolna_agent_id}", headers=headers, json=body, timeout=30)
        action = "updated"
    else:
        r = httpx.post(f"{API}/v2/agent", headers=headers, json=body, timeout=30)
        action = "created"
    if r.status_code >= 400:
        sys.exit(f"Bolna {r.status_code}: {r.text[:500]}")
    out = r.json()
    if action == "created":
        save_agent_id(out["agent_id"])
    print(f"agent {action}: {out.get('agent_id', settings.bolna_agent_id)} -> tools at {base}/bolna/*")


if __name__ == "__main__":
    main()
