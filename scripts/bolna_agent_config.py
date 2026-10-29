"""Print the Bolna agent pieces to paste/POST: system prompt, tools, webhook. Usage:
    python scripts/bolna_agent_config.py > bolna_agent.json
Reads PUBLIC_BASE_URL and WEBHOOK_SECRET from .env. See docs/bolna-notes.md for the field reference."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from bolna import tools_config  # noqa: E402
from config import settings  # noqa: E402

base = settings.public_base_url.rstrip("/")
out = {
    "agent_prompt": (ROOT / "api" / "prompts" / "voice_system_prompt.md").read_text(encoding="utf-8"),
    "welcome_message": "Namaste! Main Guru hoon, aapka AI tutor.",
    "tools_config": {"api_tools": tools_config()},
    "webhook_url": f"{base}/bolna/webhook",
    "webhook_headers": {"X-Webhook-Secret": settings.webhook_secret},
    "inbound_caller_lookup_url": f"{base}/bolna/inbound_lookup",
    "synthesizer": {"provider": "sarvam", "provider_config": {"model": "bulbul:v3", "voice": "priya",
                                                              "voice_id": "priya", "language": "hi"}},
    "transcriber": {"provider": "sarvam", "model": "saaras:v4", "language": "hi", "stream": True,
                    "endpointing": 500},
}
if "yourdomain" in base or not base:
    print("WARNING: set PUBLIC_BASE_URL in .env to your public HTTPS API first", file=sys.stderr)
print(json.dumps(out, indent=2, ensure_ascii=False))
