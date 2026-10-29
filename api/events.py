"""Realtime dashboard events (database-design.md §8). Insert into live_events: Supabase Realtime picks it up,
and the NOTIFY trigger feeds the SSE fallback (/events/stream). Payloads carry IDs + learning tags only."""
from __future__ import annotations

import logging

from pg import json, run

log = logging.getLogger("events")
KINDS = {"session_started", "attempt", "confidence", "misconception_detected", "session_ended", "safety",
         "voice_provider", "review_ready", "coach_turn", "session_saved", "profile_updated"}


def emit(student_id: str | None, kind: str, payload: dict) -> None:
    assert kind in KINDS, kind
    try:
        run("insert into live_events(student_id, kind, payload) values (%s, %s, %s)",
            (student_id, kind, json(payload)))
    except Exception as e:  # never break a call because the dashboard feed failed
        log.warning("emit %s failed: %s", kind, e)
