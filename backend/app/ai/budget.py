"""In-process AI cost accounting and monthly budget enforcement.

Spend is estimated from reported token usage using a per-model rate table and
accumulated in memory for this process. A budget of zero means unlimited. When
the configured monthly budget is reached, generation is blocked (call sites
fall back to deterministic behavior). Multi-instance deployments should share
spend in a persistent store.
"""

import threading

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
_spend_usd = 0.0


def monthly_budget_usd() -> float:
    return get_settings().aria_ai_monthly_budget_usd


def _rates(model: str) -> tuple[float, float]:
    return MODEL_RATES.get(model, (DEFAULT_INPUT_RATE, DEFAULT_OUTPUT_RATE))


def estimate_cost_usd(*, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    input_rate, output_rate = _rates(model)
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1000.0


def record_usage(*, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    global _spend_usd
    cost = estimate_cost_usd(
        model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    with _lock:
        _spend_usd += cost
        return _spend_usd


def spend_usd() -> float:
    with _lock:
        return _spend_usd


def reset_budget() -> None:
    global _spend_usd
    with _lock:
        _spend_usd = 0.0


def assert_within_budget() -> None:
    budget = monthly_budget_usd()
    if budget <= 0:
        return
    if spend_usd() >= budget:
        raise BudgetExceeded(
            f"Monthly AI budget of ${budget:.2f} has been reached"
        )
