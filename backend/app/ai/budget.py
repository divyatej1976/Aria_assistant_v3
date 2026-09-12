"""AI cost accounting and monthly budget enforcement.

Spend is estimated from reported token usage using a per-model rate table and
accumulated per calendar month. Accounting is persisted to the `ai_usage`
table so the total survives restarts and is shared across replicas.

When the database is unavailable in development (e.g., SQLite without the
table), a process-local fallback accumulator keeps the budget binding locally.
In production the app fails closed: if persistent accounting cannot be read or
written, generation is blocked rather than allowed to overspend the configured
limit. A budget of zero means unlimited. When the configured monthly budget is
reached, generation is blocked (call sites fall back to deterministic
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
    # Groq list prices (per 1M tokens) for the gpt-oss family; unknown models
    # fall back to the conservative DEFAULT rates so budgets still bind.
    "openai/gpt-oss-120b": (0.00015, 0.00075),
    "openai/gpt-oss-20b": (0.00010, 0.00050),
    "whisper-large-v3": (0.0000, 0.0000),  # audio; charged per second elsewhere
}
DEFAULT_INPUT_RATE = 0.00059
DEFAULT_OUTPUT_RATE = 0.00079


class BudgetExceeded(RuntimeError):
    pass


_lock = threading.Lock()
_fallback_spend_usd = 0.0
# True once persistent accounting has failed in production; generation is
# blocked until a DB probe succeeds again (self-healing).
_accounting_unavailable = False


def monthly_budget_usd() -> float:
    return get_settings().aria_ai_monthly_budget_usd


def _mark_db_failure() -> None:
    """Fail closed only in production; dev/tests keep the in-memory fallback."""
    global _accounting_unavailable
    if getattr(get_settings(), "aria_env", "development") == "production":
        _accounting_unavailable = True


def _probe_db(table: str = "ai_usage") -> bool:
    """Probe reads *from the accounting table itself*, not bare connectivity:
    a healthy connection with a missing/broken table must still fail closed
    (spend reads would otherwise silently return 0.0 and disable the budget)."""
    try:
        from sqlalchemy import text

        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            if table == "learner_ai_usage":
                db.execute(text("SELECT spend_usd FROM learner_ai_usage LIMIT 1"))
            else:
                db.execute(text("SELECT spend_usd FROM ai_usage LIMIT 1"))
        finally:
            db.close()
        return True
    except Exception:
        return False


def _rates(model: str) -> tuple[float, float]:
    return MODEL_RATES.get(model, (DEFAULT_INPUT_RATE, DEFAULT_OUTPUT_RATE))


def estimate_cost_usd(*, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    input_rate, output_rate = _rates(model)
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1000.0


def _period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _db_record_cost(cost: float, period: str) -> bool:
    try:
        from app.db.models import AiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            dialect = db.get_bind().dialect.name
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                stmt = pg_insert(AiUsage).values(period=period, spend_usd=cost)
            else:
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                stmt = sqlite_insert(AiUsage).values(period=period, spend_usd=cost)
            # Atomic upsert: the increment happens in SQL, so concurrent
            # replicas cannot lose an update (read-modify-write in Python did).
            db.execute(
                stmt.on_conflict_do_update(
                    index_elements=[AiUsage.period],
                    set_={"spend_usd": AiUsage.spend_usd + cost},
                )
            )
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        _mark_db_failure()
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
        _mark_db_failure()
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
    global _fallback_spend_usd, _accounting_unavailable
    with _lock:
        _fallback_spend_usd = 0.0
    _accounting_unavailable = False
    _db_reset(_period())


def assert_within_budget() -> None:
    """Global pre-call gate (best-effort under concurrency).

    Spend increments are atomic SQL upserts so concurrent replicas cannot lose
    updates, but in-flight requests admitted just before the cap is reached
    can still overshoot by a bounded amount. Keep caps conservative.
    """
    budget = monthly_budget_usd()
    if budget <= 0:
        return
    global _accounting_unavailable
    # Fail closed only in production; the flag is never set outside production.
    in_production = getattr(get_settings(), "aria_env", "development") == "production"
    if _accounting_unavailable and in_production:
        # Self-heal: try the accounting table again; clear the flag if it recovers.
        healthy = _probe_db("ai_usage")
        if not healthy:
            raise BudgetExceeded(
                "Persistent AI budget accounting is unavailable; blocking "
                "generation to avoid exceeding the configured budget"
            )
        _accounting_unavailable = False
    if spend_usd() >= budget:
        raise BudgetExceeded(
            f"Monthly AI budget of ${budget:.2f} has been reached"
        )


# --- Per-learner budgets (Step 4: BYO keys) ---

_learner_fallback_spend: dict[tuple[str, str], float] = {}


def learner_budget_usd() -> float:
    return float(getattr(get_settings(), "aria_llm_per_user_budget_usd", 0.0) or 0.0)


def _learner_apply_cost(owner_id: object, cost: float, period: str) -> bool:
    """Atomic spend adjustment; negative deltas (refunds) are supported."""
    try:
        from app.db.models import LearnerAiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            dialect = db.get_bind().dialect.name
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                stmt = pg_insert(LearnerAiUsage).values(
                    owner_id=owner_id, period=period, spend_usd=cost
                )
            else:
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                stmt = sqlite_insert(LearnerAiUsage).values(
                    owner_id=owner_id, period=period, spend_usd=cost
                )
            db.execute(
                stmt.on_conflict_do_update(
                    index_elements=[LearnerAiUsage.owner_id, LearnerAiUsage.period],
                    set_={"spend_usd": LearnerAiUsage.spend_usd + cost},
                )
            )
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        _mark_db_failure()
        return False


def _learner_db_spend(owner_id: object, period: str) -> float:
    try:
        from sqlalchemy import select

        from app.db.models import LearnerAiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            row = db.scalar(
                select(LearnerAiUsage).where(
                    LearnerAiUsage.owner_id == owner_id,
                    LearnerAiUsage.period == period,
                )
            )
            return row.spend_usd if row else 0.0
        finally:
            db.close()
    except Exception:
        _mark_db_failure()
        return 0.0


def record_learner_usage(
    *, owner_id: object, model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    cost = estimate_cost_usd(
        model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    period = _period()
    if not _learner_apply_cost(owner_id, cost, period):
        with _lock:
            key = (str(owner_id), period)
            _learner_fallback_spend[key] = _learner_fallback_spend.get(key, 0.0) + cost
    return learner_spend_usd(owner_id)


def reserve_learner_usage(
    *, owner_id: object, model: str, prompt_tokens: int, completion_tokens: int
) -> None:
    """Charge an upfront cost estimate *before* the provider call.

    Concurrent in-flight requests each pay their estimated maximum upfront,
    so `assert_learner_within_budget` sees their reservations immediately —
    the hard-cap overshoot shrinks from a whole request to the difference
    between estimate and actual usage.
    """
    record_learner_usage(
        owner_id=owner_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def settle_learner_usage(
    *,
    owner_id: object,
    model: str,
    prompt_tokens_delta: int,
    completion_tokens_delta: int,
) -> None:
    """Reconcile final usage against the reservation (deltas may be negative).

    Called after the provider response with (actual - reserved) tokens, so
    the learner's recorded spend converges to actual usage. Refunds the full
    reservation when a call fails before completion (deltas = -reserved).
    """
    if prompt_tokens_delta == 0 and completion_tokens_delta == 0:
        return
    cost = estimate_cost_usd(
        model=model,
        prompt_tokens=prompt_tokens_delta,
        completion_tokens=completion_tokens_delta,
    )
    period = _period()
    if not _learner_apply_cost(owner_id, cost, period):
        with _lock:
            key = (str(owner_id), period)
            _learner_fallback_spend[key] = _learner_fallback_spend.get(key, 0.0) + cost


def learner_spend_usd(owner_id: object) -> float:
    period = _period()
    with _lock:
        fallback = _learner_fallback_spend.get((str(owner_id), period), 0.0)
    return _learner_db_spend(owner_id, period) + fallback


def assert_learner_within_budget(owner_id: object) -> None:
    """Per-learner pre-call gate (best-effort under concurrency; see above)."""
    global _accounting_unavailable
    in_production = getattr(get_settings(), "aria_env", "development") == "production"
    if _accounting_unavailable and in_production:
        healthy = _probe_db("learner_ai_usage")
        if not healthy:
            raise BudgetExceeded(
                "Persistent AI budget accounting is unavailable; blocking "
                "generation to avoid exceeding the configured budget"
            )
        _accounting_unavailable = False
    budget = learner_budget_usd()
    if budget <= 0:
        return
    if learner_spend_usd(owner_id) >= budget:
        raise BudgetExceeded("Monthly personal AI budget has been reached")


def reset_learner_budget(owner_id: object | None = None) -> None:
    with _lock:
        if owner_id is None:
            _learner_fallback_spend.clear()
        else:
            for key in [k for k in _learner_fallback_spend if k[0] == str(owner_id)]:
                del _learner_fallback_spend[key]
    try:
        from sqlalchemy import delete

        from app.db.models import LearnerAiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            stmt = delete(LearnerAiUsage).where(LearnerAiUsage.period == _period())
            if owner_id is not None:
                stmt = stmt.where(LearnerAiUsage.owner_id == owner_id)
            db.execute(stmt)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
