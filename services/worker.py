"""InvoiceMind queue worker.

This worker polls queued runs from DB and executes them through the same stage
orchestrator used by API background tasks.
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.database import SessionLocal
from app.metrics import metrics
from app.orchestrator import process_run
from app.repositories import count_runs_by_status, list_queued_runs


def _default_worker_id() -> str:
    return f"worker:{socket.gethostname()}"


def drain_once(*, max_runs: int | None = None, worker_id: str | None = None) -> int:
    limit = max_runs if max_runs is not None else max(1, settings.worker_batch_size)
    wid = worker_id or _default_worker_id()

    db = SessionLocal()
    try:
        queued = list_queued_runs(db, limit=limit)
        run_ids = [r.id for r in queued]
        metrics.set_queue_depth(count_runs_by_status(db, "QUEUED"))
    finally:
        db.close()

    for run_id in run_ids:
        process_run(run_id, wid)

    db = SessionLocal()
    try:
        metrics.set_queue_depth(count_runs_by_status(db, "QUEUED"))
    finally:
        db.close()

    return len(run_ids)


def run_forever(*, poll_seconds: float | None = None, max_runs_per_cycle: int | None = None) -> None:
    interval = poll_seconds if poll_seconds is not None else max(0.1, settings.worker_poll_seconds)
    while True:
        processed = drain_once(max_runs=max_runs_per_cycle)
        if processed == 0:
            time.sleep(interval)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="InvoiceMind queue worker")
    parser.add_argument("--once", action="store_true", help="Process a single poll cycle and exit")
    parser.add_argument("--max-runs", type=int, default=None, help="Maximum runs to process per cycle")
    parser.add_argument("--poll-seconds", type=float, default=None, help="Poll interval in seconds")
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    if args.once:
        processed = drain_once(max_runs=args.max_runs)
        print(f"Processed runs: {processed}")
        return
    run_forever(poll_seconds=args.poll_seconds, max_runs_per_cycle=args.max_runs)


if __name__ == "__main__":
    main()
