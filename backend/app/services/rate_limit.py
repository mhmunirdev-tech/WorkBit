"""Rate-limit contract. Replace this process-local store with Redis in production."""
from datetime import datetime, timedelta, timezone
from threading import Lock
from fastapi import HTTPException
_hits: dict[str, datetime] = {}
_lock = Lock()
def enforce_cooldown(
    key: str,
    seconds: int = 60,
    message: str = "Please wait before starting this offer again.",
) -> None:
    now = datetime.now(timezone.utc)
    with _lock:
        previous = _hits.get(key)
        if previous and previous + timedelta(seconds=seconds) > now:
            raise HTTPException(429, message)
        _hits[key] = now
