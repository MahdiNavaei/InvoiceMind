from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import settings


class SlidingWindowRateLimiter:
    def __init__(self, max_per_minute: int) -> None:
        self.max_per_minute = max_per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - 60
        q = self.hits[key]
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= self.max_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        q.append(now)


limiter = SlidingWindowRateLimiter(settings.rate_limit_per_minute)


def rate_limit_dependency(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    limiter.check(key)
