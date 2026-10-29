"""Picks the voice channel for a tutoring call.

auto (default): Bolna phone call first. If Bolna answers with a limit / credit / quota / concurrency error
(or is unreachable), Bolna is benched for BOLNA_COOLDOWN_MINUTES and the call falls back to a Sarvam
browser call: the student gets a link, speaks in the browser, and Sarvam STT/TTS + the same tutor core
run behind it. While Bolna is benched every new call goes straight to Sarvam, no Bolna request is made."""
from __future__ import annotations

import base64
import hashlib
import hmac
import threading
import time
from datetime import datetime, timedelta, timezone

import bolna
import db
import events
import sarvam
from config import settings

_lock = threading.Lock()
_state = {"bolna_blocked_until": None, "reason": None, "last_error": None, "last_switch_at": None}
NETWORK_COOLDOWN_MIN = 5


class VoiceError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _reason(raw: str) -> str:
    """Bolna errors come as JSON text ({"message": "..."}); show just the human message."""
    try:
        import json
        return str(json.loads(raw).get("message") or raw)[:160]
    except Exception:
        return (raw or "")[:160]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def bolna_blocked() -> bool:
    until = _state["bolna_blocked_until"]
    return bool(until and until > _now())


def block_bolna(reason: str, error: str, minutes: int) -> None:
    with _lock:
        _state.update(bolna_blocked_until=_now() + timedelta(minutes=minutes), reason=reason,
                      last_error=error[:300], last_switch_at=_now())
    events.emit(None, "voice_provider", {"provider": "sarvam_web", "reason": reason,
                                         "bolna_retry_at": _state["bolna_blocked_until"].isoformat()})


def reset_bolna() -> None:
    with _lock:
        _state.update(bolna_blocked_until=None, reason=None, last_error=None)


def status() -> dict:
    blocked = bolna_blocked()
    if settings.voice_provider == "sarvam" or (not bolna.enabled()):
        active = "sarvam_web" if sarvam.enabled() else None
    elif settings.voice_provider == "bolna":
        active = "bolna"
    else:
        active = "sarvam_web" if blocked and sarvam.enabled() else "bolna"
    until = _state["bolna_blocked_until"]
    return {"mode": settings.voice_provider, "active": active,
            "bolna": {"configured": bolna.enabled(), "blocked": blocked,
                      "retry_at": until.isoformat() if blocked else None,
                      "reason": _state["reason"] if blocked else None, "last_error": _state["last_error"]},
            "sarvam": {"configured": sarvam.enabled(), "stt_model": settings.sarvam_stt_model,
                       "tts_model": settings.sarvam_tts_model, "speaker": settings.sarvam_tts_speaker}}


# ---------------------------------------------------------------- signed web-call links


def _key() -> bytes:
    return hashlib.sha256(f"webcall:{settings.webhook_secret}:{settings.admin_key}".encode()).digest()


def make_token(student_id: str, minutes: int | None = None) -> str:
    exp = int(time.time()) + 60 * (minutes or settings.web_call_link_minutes)
    msg = f"{student_id}.{exp}"
    sig = hmac.new(_key(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(f"{msg}.{sig}".encode()).decode().rstrip("=")


def read_token(token: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()
        student_id, exp, sig = raw.rsplit(".", 2)
    except Exception as e:
        raise VoiceError(401, "invalid link") from e
    good = hmac.new(_key(), f"{student_id}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, good):
        raise VoiceError(401, "invalid link")
    if int(exp) < time.time():
        raise VoiceError(401, "this call link has expired")
    return student_id


def web_link(student_id: str) -> dict:
    token = make_token(student_id)
    base = settings.public_base_url.rstrip("/") if settings.public_base_url and \
        "yourdomain" not in settings.public_base_url else ""
    return {"token": token, "url": f"{base}/call?t={token}"}


# ---------------------------------------------------------------- start a call


def start_call(student_id: str, provider: str | None = None) -> dict:
    st = db.student(student_id)
    if not st:
        raise VoiceError(404, "unknown student")
    if not db.has_consent(student_id):
        raise VoiceError(403, "no guardian consent on file")
    mode = provider or settings.voice_provider
    tried: list[str] = []

    if mode in ("auto", "bolna") and bolna.enabled() and st["phone_e164"]:
        if mode == "bolna" or not bolna_blocked():
            try:
                out = bolna.trigger_call(st["phone_e164"], student_id, {"first_name": st["first_name"]})
                db.audit("system", "bolna_call_triggered", "student", student_id)
                return {"provider": "bolna", "execution_id": out.get("execution_id"), "status": out.get("status")}
            except bolna.BolnaError as e:
                if mode == "bolna":
                    raise VoiceError(502, f"Bolna call failed: {e.message}") from e
                if e.recipient:  # this number can't be called (e.g. unverified on a trial): don't pause Bolna
                    _state["last_error"] = e.message[:300]
                else:
                    block_bolna("limit_reached" if e.limit else "unavailable", e.message,
                                settings.bolna_cooldown_minutes if e.limit else NETWORK_COOLDOWN_MIN)
                tried.append(f"bolna: {'limit reached' if e.limit else 'cannot call this number' if e.recipient else 'unavailable'}"
                             f" ({e.status}): {_reason(e.message)}")
        else:
            until = _state["bolna_blocked_until"].astimezone().strftime("%H:%M")
            tried.append(f"bolna: paused until {until} ({_state['reason']}: {_reason(_state['last_error'] or '')})")
    elif mode in ("auto", "bolna"):
        tried.append("bolna: not configured" if not bolna.enabled() else "bolna: student has no phone number")
        if mode == "bolna":
            raise VoiceError(503, "; ".join(tried))

    if not sarvam.enabled():
        raise VoiceError(503, "; ".join(tried + ["sarvam: SARVAM_API_KEY not set"]))
    link = web_link(student_id)
    db.audit("system", "sarvam_web_call_link", "student", student_id)
    return {"provider": "sarvam_web", **link, "fallback_reason": "; ".join(tried) or None,
            "expires_in_minutes": settings.web_call_link_minutes}
