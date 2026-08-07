"""
lib/state.py — In-memory conversation state manager.

State machine steps:
  idle               → not in a flow
  waiting_student_id → asked for student ID (e.g. G9A001)
  waiting_class      → asked to choose class
  waiting_method     → asked to choose Wave or NUG
  waiting_amount     → asked to type amount
  waiting_screenshot → asked to send payment screenshot
  processing         → screenshot received, Gemini/Drive/Sheets running
  admin_broadcast    → admin typed /broadcast, waiting for message text
"""
import time
from typing import Optional

# { user_id: { "step": str, "data": dict, "last_active": float } }
_states: dict[int, dict] = {}

# Rate limiter: { user_id: last_submission_timestamp }
_rate_limits: dict[int, float] = {}


def get_step(user_id: int) -> str:
    return _states.get(user_id, {}).get("step", "idle")


def get_data(user_id: int) -> dict:
    return _states.get(user_id, {}).get("data", {})


def set_step(user_id: int, step: str):
    if user_id not in _states:
        _states[user_id] = {"step": step, "data": {}, "last_active": time.time()}
    else:
        _states[user_id]["step"] = step
        _states[user_id]["last_active"] = time.time()


def update_data(user_id: int, **kwargs):
    if user_id not in _states:
        _states[user_id] = {"step": "idle", "data": {}, "last_active": time.time()}
    _states[user_id]["data"].update(kwargs)
    _states[user_id]["last_active"] = time.time()


def reset(user_id: int):
    _states.pop(user_id, None)


def check_rate_limit(user_id: int, limit_seconds: int) -> Optional[int]:
    """Returns None if allowed, or seconds remaining if rate-limited."""
    now = time.time()
    last = _rate_limits.get(user_id)
    if last is None:
        return None
    elapsed = now - last
    if elapsed < limit_seconds:
        return int(limit_seconds - elapsed)
    return None


def record_submission(user_id: int):
    _rate_limits[user_id] = time.time()


def cleanup_stale(max_age_seconds: int = 3600):
    now = time.time()
    stale = [uid for uid, s in _states.items()
             if now - s.get("last_active", 0) > max_age_seconds]
    for uid in stale:
        _states.pop(uid, None)
