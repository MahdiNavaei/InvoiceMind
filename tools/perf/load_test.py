from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

API_URL = os.getenv("INVOICEMIND_API", "http://127.0.0.1:8000")
DEFAULT_CONCURRENCY = int(os.getenv("INVOICEMIND_LOAD_CONCURRENCY", "4"))
DEFAULT_REQUESTS = int(os.getenv("INVOICEMIND_LOAD_REQUESTS", "12"))
DEFAULT_SCENARIO = os.getenv("INVOICEMIND_LOAD_SCENARIO", "upload")

TERMINAL_STATUSES = {"SUCCESS", "WARN", "NEEDS_REVIEW", "FAILED", "CANCELLED"}


def _sample_payload() -> bytes:
    return Path("tests/e2e/sample_invoice.png").read_bytes()


async def get_token(client: httpx.AsyncClient) -> str:
    r = await client.post("/v1/auth/token", json={"username": "admin", "password": "admin123"})
    r.raise_for_status()
    return r.json()["access_token"]


async def upload_document(client: httpx.AsyncClient, token: str, payload: bytes, idx: int) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "X-Filename": f"perf_{idx}.png",
        "X-Content-Type": "image/png",
    }
    r = await client.post("/v1/documents", content=payload, headers=headers)
    r.raise_for_status()
    return str(r.json()["id"])


async def create_run(client: httpx.AsyncClient, token: str, doc_id: str, idx: int) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": f"perf-{idx}-{uuid.uuid4()}",
    }
    r = await client.post(f"/v1/documents/{doc_id}/runs", headers=headers)
    r.raise_for_status()
    return str(r.json()["run_id"])


async def get_run(client: httpx.AsyncClient, token: str, run_id: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/v1/runs/{run_id}", headers=headers)
    r.raise_for_status()
    return r.json()


async def cancel_run(client: httpx.AsyncClient, token: str, run_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(f"/v1/runs/{run_id}/cancel", headers=headers)
    r.raise_for_status()


async def replay_run(client: httpx.AsyncClient, token: str, run_id: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(f"/v1/runs/{run_id}/replay", headers=headers)
    r.raise_for_status()
    return str(r.json()["run_id"])


async def wait_for_terminal_status(
    client: httpx.AsyncClient,
    token: str,
    run_id: str,
    timeout_seconds: float = 20.0,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        payload = await get_run(client, token, run_id)
        status = str(payload["status"])
        if status in TERMINAL_STATUSES:
            return status
        await asyncio.sleep(0.2)
    return "TIMEOUT"


async def scenario_upload(client: httpx.AsyncClient, token: str, payload: bytes, idx: int) -> dict[str, Any]:
    start = time.perf_counter()
    await upload_document(client, token, payload, idx)
    return {"latency_ms": (time.perf_counter() - start) * 1000, "status": "SUCCESS"}


async def scenario_run_lifecycle(client: httpx.AsyncClient, token: str, payload: bytes, idx: int) -> dict[str, Any]:
    start = time.perf_counter()
    doc_id = await upload_document(client, token, payload, idx)
    run_id = await create_run(client, token, doc_id, idx)
    final_status = await wait_for_terminal_status(client, token, run_id)
    return {"latency_ms": (time.perf_counter() - start) * 1000, "status": final_status}


async def scenario_replay_cancel(client: httpx.AsyncClient, token: str, payload: bytes, idx: int) -> dict[str, Any]:
    start = time.perf_counter()
    doc_id = await upload_document(client, token, payload, idx)
    run_id = await create_run(client, token, doc_id, idx)
    await cancel_run(client, token, run_id)
    replay_id = await replay_run(client, token, run_id)
    final_status = await wait_for_terminal_status(client, token, replay_id)
    return {"latency_ms": (time.perf_counter() - start) * 1000, "status": final_status}


def _pick_scenario(name: str):
    mapping = {
        "upload": scenario_upload,
        "run_lifecycle": scenario_run_lifecycle,
        "replay_cancel": scenario_replay_cancel,
    }
    if name not in mapping:
        raise ValueError(f"Unknown scenario: {name}")
    return mapping[name]


async def run_benchmark(*, scenario: str, requests: int, concurrency: int, timeout: float) -> dict[str, Any]:
    payload = _sample_payload()
    scenario_fn = _pick_scenario(scenario)

    async with httpx.AsyncClient(base_url=API_URL, timeout=timeout) as client:
        token = await get_token(client)
        sem = asyncio.Semaphore(concurrency)
        results: list[float] = []
        statuses: Counter[str] = Counter()
        failures = 0

        async def worker(i: int) -> None:
            nonlocal failures
            async with sem:
                try:
                    out = await scenario_fn(client, token, payload, i)
                except Exception:  # noqa: BLE001
                    failures += 1
                    statuses["EXCEPTION"] += 1
                    return
                results.append(float(out["latency_ms"]))
                statuses[str(out["status"])] += 1

        await asyncio.gather(*[worker(i) for i in range(requests)])

    if results:
        p50 = statistics.median(results)
        p95 = sorted(results)[max(0, int(len(results) * 0.95) - 1)]
    else:
        p50 = 0.0
        p95 = 0.0

    return {
        "scenario": scenario,
        "requests": requests,
        "concurrency": concurrency,
        "successes": len(results),
        "failures": failures,
        "latency_ms_p50": round(p50, 2),
        "latency_ms_p95": round(p95, 2),
        "status_distribution": dict(statuses),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="InvoiceMind load test scenarios")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO, choices=["upload", "run_lifecycle", "replay_cancel"])
    parser.add_argument("--requests", type=int, default=DEFAULT_REQUESTS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json", action="store_true", help="Print json output")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = asyncio.run(
        run_benchmark(
            scenario=args.scenario,
            requests=max(1, args.requests),
            concurrency=max(1, args.concurrency),
            timeout=max(1.0, args.timeout),
        )
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"scenario={result['scenario']} requests={result['requests']} concurrency={result['concurrency']}")
    print(f"successes={result['successes']} failures={result['failures']}")
    print(f"latency_ms_p50={result['latency_ms_p50']}")
    print(f"latency_ms_p95={result['latency_ms_p95']}")
    print(f"status_distribution={json.dumps(result['status_distribution'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
