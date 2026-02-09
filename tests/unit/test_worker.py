from types import SimpleNamespace

from services import worker


class _DummySession:
    def close(self) -> None:
        return


def test_drain_once_processes_queued_runs(monkeypatch):
    processed: list[tuple[str, str]] = []

    monkeypatch.setattr(worker, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(
        worker,
        "list_queued_runs",
        lambda db, limit: [SimpleNamespace(id="run-1"), SimpleNamespace(id="run-2")][:limit],
    )
    monkeypatch.setattr(worker, "count_runs_by_status", lambda db, status: 0)
    monkeypatch.setattr(worker.metrics, "set_queue_depth", lambda depth: None)
    monkeypatch.setattr(worker, "process_run", lambda run_id, wid: processed.append((run_id, wid)))

    count = worker.drain_once(max_runs=2, worker_id="worker:test")
    assert count == 2
    assert processed == [("run-1", "worker:test"), ("run-2", "worker:test")]
