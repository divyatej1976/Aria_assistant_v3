"""AI provider evaluation harness.

Runs canned text and structured prompts against the configured LLM provider and
prints latency, token, and cost metrics. Exits non-zero when any call fails or
returns output that fails schema validation.

Usage:
    python scripts/eval_ai.py
"""

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ai.budget import reset_budget, spend_usd  # noqa: E402
from app.ai.prompts import get_prompt  # noqa: E402
from app.ai.registry import get_llm_provider  # noqa: E402
from app.assessment.schema import ConceptSet  # noqa: E402

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules."
)


async def run_case(provider, name: str, coro) -> dict[str, Any]:
    started = time.monotonic()
    try:
        await coro
        ok = True
        detail = "ok"
    except Exception as exc:  # noqa: BLE001 - eval reports any failure
        ok = False
        detail = f"{type(exc).__name__}: {exc}"
    return {
        "name": name,
        "ok": ok,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "detail": detail,
    }


async def main() -> int:
    reset_budget()
    provider = get_llm_provider()
    if provider is None:
        print("GROQ_API_KEY not configured — provider eval skipped.")
        return 0

    cases = [
        run_case(
            provider,
            "study_answer",
            provider.generate_text(
                system=get_prompt("study_answer").system,
                user=get_prompt("study_answer").render(
                    context=MATERIAL, question="What is strict two-phase locking?"
                ),
                prompt_version=get_prompt("study_answer").label(),
            ),
        ),
        run_case(
            provider,
            "concept_extraction",
            provider.generate_structured(
                prompt=get_prompt("concept_extraction").render(
                    limit=3, material=MATERIAL
                ),
                schema=ConceptSet,
                prompt_version=get_prompt("concept_extraction").label(),
            ),
        ),
    ]

    results = []
    for coro in cases:
        results.append(await coro)

    print(f"{'case':<20} {'ok':<5} {'duration_ms':>10} {'detail'}")
    failures = 0
    for result in results:
        failures += 0 if result["ok"] else 1
        print(
            f"{result['name']:<20} {str(result['ok']):<5} {result['duration_ms']:>10} "
            f"{result['detail']}"
        )
    print(f"estimated spend: ${spend_usd():.4f}")
    return 1 if failures else 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
