from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class AppMetrics:
    run_created: int = 0
    run_succeeded: int = 0
    run_warn: int = 0
    run_needs_review: int = 0
    run_failed: int = 0
    run_timed_out: int = 0
    run_cancelled: int = 0
    stage_retried: int = 0
    quarantine_created: int = 0
    quarantine_reprocessed: int = 0
    queue_depth: int = 0
    _lock: Lock = field(default_factory=Lock)

    def inc(self, key: str, amount: int = 1) -> None:
        with self._lock:
            setattr(self, key, getattr(self, key) + amount)

    def set_queue_depth(self, depth: int) -> None:
        with self._lock:
            self.queue_depth = depth

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "run_created": self.run_created,
                "run_succeeded": self.run_succeeded,
                "run_warn": self.run_warn,
                "run_needs_review": self.run_needs_review,
                "run_failed": self.run_failed,
                "run_timed_out": self.run_timed_out,
                "run_cancelled": self.run_cancelled,
                "stage_retried": self.stage_retried,
                "quarantine_created": self.quarantine_created,
                "quarantine_reprocessed": self.quarantine_reprocessed,
                "queue_depth": self.queue_depth,
            }


metrics = AppMetrics()
