"""One swappable LLM entry point. Returns None when no provider answers: every caller has a
deterministic fallback, so the demo never depends on an API key or a timeout.

Claude (primary): Opus 5.5 by default. Thinking can't be disabled on it, so speed is controlled with
output_config.effort ("low" for live conversation turns, "medium" for evaluations/plans). JSON comes back via
structured outputs (output_config.format json_schema). The server-side refusal fallback is enabled.
Sarvam (fallback): sarvam-105b-conversations, JSON mode with the schema described in the system prompt."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from config import settings

log = logging.getLogger("llm")
PROMPTS = Path(__file__).resolve().parent / "prompts"
_anthropic = None
# Models that accept the server-side refusal fallback ("default" routing, Claude API).
_FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")


def prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def _providers() -> list[str]:
    have = {"anthropic": bool(settings.anthropic_api_key), "sarvam": bool(settings.sarvam_api_key)}
    first = settings.llm_provider.lower()
    if first == "none":
        return []
    order = [first] + [p for p in ("anthropic", "sarvam") if p != first]
    return [p for p in order if have.get(p)]


def _claude():
    global _anthropic
    if _anthropic is None:
        from anthropic import Anthropic
        _anthropic = Anthropic(api_key=settings.anthropic_api_key, max_retries=0)  # voice: fail fast, fall back
    return _anthropic


def _call_anthropic(system: str, messages: list[dict], schema: dict | None, max_tokens: int, timeout: float,
                    purpose: str) -> str | None:
    model = (settings.anthropic_chat_model or settings.anthropic_model) if purpose == "chat" else settings.anthropic_model
    effort = settings.anthropic_chat_effort if purpose == "chat" else settings.anthropic_eval_effort
    output_config: dict = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages,
                    "output_config": output_config, "timeout": timeout}
    if system:  # long, stable system prompt first so it can be cached across turns
        kwargs["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    client = _claude()
    if model.startswith(_FALLBACK_MODELS):
        msg = client.beta.messages.create(**kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    else:
        msg = client.messages.create(**kwargs)
    if msg.stop_reason == "refusal":
        log.warning("claude refused (%s)", getattr(msg.stop_details, "category", None))
        return None
    return "".join(b.text for b in msg.content if b.type == "text")


def _call_sarvam(system: str, messages: list[dict], schema: dict | None, max_tokens: int, timeout: float) -> str:
    import sarvam
    if schema:
        system = (system + "\n\nReply with ONLY a JSON object matching this JSON schema:\n" + json.dumps(schema)).strip()
    return sarvam.chat(system, messages=messages, max_tokens=max_tokens, timeout=timeout, json_mode=bool(schema))


def parse_json(text: str):
    m = re.search(r"\{.*\}|\[.*\]", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def chat(system: str, messages: list[dict], schema: dict | None = None, max_tokens: int = 1500,
         timeout: float | None = None, purpose: str = "eval"):
    """Multi-turn call. messages = [{"role": "user"|"assistant", "content": str}, ...].
    Returns str, or a dict when schema is given; None if every provider failed."""
    timeout = timeout or settings.llm_timeout_s
    for p in _providers():
        try:
            text = (_call_anthropic(system, messages, schema, max_tokens, timeout, purpose) if p == "anthropic"
                    else _call_sarvam(system, messages, schema, max_tokens, timeout))
        except Exception as e:  # provider down / out of credit / no key -> try the next one
            log.warning("llm provider %s failed: %s", p, str(e)[:200])
            continue
        if text is None:
            continue
        if not schema:
            if text.strip():
                return text.strip()
            continue
        parsed = parse_json(text)
        if isinstance(parsed, dict):
            return parsed
        log.warning("llm provider %s returned unparsable JSON", p)
    return None


def llm(system: str, user: str, json_mode: bool = False, max_tokens: int = 800, timeout: float | None = None):
    """Single-turn helper used by grading/hints/summaries. json_mode without a schema: parse loosely."""
    out = chat(system, [{"role": "user", "content": user}], None, max_tokens, timeout)
    if out is None or not json_mode:
        return out
    return parse_json(out)
