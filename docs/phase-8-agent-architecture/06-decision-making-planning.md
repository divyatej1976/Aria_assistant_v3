# ARIA — Phase 8: Agent Architecture

## Step 6 — Decision-Making & Planning

**Status:** Draft v1

## Purpose

This document defines how ARIA agents make decisions, create execution plans and adapt those plans while remaining explainable, deterministic where required and aligned with business constraints.

---

# Decision Principles

- Decisions begin with validated context.
- Agents reason from available evidence.
- Business constraints take precedence over AI recommendations.
- High-impact decisions require deterministic validation or human oversight.
- Every significant decision should be explainable.

---

# Planning Principles

- Decompose goals into manageable tasks.
- Prefer incremental execution over large monolithic plans.
- Replan when new validated information changes the situation.
- Avoid unnecessary work.
- Stop execution when objectives are achieved or escalation is required.

---

# Decision Boundaries

Agents may:
- Plan.
- Recommend.
- Coordinate.
- Prioritize.

Agents must not:
- Bypass business rules.
- Modify persistent state directly.
- Ignore validation outcomes.
- Override human decisions.

---

# Out of Scope

This document intentionally does not define:

- Prompt engineering.
- Planning algorithms.
- Model-specific reasoning.
- LangGraph implementation.
- Runtime optimization.

---

# Acceptance Criteria

- Decision principles documented.
- Planning principles established.
- Decision boundaries defined.
- Ready for Safety, Guardrails & Human Oversight.

---

## Next

Step 7 — Safety, Guardrails & Human Oversight.