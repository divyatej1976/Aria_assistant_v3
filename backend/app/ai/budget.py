"""AI cost accounting and monthly budget enforcement.

Spend is estimated from reported token usage using a per-model rate table and
accumulated per calendar month. Accounting is persisted to the `ai_usage`
table so the total survives restarts and is shared across replicas; when the
database is unavailable (e.g., SQLite without the table), a process-local
fallback accumulator is used so local development and tests still enforce the
budget. A budget of zero means unlimited. When the configured monthly budget
is reached, generation is blocked (call sites fall back to deterministic
behavior).
"""

import threading
from datetime import UTC, datetime

from app.core.config import get_settings

# USD per 1K tokens (input, output). Falls back to the DEFAULT rates when a
# model is unknown so budgets still bind.
MODEL_RATES: dict[str, tuple[float, float]] = {
    "llama-3.3-70b-versatile": (0.00059, 0.00079),
    "llama-3.1-8b-instant": (0.00005, 0.00008),
    "gemma2-9b-it": (0.00020, 0.00020),
    "whisper-large-v3": (0.0000, 0.0000),  # audio; charged per second elsewhere
}
DEFAULT_INPUT_RATE = 0.00059
DEFAULT_OUTPUT_RATE = 0.00079


class BudgetExceeded(RuntimeError):
    pass


_lock = threading.Lock()
_fallback_spend_usd = 0.0


def monthly_budget_usd() -> float:
    return get_settings().aria_ai_monthly_budget_usd


def _rates(model: str) -> tuple[float, float]:
    return MODEL_RATES.get(model, (DEFAULT_INPUT_RATE, DEFAULT_OUTPUT_RATE))


def estimate_cost_usd(*, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    input_rate, output_rate = _rates(model)
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1000.0


def _period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _db_record_cost(cost: float, period: str) -> bool:
    try:
        from sqlalchemy import select

        from app.db.models import AiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            row = db.scalar(select(AiUsage).where(AiUsage.period == period))
            if row is None:
                db.add(AiUsage(period=period, spend_usd=cost))
            else:
                row.spend_usd += cost
                db.add(row)
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        return False


def _db_spend(period: str) -> float:
    try:
        from sqlalchemy import select

        from app.db.models import AiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            row = db.scalar(select(AiUsage).where(AiUsage.period == period))
            return row.spend_usd if row else 0.0
        finally:
            db.close()
    except Exception:
        return 0.0


def _db_reset(period: str) -> None:
    try:
        from sqlalchemy import delete

        from app.db.models import AiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            db.execute(delete(AiUsage).where(AiUsage.period == period))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def record_usage(*, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    global _fallback_spend_usd
    cost = estimate_cost_usd(
        model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    period = _period()
    if not _db_record_cost(cost, period):
        with _lock:
            _fallback_spend_usd += cost
    return spend_usd()


def spend_usd() -> float:
    with _lock:
        fallback = _fallback_spend_usd
    return _db_spend(_period()) + fallback


def reset_budget() -> None:
    global _fallback_spend_usd
    with _lock:
        _fallback_spend_usd = 0.0
    _db_reset(_period())


def assert_within_budget() -> None:
    budget = monthly_budget_usd()
    if budget <= 0:
        return
    if spend_usd() >= budget:
        raise BudgetExceeded(
            f"Monthly AI budget of ${budget:.2f} has been reached"
        )
