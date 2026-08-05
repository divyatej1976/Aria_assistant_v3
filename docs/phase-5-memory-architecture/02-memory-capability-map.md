# ARIA — Phase 5: Memory Architecture

## Step 2 — Memory Capability Map

**Status:** Draft v1

## Purpose

This document defines every logical memory capability within ARIA, separates R0 memory from future memory, and establishes ownership boundaries for each memory type.

---

# R0 Memory Capabilities

## Session Memory
- Active learning session
- Current study activity
- Temporary working context

## Conversation Memory
- Previous messages
- Clarifications
- Follow-up references

## Learner Memory
- Learner goals
- Preferences
- Current learner state

## Evidence Memory
- Validated evidence history
- Assessment outcomes
- Revision history

## Resource Memory
- Uploaded learning resources
- Resource metadata
- Retrieval references

---

# Future Memory Capabilities

- Planner memory
- Roadmap memory
- Career memory
- Multi-goal coordination memory
- Collaboration memory
- Long-term AI mentor memory

---

# Memory Classification

Each memory type should define:

- Purpose
- Ownership
- Lifetime
- Update policy
- Retrieval policy
- Privacy requirements

---

# Design Principles

- Keep memory responsibilities independent.
- Separate temporary and persistent memory.
- Avoid duplication across memory types.
- Memory should remain explainable and traceable.

---

# Out of Scope

This document intentionally does not define:

- Database implementation.
- Physical storage.
- API interfaces.
- AI reasoning algorithms.

---

# Acceptance Criteria

- Memory capabilities are cataloged.
- R0 and future memory are separated.
- Ownership boundaries are established.
- Memory taxonomy aligns with previous phases.

---

## Next

Step 3 — Session Memory.
