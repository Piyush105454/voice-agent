"""Bayesian Knowledge Tracing + forgetting (agent.md §5.3)."""
from __future__ import annotations

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
    """Exponential forgetting. Stability grows with successful reviews."""
    dt = (datetime.now(timezone.utc) - last_updated).total_seconds() / 86400
    return p_known * math.exp(-dt / max(stability_days, 0.5))


def next_review_days(p_known: float, stability_days: float) -> float:
    """Review when predicted recall falls to ~0.7."""
    return max(0.5, -stability_days * math.log(0.7 / max(p_known, 0.71)))


def grow_stability(stability_days: float, correct: bool, hints_used: int) -> float:
    if correct and hints_used == 0:
        return min(60.0, stability_days * 1.5)
    if correct:
        return min(60.0, stability_days * 1.15)
    return max(1.0, stability_days * 0.8)


# Misconception strength (0..1). Errors pull it toward 1 with diminishing steps; correct use of the same idea
# decays it proportionally, less when the student needed hints (guided success is weaker evidence, as in BKT).
MIS_NEW, MIS_ERROR_GAIN, MIS_CORRECT_KEEP, MIS_GUIDED_KEEP = 0.3, 0.2, 0.75, 0.85


def misconception_update(strength: float | None, event: str) -> float:
    """event: 'error' | 'correct' | 'guided_correct'."""
    s = MIS_NEW if strength is None else strength
    if event == "error":
        s = s + MIS_ERROR_GAIN * (1 - s)
    elif event == "correct":
        s = s * MIS_CORRECT_KEEP
    elif event == "guided_correct":
        s = s * MIS_GUIDED_KEEP
    else:
        raise ValueError(event)
    return round(min(1.0, max(0.0, s)), 4)


def calibration_gap(confidence_1_10: int, accuracy_0_1: float) -> float:
    """>0 overconfident, <0 underconfident. Metacognitive calibration."""
    return (confidence_1_10 / 10) - accuracy_0_1
