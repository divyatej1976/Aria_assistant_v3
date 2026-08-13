"""Lightweight load/stress baseline against a running ARIA backend.

Hits unauthenticated and authenticated endpoints at a given concurrency and
writes a latency/throughput/error report (reports/load_baseline.json). This is
the usage evidence that gates the caching and retrieval decisions in later
Phase 12 tranches.

Usage:
    python scripts/load_baseline.py --base http://localhost:8000 \
        --concurrency 20 --duration 15

Exit code is non-zero when p95 latency exceeds --p95-max-ms (default 1000) or
the error rate exceeds --max-error-rate (default 0.05).
"""

import argparse
import asyncio
import json
import statistics
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"


async def _register_token(client: httpx.AsyncClient, base: str) -> str | None:
    email = f"load-{uuid.uuid4().hex[:10]}@example.com"
    try:
        response = await client.post(
            f"{base}/api/v1/auth/register",
            json={"email": email, "password": "correct-horse"},
        )
        if response.status_code == 201:
            return response.json()["access_token"]
    except httpx.HTTPError:
        pass
    return None


async def _worker(
    client: httpx.AsyncClient,
    base: str,
    token: str | None,
    paths: list[str],
    duration: float,
    results: list[dict],
) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    started = time.monotonic()
    index = 0
    while time.monotonic() - started < duration:
        path = paths[index % len(paths)]
        index += 1
        begin = time.perf_counter()
        try:
            response = await client.get(f"{base}{path}", headers=headers)
            status = response.status_code
        except httpx.HTTPError:
            status = 0
        results.append(
            {
                "path": path,
                "status": status,
                "ms": (time.perf_counter() - begin) * 1000,
            }
        )


def _summarize(results: list[dict]) -> dict:
    by_path: dict[str, list[float]] = {}
    errors = 0
    for result in results:
        bucket = by_path.setdefault(result["path"], [])
        bucket.append(result["ms"])
        if result["status"] == 0 or result["status"] >= 500:
            errors += 1
    summary = {}
    total = len(results)
    for path, latencies in by_path.items():
        summary[path] = {
            "requests": len(latencies),
            "p50_ms": round(statistics.median(latencies), 1),
            "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 1),
            "max_ms": round(max(latencies), 1),
        }
    return {"total_requests": total, "errors": errors, "paths": summary}


async def run(args) -> int:
    results: list[dict] = []
    paths = ["/health", "/ready", "/metrics", "/api/v1/contexts"]
    async with httpx.AsyncClient(timeout=10) as client:
        token = await _register_token(client, args.base)
        workers = [
            asyncio.create_task(
                _worker(client, args.base, token, paths, args.duration, results)
            )
            for _ in range(args.concurrency)
        ]
        await asyncio.gather(*workers)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base": args.base,
        "concurrency": args.concurrency,
        "duration_seconds": args.duration,
        "authenticated": token is not None,
        **_summarize(results),
    }
    REPORT_DIR.mkdir(exist_ok=True)
    output = REPORT_DIR / "load_baseline.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    error_rate = report["errors"] / report["total_requests"] if report["total_requests"] else 0
    p95_max = max(path["p95_ms"] for path in report["paths"].values()) if report["paths"] else 0
    if error_rate > args.max_error_rate:
        print(f"FAIL: error rate {error_rate:.2%} exceeds {args.max_error_rate:.2%}")
        return 1
    if p95_max > args.p95_max_ms:
        print(f"FAIL: p95 {p95_max:.0f}ms exceeds {args.p95_max_ms}ms")
        return 1
    print("Load baseline OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--p95-max-ms", type=float, default=1000)
    parser.add_argument("--max-error-rate", type=float, default=0.05)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
