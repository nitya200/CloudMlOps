"""In-process sliding-window rate limiting for the authentication endpoints.

Brute forcing a password is the one attack the rest of the auth design cannot
mitigate: hashing is deliberately slow, but nothing stops an attacker from
simply trying again. This module caps how often a single client may call the
credential endpoints.

**Known limitation.** The counters live in the process, so N App Runner
instances allow N times the configured budget. That is a deliberate trade-off:
a shared Redis counter would be exact but adds a service, a network hop and a
new failure mode to a student project. The per-instance limit still turns an
unbounded online attack into a slow one, and the ``RateLimiter`` interface is
the seam where a Redis backend would slot in.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

# Stop one busy instance from growing the key space without bound. Well past
# any realistic number of concurrent clients for this deployment.
MAX_TRACKED_KEYS = 10_000


class SlidingWindowRateLimiter:
    """Counts hits per key over a moving time window.

    A sliding window is used rather than a fixed one because fixed windows let
    a caller send two full budgets back to back across a window boundary.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, *, limit: int, window_seconds: int) -> float | None:
        """Record an attempt.

        Returns ``None`` when the caller is within budget, otherwise the number
        of seconds until the oldest hit falls out of the window.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            if len(self._hits) > MAX_TRACKED_KEYS:
                self._evict_expired(cutoff)

            timestamps = self._hits[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= limit:
                return max(1.0, timestamps[0] + window_seconds - now)

            timestamps.append(now)
            return None

    def reset(self, key: str | None = None) -> None:
        """Clear one key, or every key when called without an argument."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)

    def _evict_expired(self, cutoff: float) -> None:
        """Drop keys whose every hit has aged out. Caller must hold the lock."""
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]


limiter = SlidingWindowRateLimiter()
